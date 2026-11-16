"""Honest status until a validated ESP32 transport is installed. No device I/O."""

import threading


class UnconfiguredRobotProvider:
    def __init__(self):
        self.lock = threading.RLock()
        self.scenario = "disconnected"
        self.action = None

    def status(self):
        return {
            "source": "real",
            "hardware_connected": False,
            "connection": "disconnected",
            "scenario": "disconnected",
            "state": "unavailable",
            "control": {
                "action": None,
                "speed": "low",
                "epoch": 0,
                "window_id": "",
                "window_valid_for_ms": 0,
                "command_ttl_ms": 0,
                "owner": None,
            },
            "capabilities": {
                "manual_control": False,
                "npk_capture": False,
                "physical_motion": False,
                "camera": False,
                "ambient": False,
                "inclination": False,
            },
        }

    def command(self, data):
        return {
            "code": "robot_not_integrated",
            "detail": "El vehículo no está conectado. El control físico no está habilitado.",
            "hardware_acted": False,
        }, 503

    def telemetry(self):
        return {
            "battery": {
                "value": None,
                "unit": "%",
                "source": "real",
                "validity": "unknown",
                "freshness": "unknown",
                "status": "unavailable",
            },
            "ambient_temperature": None,
            "ambient_humidity": None,
            "inclination": None,
        }
