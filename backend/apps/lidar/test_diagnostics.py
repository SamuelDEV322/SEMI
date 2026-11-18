import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from django.test import SimpleTestCase
from adapters.a1 import frame
from adapters.lidar_diagnostics import annotate
from adapters.lidar_sources import LidarSources
from adapters import registry


class PassiveLidarTests(SimpleTestCase):
    def setUp(self):
        config = patch.dict(os.environ, {"SEMI_LIDAR_PORT": ""})
        config.start()
        self.addCleanup(config.stop)
        self.inventory = patch(
            "adapters.lidar_diagnostics.passive_ports",
            return_value={"status": "ok", "ports": []},
        )
        self.ports = self.inventory.start()
        self.addCleanup(self.inventory.stop)
        self.now = [100.0]

    def result(self, data):
        return annotate(data, clock=lambda: self.now[0])

    def reader(self, data, phase="reading", identified=True):
        data["reader"] = {
            "port": "COM_FAKE_A1",
            "phase": phase,
            "identity_verified": identified,
            "heartbeat_monotonic": 100.0,
            "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        }
        return data

    def test_no_usb_does_not_claim_real_sensor_connected(self):
        result = self.result(frame())
        self.assertEqual(result["acquisition"]["state"], "not_detected")
        self.assertFalse(result["valid"])
        self.assertIsNone(result["acquisition"]["sensor_identified"])
        self.assertFalse(result["acquisition"]["usb_detected"])

    def test_system_com_is_not_lidar(self):
        self.ports.return_value = {
            "status": "ok",
            "ports": [{"port": "COM1", "description": "System port", "usb": False}],
        }
        with patch.dict(os.environ, {"SEMI_LIDAR_PORT": "COM1"}):
            result = self.result(frame())
        self.assertFalse(result["acquisition"]["usb_detected"])
        self.assertEqual(result["acquisition"]["state"], "not_detected")

    def test_unknown_usb_not_automatically_assigned_to_lidar(self):
        self.ports.return_value = {
            "status": "ok",
            "ports": [
                {"port": "COM_FAKE_ESP32", "description": "USB serial", "usb": True}
            ],
        }
        result = self.result(frame())
        self.assertEqual(result["acquisition"]["state"], "usb_unidentified")
        self.assertIsNone(result["acquisition"]["selected_port"])

    def test_explicit_usb_port_detected_without_scan_or_open(self):
        self.ports.return_value = {
            "status": "ok",
            "ports": [
                {"port": "COM_FAKE_A1", "description": "USB fixture", "usb": True}
            ],
        }
        with patch.dict(os.environ, {"SEMI_LIDAR_PORT": "COM_FAKE_A1"}), patch(
            "adapters.a1.SerialLidarProvider.start"
        ) as start:
            result = self.result(frame())
        start.assert_not_called()
        self.assertEqual(result["acquisition"]["state"], "usb_detected")
        self.assertFalse(result["valid"])
        self.assertIsNone(result["acquisition"]["sensor_identified"])

    def test_waiting_requires_reader_identification_and_recent_heartbeat(self):
        result = self.result(self.reader(frame("no_data")))
        self.assertEqual(result["acquisition"]["state"], "waiting")
        self.assertFalse(result["valid"])
        invalid = frame(
            "valid",
            [{"angle_deg": 0, "distance": 0, "quality": 0, "valid": False}],
            clock=lambda: 100,
        )
        self.assertEqual(
            self.result(self.reader(invalid))["acquisition"]["state"], "waiting"
        )

    def test_active_stale_and_interrupted_are_distinct(self):
        points = [{"angle_deg": 90, "distance": 1000, "quality": 20, "valid": True}]
        data = self.reader(frame("valid", points, clock=lambda: 100))
        self.assertEqual(self.result(dict(data))["acquisition"]["state"], "active")
        stale = {**data, "status": "stale", "valid": False}
        self.assertEqual(self.result(stale)["acquisition"]["state"], "stale")
        self.now[0] = 102.1
        result = self.result(dict(data))
        self.assertEqual(result["acquisition"]["state"], "interrupted")
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "stale")

    def test_error_closed_and_missing_inventory_not_fabricated(self):
        self.assertEqual(
            self.result(frame("error", error="fixture"))["acquisition"]["state"],
            "error",
        )
        self.assertEqual(
            self.result(self.reader(frame(), phase="closed"))["acquisition"]["state"],
            "interrupted",
        )
        self.ports.return_value = {"status": "unavailable", "ports": []}
        self.assertEqual(self.result(frame())["acquisition"]["state"], "unknown")

    def test_mismatched_selected_port_rejects_scan(self):
        data = self.reader(
            frame(
                "valid",
                [{"angle_deg": 0, "distance": 300, "quality": 20, "valid": True}],
                clock=lambda: 100,
            )
        )
        with patch.dict(os.environ, {"SEMI_LIDAR_PORT": "COM_DIFFERENT"}):
            result = self.result(data)
        self.assertFalse(result["valid"])
        self.assertEqual(result["acquisition"]["state"], "error")

    def test_reader_is_not_started_without_authorization_or_confirmation(self):
        import io
        from django.core.management import call_command, CommandError

        with patch(
            "apps.agriculture.management.commands.lidar_usb.SerialLidarProvider"
        ) as provider:
            with patch.dict(
                os.environ, {"SEMI_LIDAR_DIAGNOSTICS": "0"}
            ), self.assertRaises(CommandError):
                call_command(
                    "lidar_usb",
                    mode="real",
                    port="COM_FAKE",
                    revision="fixture",
                    stdout=io.StringIO(),
                )
            with patch.dict(os.environ, {"SEMI_LIDAR_DIAGNOSTICS": "1"}), patch(
                "builtins.input", return_value="CANCEL"
            ), self.assertRaises(CommandError):
                call_command(
                    "lidar_usb",
                    mode="real",
                    port="COM_FAKE",
                    revision="fixture",
                    stdout=io.StringIO(),
                )
            provider.assert_not_called()
