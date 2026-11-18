"""Rack simulation only. No GPIO, PWM, serial or physical motor implementation."""

import hashlib
import json
import time
from .mock import MockRobotProvider


class BlockedRackProvider:
    def status(self):
        return {
            "device_id": None,
            "source": "real",
            "available": False,
            "connection": "unavailable",
            "state": "unavailable",
            "physical_authorized": False,
            "execution_state": "unverified",
            "control": None,
            "diagnostic": "mechanical_limits_and_physical_supervisor_not_validated",
        }

    def command(self, data):
        return {
            "code": "physical_rack_forbidden",
            "detail": "El módulo agrícola físico no está habilitado.",
            "hardware_acted": False,
        }, 403


class MockRackProvider:
    actions = {"up": "forward", "down": "backward", "stop": "stop"}

    def __init__(self, device_id):
        self.device_id = device_id
        self.sim = MockRobotProvider()
        self.lock = self.sim.lock
        self.requests = {}

    def set_scenario(self, scenario):
        self.sim.set_scenario(scenario)

    def stop(self):
        self.sim.set_scenario(self.sim.scenario)

    def status(self):
        raw = self.sim.status()
        control = {
            **raw["control"],
            "action": {"forward": "up", "backward": "down", "stop": "stop"}[
                raw["control"]["action"]
            ],
        }
        state = (
            "error"
            if self.sim.scenario == "error"
            else (
                "unavailable"
                if self.sim.scenario == "disconnected"
                else {
                    "up": "raising_simulated",
                    "down": "lowering_simulated",
                    "stop": "stopped_simulated",
                }[control["action"]]
            )
        )
        return {
            "device_id": self.device_id,
            "source": "mock",
            "available": True,
            "connection": raw["connection"],
            "state": state,
            "physical_authorized": False,
            "execution_state": "unverified",
            "control": control,
            "diagnostic": None,
        }

    def command(self, data):
        with self.lock:
            self.sim._expire()
            if data["mode"] != "demonstration":
                return BlockedRackProvider().command(data)
            if data["device_id"] != self.device_id:
                return {
                    "code": "rack_device_mismatch",
                    "detail": "Selecciona el módulo de esta demostración.",
                }, 400
            key = (data["session_id"], str(data["request_id"]))
            fingerprint = hashlib.sha256(
                json.dumps(data, sort_keys=True, default=str).encode()
            ).hexdigest()
            previous = self.requests.get(key)
            if previous:
                if previous != fingerprint:
                    return {
                        "code": "request_conflict",
                        "detail": "El identificador ya tiene otro contenido.",
                    }, 409
                return self.ack(data, "duplicate"), 200
            desired = self.actions[data["action"]]
            if self.sim.action not in ["stop", desired] and desired != "stop":
                return {
                    "code": "opposite_direction",
                    "detail": "Detén el módulo antes de cambiar de dirección.",
                }, 409
            raw, status = self.sim.command({**data, "action": desired, "speed": "low"})
            if status != 200:
                return raw, status
            if desired != "stop":
                self.sim.deadline = min(
                    self.sim.deadline, time.monotonic() + data["max_duration_ms"] / 1000
                )
            if len(self.requests) >= 256:
                self.requests.pop(next(iter(self.requests)))
            self.requests[key] = fingerprint
            return self.ack(data, "accepted"), 200

    def ack(self, data, acceptance):
        return {
            "result": "accepted_simulated",
            "acceptance": acceptance,
            "hardware_acted": False,
            "execution_state": "unverified",
            "device_id": self.device_id,
            "request_id": str(data["request_id"]),
            "seq": data["seq"],
            "max_duration_ms": data["max_duration_ms"],
            "rack": self.status(),
        }
