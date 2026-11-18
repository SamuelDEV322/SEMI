"""Single-robot bench broker. All deadlines use this process's monotonic clock."""

import hashlib
import hmac
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
import re
import secrets
import threading
import time
from dataclasses import dataclass, field

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .services import DeviceFault
from .views import DeviceAPIView, envelope

ACTIONS = {"traction": ("forward", "backward", "left", "right"), "rack": ("up", "down")}
MAX_HOLD = {"traction": 1.5, "rack": 0.30}
LINK_TIMEOUT = 0.45
HOLD_TTL = 0.35


def configured():
    return (
        settings.SEMI_MODE == "operational"
        and settings.SEMI_DEVICE_INTEGRATION == "diagnostic"
        and bool(settings.SEMI_BENCH_DEVICE)
        and len(settings.SEMI_MOTOR_KEY) >= 32
        and len(settings.SEMI_OPERATOR_KEY) >= 32
        and len(
            {
                settings.SEMI_MOTOR_KEY,
                settings.SEMI_OPERATOR_KEY,
                settings.SEMI_DEVICE_TOKENS.get(settings.SEMI_BENCH_DEVICE),
            }
        )
        == 3
        and bool(settings.SEMI_DEVICE_TOKENS.get(settings.SEMI_BENCH_DEVICE))
    )


def mac(message):
    return hmac.new(
        settings.SEMI_MOTOR_KEY.encode(), message.encode(), hashlib.sha256
    ).hexdigest()


def denied():
    raise DeviceFault(
        "manual_unavailable",
        "El mando caducó. Suelta el botón y revisa la conexión.",
        409,
    )


@dataclass
class Channel:
    ready: bool = False
    armed: bool = False
    window: str = field(default_factory=lambda: secrets.token_hex(16))
    action: str = "stop"
    speed: str = "low"
    owner: str = ""
    seq: int = 0
    until: float = 0
    hard_end: float = 0

    def stop(self, disarm=False):
        self.action = "stop"
        self.window = secrets.token_hex(16)
        self.owner = ""
        if disarm:
            self.armed = False


class Bench:
    def __init__(self):
        self.lock = threading.RLock()
        self.boot = ""
        self.counter = 0
        self.last = -1e12
        self.channels = {name: Channel() for name in ACTIONS}

    def expire(self, now):
        for channel in self.channels.values():
            if now < self.last or now - self.last >= LINK_TIMEOUT:
                channel.ready = False
                channel.stop(True)
            elif channel.action != "stop" and now >= channel.until:
                channel.stop(True)

    def status(self, now):
        with self.lock:
            self.expire(now)
            tick = int(now * 1000)
            return {
                name: {
                    "ready": c.ready,
                    "armed": c.armed,
                    "action": c.action,
                    "epoch": tick,
                    "window_id": c.window,
                    "ticket": mac(f"ui|{name}|{c.window}|{tick}"),
                }
                for name, c in self.channels.items()
            }

    def intent(self, data, now):
        with self.lock:
            self.expire(now)
            domain, action = data.get("domain"), data.get("action")
            if domain == "all" and action == "stop":
                for chan in self.channels.values():
                    chan.stop(True)
                return
            if domain not in ("traction", "rack"):
                raise ValidationError("Mecanismo desconocido.")
            c = self.channels[domain]
            if action in ("stop", "disarm"):
                c.stop(action == "disarm")
                return
            epoch = data.get("epoch")
            if (
                not c.ready
                or type(epoch) is not int
                or not 0 <= int(now * 1000) - epoch <= 1800
                or data.get("window_id") != c.window
                or data.get("ticket") != mac(f"ui|{domain}|{c.window}|{epoch}")
            ):
                denied()
            if action == "arm":
                c.stop()
                c.armed = True
                return
            seq, owner, speed = (
                data.get("seq"),
                data.get("session_id"),
                data.get("speed"),
            )
            if (
                not c.armed
                or action not in ACTIONS[domain]
                or speed not in ("low", "medium")
                or type(seq) is not int
                or seq <= 0
                or not isinstance(owner, str)
                or not 1 <= len(owner) <= 64
            ):
                denied()
            if c.action != "stop" and (
                c.action != action or owner != c.owner or seq <= c.seq
            ):
                c.stop(True)
                denied()
            if c.action == "stop":
                c.hard_end = now + MAX_HOLD[domain]
            c.action, c.speed, c.owner, c.seq = action, speed, owner, seq
            c.until = min(now + HOLD_TTL, c.hard_end)

    def poll(self, boot, count, flags, now):
        with self.lock:
            self.expire(now)
            if boot != self.boot:
                if count != 1:
                    denied()
                for c in self.channels.values():
                    c.stop(True)
                self.boot, self.counter = boot, 0
            if count <= self.counter:
                denied()
            self.counter, self.last = count, now
            fields = ["reply", boot, str(count)]
            for bit, c in enumerate(self.channels.values()):
                c.ready = bool(flags & (1 << bit))
                if not c.ready:
                    c.stop(True)
                ttl = (
                    max(0, min(250, int((c.until - now) * 1000)))
                    if c.action != "stop"
                    else 0
                )
                fields.extend([c.action if ttl else "stop", c.speed, str(ttl)])
            return "|".join(fields)


