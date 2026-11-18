import math
import threading
import time
import uuid
from datetime import timedelta
from django.utils import timezone


class MockRobotProvider:
    """Single-process simulation. Deadlines are checked on every observation.

    This never writes GPIO, serial, USB or network commands. It is NOT a real
    motor safety supervisor; a future firmware must enforce its own deadlines.
    """

    scenarios = {"connected", "disconnected", "no_data", "error", "stale"}

    def __init__(self):
        self.lock = threading.RLock()
        self.reset()

    def reset(self):
        with self.lock:
            self.simulation_id = uuid.uuid4()
            self.scenario = "connected"
            self.action = "stop"
            self.speed = "low"
            self.epoch = 0
            self.owner = None
            self.deadline = 0.0
            self.last_seq = {}
            self.windows = {}

    def _expire(self):
        now = time.monotonic()
        self.windows = {
            key: value for key, value in self.windows.items() if value > now
        }
        if self.action != "stop" and now >= self.deadline:
            self.action, self.owner = "stop", None
            self.epoch += 1

    def set_scenario(self, scenario):
        with self.lock:
            self.scenario = scenario
            self.action, self.owner = "stop", None
            self.epoch += 1
            self.windows.clear()

    def status(self):
        with self.lock:
            self._expire()
            token = str(uuid.uuid4())
            self.windows[token] = time.monotonic() + 1.5
            # Bounded memory even when multiple clients poll.
            if len(self.windows) > 64:
                self.windows.pop(next(iter(self.windows)))
            return {
                "source": "mock",
                "hardware_connected": False,
                "connection": (
                    "simulated_online"
                    if self.scenario not in {"disconnected", "error"}
                    else "simulated_offline"
                ),
                "scenario": self.scenario,
                "state": (
                    "fault"
                    if self.scenario == "error"
                    else (
                        "moving_simulated"
                        if self.action != "stop"
                        else "stopped_simulated"
                    )
                ),
                "control": {
                    "action": self.action,
                    "speed": self.speed,
                    "epoch": self.epoch,
                    "window_id": token,
                    "window_valid_for_ms": 1500,
                    "command_ttl_ms": 450,
                    "owner": self.owner,
                },
                "capabilities": {
                    "manual_control": True,
                    "npk_capture": True,
                    "physical_motion": False,
                    "camera": False,
                    "ambient": False,
                    "inclination": False,
                },
            }

    def command(self, data):
        with self.lock:
            self._expire()
            if data["mode"] != "demonstration":
                return {
                    "code": "physical_control_forbidden",
                    "detail": "Gate 1 solo admite comandos de demostración.",
                }, 403
            if self.scenario in {"disconnected", "error"} and data["action"] != "stop":
                return {
                    "code": "simulated_link_unavailable",
                    "detail": "El enlace simulado no está disponible.",
                }, 503
            session, seq = data["session_id"], data["seq"]
            if seq <= self.last_seq.get(session, -1):
                return {
                    "code": "old_command",
                    "detail": "Secuencia repetida o antigua.",
                }, 409
            if data["action"] != "stop":
                if data["epoch"] != self.epoch:
                    return {
                        "code": "old_epoch",
                        "detail": "Sincroniza el estado antes de mover.",
                    }, 409
                if self.windows.get(data["window_id"], 0) <= time.monotonic():
                    return {
                        "code": "expired_command",
                        "detail": "Ventana de mando vencida.",
                    }, 409
                if self.owner is not None and self.owner != session:
                    return {
                        "code": "operator_busy",
                        "detail": "Otro operador tiene el control simulado.",
                    }, 409
            if len(self.last_seq) >= 128 and session not in self.last_seq:
                return {
                    "code": "session_limit",
                    "detail": "Límite de sesiones; reinicia el simulador.",
                }, 429
            self.last_seq[session] = seq
            self.action, self.speed = data["action"], data["speed"]
            self.owner = session if self.action != "stop" else None
            self.deadline = min(
                time.monotonic() + 0.45,
                self.windows.get(data["window_id"], time.monotonic()),
            )
            if self.action == "stop":
                self.epoch += 1
                self.windows.clear()
            power = 0.25 if self.speed == "low" else 0.5
            tracks = {
                "forward": [power, power],
                "backward": [-power, -power],
                "left": [-power, power],
                "right": [power, -power],
                "stop": [0, 0],
            }[self.action]
            return {
                "result": "applied_simulated",
                "hardware_acted": False,
                "track_demand": tracks,
                "control": self.status()["control"],
            }, 200


class MockTelemetryProvider:
    def __init__(self, robot):
        self.robot = robot

    def latest(self):
        scenario = self.robot.scenario
        available = scenario not in {"no_data", "disconnected", "error"}
        return {
            "battery": {
                "value": 72 if available else None,
                "unit": "%",
                "source": "mock",
                "validity": "valid" if available else "unknown",
                "freshness": "stale" if scenario == "stale" else "fresh",
                "status": "simulated" if available else "unavailable",
            },
            "ambient_temperature": None,
            "ambient_humidity": None,
            "inclination": None,
        }


class MockNPKProvider:
    def capture(self, point_label):
        return {
            "captured_at": timezone.now(),
            "point_label": point_label,
            "nitrogen": 34.0,
            "phosphorus": 18.0,
            "potassium": 87.0,
            "soil_moisture": 42.0,
            "source": "mock",
        }


class MockLidarProvider:
    """Repeatable synthetic room, independent of traction and rack state."""

    def __init__(self, robot=None):
        self.robot = robot  # Legacy construction only; not the source of scan state.
        self.scenario = "connected"

    def set_scenario(self, scenario):
        if scenario not in MockRobotProvider.scenarios:
            raise ValueError("Unknown LiDAR simulation scenario")
        self.scenario = scenario

    def latest(self):
        scenario = self.scenario
        available = scenario not in {"no_data", "disconnected", "error"}
        captured = timezone.now() - timedelta(seconds=30 if scenario == "stale" else 0)
        points = []
        if available:
            for angle in range(0, 360, 3):
                a = math.radians(angle)
                dx, dy = math.sin(a), math.cos(a)
                limits = [
                    2000 / abs(dx) if abs(dx) > 1e-9 else 100000,
                    1600 / abs(dy) if abs(dy) > 1e-9 else 100000,
                ]
                projection = dx * 700 + dy * 800
                discriminant = projection * projection - (
                    700 * 700 + 800 * 800 - 250 * 250
                )
                if discriminant >= 0 and projection > 0:
                    limits.append(projection - math.sqrt(discriminant))
                points.append(
                    {
                        "angle_deg": angle,
                        "distance": round(min(limits), 1),
                        "quality": 35,
                        "valid": True,
                    }
                )
        return {
            "sensor_id": "mock-rplidar-a1",
            "captured_at": captured.isoformat(),
            "status": (
                "simulated"
                if available
                else "error" if scenario == "error" else "unavailable"
            ),
            "source": "mock",
            "unit": "mm",
            "valid": available,
            "freshness": "stale" if scenario == "stale" else "fresh",
            "angle_convention": "0=forward; clockwise; robot_local",
            "max_range_mm": 4000,
            "points": points,
            "age_ms": 30000 if scenario == "stale" else 0,
            "error": "simulated_lidar_error" if scenario == "error" else None,
        }
