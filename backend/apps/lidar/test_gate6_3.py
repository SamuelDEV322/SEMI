"""Authorized reader-to-API path with protocol fixtures, never a serial port."""

import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient
from adapters.a1 import SerialLidarProvider, frame
from adapters.lidar_ipc import reader_lock, local_host
from adapters import registry
from .tests import FakeSerial, packet


@override_settings(SEMI_MODE="operational")
class UnifiedLidarTests(SimpleTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "latest.json"
        env = patch.dict(
            os.environ,
            {
                "SEMI_LIDAR_SPOOL": str(self.path),
                "SEMI_LIDAR_PORT": "FIXTURE_A1",
                "SEMI_LIDAR_DIAGNOSTICS": "1",
            },
        )
        env.start()
        self.addCleanup(env.stop)
        inventory = patch(
            "adapters.lidar_diagnostics.passive_ports",
            return_value={
                "status": "ok",
                "ports": [
                    {"port": "FIXTURE_A1", "description": "fixture", "usb": True}
                ],
            },
        )
        inventory.start()
        self.addCleanup(inventory.stop)

    def test_authorized_command_publishes_scan_to_existing_api_and_closes(self):
        device = FakeSerial()
        device.data.extend(
            packet(0)
            + packet(45, distance=0, start=False)
            + packet(90, start=False)
            + packet(180, quality=0, start=False)
            + packet(0)
        )
        snapshots = []
        original = Path.replace

        def publish(path, target):
            value = original(path, target)
            snapshots.append(APIClient().get("/api/lidar/latest/").json()["data"])
            return value

        def provider(*args, **kwargs):
            return SerialLidarProvider(
                *args, **kwargs, serial_factory=lambda **k: device
            )

        with patch("adapters.a1.SerialLidarProvider", provider), patch(
            "apps.agriculture.management.commands.lidar_usb.SerialLidarProvider",
            provider,
        ), patch("builtins.input", return_value="INICIAR A1"), patch(
            "apps.agriculture.management.commands.lidar_usb.time.sleep",
            side_effect=KeyboardInterrupt,
        ), patch.object(
            Path, "replace", publish
        ):
            call_command(
                "lidar_usb",
                mode="real",
                port="FIXTURE_A1",
                revision="A1M8 fixture only",
                stdout=io.StringIO(),
            )
        active = next(s for s in snapshots if s["acquisition"]["state"] == "active")
        self.assertEqual(active["source"], "real")
        self.assertEqual(active["unit"], "mm")
        self.assertEqual([p["angle_deg"] for p in active["points"]], [0, 90])
        self.assertTrue(
            all(p["quality"] == 20 and p["distance"] == 1000 for p in active["points"])
        )
        self.assertIsNotNone(active["captured_at"])
        self.assertLess(active["age_ms"], 2000)
        self.assertTrue(active["acquisition"]["sensor_identified"])
        self.assertEqual(active["reader"]["host"], local_host())
        self.assertEqual(snapshots[-1]["acquisition"]["state"], "interrupted")
        self.assertTrue(device.closed)

    def test_authorization_and_confirmation_precede_provider_construction(self):
        for enabled, confirmation in [("0", "INICIAR A1"), ("1", "cancel")]:
            with patch.dict(os.environ, {"SEMI_LIDAR_DIAGNOSTICS": enabled}), patch(
                "builtins.input", return_value=confirmation
            ), patch(
                "apps.agriculture.management.commands.lidar_usb.SerialLidarProvider"
            ) as provider:
                with self.assertRaises(CommandError):
                    call_command(
                        "lidar_usb",
                        mode="real",
                        port="FIXTURE_A1",
                        revision="fixture",
                        stdout=io.StringIO(),
                    )
                provider.assert_not_called()

    def test_duplicate_reader_rejected_before_device_open_and_lock_released(self):
        with reader_lock(self.path):
            with self.assertRaises(RuntimeError):
                with reader_lock(self.path):
                    pass
        with reader_lock(self.path):
            pass

    def test_shared_remote_file_is_rejected_without_mock_fallback(self):
        data = frame(
            "valid", [{"angle_deg": 0, "distance": 1000, "quality": 20, "valid": True}]
        )
        data["reader"] = {"host": "fixture-other-machine"}
        self.path.write_text(json.dumps(data))
        result = registry.real_lidar.latest()
        self.assertEqual(result["source"], "real")
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["valid"])

    def test_complete_revolution_without_valid_points_is_not_a_scan(self):
        device = FakeSerial()
        reader = SerialLidarProvider(
            "FIXTURE_A1", "fixture", serial_factory=lambda **k: device
        )
        reader.start(confirmed=True)
        device.data.extend(
            packet(0, distance=0) + packet(90, quality=0, start=False) + packet(0)
        )
        result = reader.read_once()
        self.assertFalse(result["valid"])
        self.assertEqual(result["points"], [])
        self.assertEqual(result["status"], "no_data")
        reader.close()