class SharedBench:
    """Serialize all workers on this host. Keep control traffic outside the farm database."""

    def call(self, method, *args):
        fault = None
        try:
            with closing(
                sqlite3.connect(settings.SEMI_BENCH_STORE, timeout=0.10)
            ) as db, db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS bench (id INTEGER PRIMARY KEY, state TEXT NOT NULL)"
                )
                row = db.execute("SELECT state FROM bench WHERE id=1").fetchone()
                state = Bench()
                if row:
                    data = json.loads(row[0])
                    state.boot, state.counter, state.last = (
                        data["boot"],
                        data["counter"],
                        data["last"],
                    )
                    state.channels = {name: Channel(**data[name]) for name in ACTIONS}
                try:
                    result = getattr(state, method)(*args, time.monotonic())
                except DeviceFault as exc:
                    # A contradictory order must commit its stop even though HTTP returns 409.
                    fault = exc
                record = {
                    "boot": state.boot,
                    "counter": state.counter,
                    "last": state.last,
                    **{name: asdict(c) for name, c in state.channels.items()},
                }
                db.execute(
                    "INSERT OR REPLACE INTO bench VALUES (1,?)", (json.dumps(record),)
                )
        except sqlite3.Error:
            raise DeviceFault(
                "bench_storage",
                "El mando está ocupado o sin almacenamiento disponible.",
                503,
            )
        if fault:
            raise fault
        return result


bench = SharedBench()


class BenchPoll(DeviceAPIView):
    def post(self, request):
        device = request.auth
        if not configured() or device.device_id != settings.SEMI_BENCH_DEVICE:
            raise PermissionDenied("Banco desactivado.")
        d = request.data
        if str(device.session_id) != d.get("session_id"):
            denied()
        boot, n, bits = d.get("boot"), d.get("counter"), d.get("ready")
        if (
            not isinstance(boot, str)
            or not re.fullmatch("[0-9a-f]{32}", boot)
            or type(n) is not int
            or not 1 <= n <= 0x7FFFFFFF
            or type(bits) is not int
            or not 0 <= bits <= 3
        ):
            raise ValidationError("Consulta inválida.")
        expected = mac(f"poll|{device.device_id}|{device.session_id}|{boot}|{n}|{bits}")
        if not hmac.compare_digest(expected.encode(), str(d.get("mac", "")).encode()):
            raise PermissionDenied("Firma inválida.")
        frame = bench.call("poll", boot, n, bits)
        return Response(envelope({"frame": frame, "mac": mac(frame)}))


@api_view(["POST"])
def manual_control(request):
    key = request.headers.get("X-SEMI-Operator", "")
    if not configured() or not hmac.compare_digest(
        key.encode(), settings.SEMI_OPERATOR_KEY.encode()
    ):
        raise PermissionDenied(
            "Comprueba la clave del operador y la configuración del banco."
        )
    if not isinstance(request.data, dict):
        raise ValidationError("Mando inválido.")
    bench.call("intent", request.data)
    return Response(envelope(bench.call("status")))
