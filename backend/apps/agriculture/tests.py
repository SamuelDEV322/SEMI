import os
import subprocess
import sys
import uuid
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from adapters import registry
from .models import Sample


@override_settings(
    SEMI_MODE="demonstration", SEMI_DEV_TOOLS=True, SEMI_LIDAR_SOURCE="mock"
)
class GateOneTests(TestCase):
    def setUp(self):
        registry.robot.reset()
        registry.lidar_sources.select("mock")
        self.client = APIClient(enforce_csrf_checks=True)
        self.token = self.client.get("/api/health/").json()["data"]["csrf_token"]
        self.session = str(uuid.uuid4())

    def post(self, path, data):
        return self.client.post(path, data, format="json", HTTP_X_CSRFTOKEN=self.token)

    def order(self, **changes):
        state = self.client.get("/api/robot/status/").json()["data"]["control"]
        data = {
            "mode": "demonstration",
            "action": "forward",
            "speed": "low",
            "session_id": self.session,
            "seq": 1,
            "epoch": state["epoch"],
            "window_id": state["window_id"],
        }
        data.update(changes)
        return data

    def test_all_get_endpoints_and_no_hardware(self):
        for path in [
            "health/",
            "robot/status/",
            "measurements/latest/",
            "measurements/history/",
            "npk/samples/",
            "lidar/latest/",
        ]:
            response = self.client.get("/api/" + path)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.json()["mode"], "demonstration")
        state = self.client.get("/api/robot/status/").json()["data"]
        self.assertFalse(state["hardware_connected"])
        self.assertFalse(state["capabilities"]["physical_motion"])

    def test_empty_database_preserves_absence(self):
        self.assertIsNone(self.client.get("/api/measurements/latest/").json()["data"])
        self.assertEqual(self.client.get("/api/npk/samples/").json()["data"], [])

    def test_seed_is_repeatable(self):
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Sample.objects.count(), 12)
        self.assertEqual(set(Sample.objects.values_list("source", flat=True)), {"mock"})

    def test_capture_is_persistent_and_has_no_fabricated_position(self):
        response = self.post("/api/demo/capture/", {"point_label": "Zona de ensayo"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Sample.objects.count(), 1)
        saved = self.client.get("/api/npk/samples/").json()["data"][0]
        self.assertEqual(saved["point_label"], "Zona de ensayo")
        self.assertEqual(saved["position_method"], "none")
        self.assertIsNone(saved["x"])

    def test_samples_accept_null_without_converting_to_zero(self):
        payload = {
            "captured_at": timezone.now().isoformat(),
            "point_label": "P1",
            "nitrogen": None,
            "phosphorus": None,
            "potassium": 0,
            "soil_moisture": None,
            "position_method": "none",
            "source": "mock",
        }
        response = self.post("/api/npk/samples/", payload)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()["data"]["nitrogen"])
        self.assertEqual(response.json()["data"]["potassium"], 0)

    def test_real_sample_rejected(self):
        self.assertEqual(
            self.post("/api/npk/samples/", {"source": "real"}).status_code, 403
        )

    def test_units_are_not_silently_relabelled(self):
        payload = {
            "captured_at": timezone.now().isoformat(),
            "point_label": "P1",
            "nitrogen": 2,
            "npk_unit": "ppm",
        }
        self.assertEqual(self.post("/api/npk/samples/", payload).status_code, 400)

    def test_invalid_position_rejected(self):
        payload = {
            "captured_at": timezone.now().isoformat(),
            "point_label": "P1",
            "nitrogen": 2,
            "position_method": "manual_schematic",
            "x": 120,
            "y": 10,
        }
        self.assertEqual(self.post("/api/npk/samples/", payload).status_code, 400)
        payload.update(position_method="gnss", x=1)
        self.assertEqual(self.post("/api/npk/samples/", payload).status_code, 400)

    def test_nonfinite_and_out_of_range_rejected(self):
        payload = {
            "captured_at": timezone.now().isoformat(),
            "point_label": "P1",
            "nitrogen": "NaN",
        }
        self.assertEqual(self.post("/api/npk/samples/", payload).status_code, 400)
        payload.update(nitrogen=1, soil_moisture=101)
        self.assertEqual(self.post("/api/npk/samples/", payload).status_code, 400)

    def test_missing_csrf_rejected(self):
        self.assertEqual(
            self.client.post(
                "/api/control/command/", self.order(), format="json"
            ).status_code,
            403,
        )

    def test_physical_mode_is_forbidden(self):
        response = self.post("/api/control/command/", self.order(mode="hardware"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(registry.robot.action, "stop")

    def test_extra_physical_fields_rejected(self):
        self.assertEqual(
            self.post("/api/control/command/", self.order(gpio=12)).status_code, 400
        )

    def test_directional_tracks_are_simulated_only(self):
        response = self.post(
            "/api/control/command/", self.order(action="left", speed="medium")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["track_demand"], [-0.5, 0.5])
        self.assertFalse(response.json()["data"]["hardware_acted"])

    def test_repeated_sequence_rejected(self):
        data = self.order()
        self.assertEqual(self.post("/api/control/command/", data).status_code, 200)
        self.assertEqual(self.post("/api/control/command/", data).status_code, 409)

    def test_other_operator_cannot_move(self):
        self.assertEqual(
            self.post("/api/control/command/", self.order()).status_code, 200
        )
        self.assertEqual(
            self.post(
                "/api/control/command/", self.order(session_id=str(uuid.uuid4()))
            ).status_code,
            409,
        )

    def test_expired_window_rejected(self):
        with patch("adapters.mock.time.monotonic", return_value=100):
            data = self.order()
        with patch("adapters.mock.time.monotonic", return_value=102):
            response = self.post("/api/control/command/", data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(registry.robot.action, "stop")

    def test_command_expires_without_browser_stop(self):
        with patch("adapters.mock.time.monotonic", return_value=100):
            self.assertEqual(
                self.post("/api/control/command/", self.order()).status_code, 200
            )
        with patch("adapters.mock.time.monotonic", return_value=101):
            state = registry.robot.status()
        self.assertEqual(state["control"]["action"], "stop")
        self.assertIsNone(state["control"]["owner"])

    def test_stop_invalidates_delayed_move(self):
        old = self.order(seq=3)
        self.assertEqual(
            self.post(
                "/api/control/command/", self.order(action="stop", seq=2)
            ).status_code,
            200,
        )
        self.assertEqual(self.post("/api/control/command/", old).status_code, 409)

    def test_scenarios_and_reconnect_do_not_resume(self):
        self.post("/api/control/command/", self.order())
        self.post("/api/demo/scenario/", {"scenario": "disconnected"})
        self.assertEqual(
            self.post("/api/control/command/", self.order(seq=2)).status_code, 503
        )
        self.assertIsNone(self.client.get("/api/measurements/latest/").json()["data"])
        self.post("/api/demo/scenario/", {"scenario": "connected"})
        self.assertEqual(registry.robot.status()["control"]["action"], "stop")

    def test_no_data_and_error_are_explicit(self):
        self.post("/api/demo/scenario/", {"scenario": "no_data"})
        self.assertIsNone(self.client.get("/api/measurements/latest/").json()["data"])
        self.assertEqual(
            self.client.get("/api/lidar/latest/").json()["data"]["points"], []
        )
        self.post("/api/demo/scenario/", {"scenario": "error"})
        self.assertEqual(self.client.get("/api/measurements/latest/").status_code, 503)

    def test_scan_contract_and_staleness(self):
        scan = self.client.get("/api/lidar/latest/").json()["data"]
        self.assertEqual(scan["source"], "mock")
        self.assertEqual(scan["unit"], "mm")
        self.assertEqual(len(scan["points"]), 120)
        self.assertTrue(
            all(0 <= p["angle_deg"] < 360 and p["valid"] for p in scan["points"])
        )
        self.post("/api/demo/scenario/", {"scenario": "stale"})
        self.assertEqual(
            self.client.get("/api/lidar/latest/").json()["data"]["freshness"], "stale"
        )

    def test_history_limit_is_bounded(self):
        self.assertEqual(
            self.client.get("/api/measurements/history/?limit=100000").status_code, 400
        )

    def test_invalid_operational_mock_source_prevents_startup(self):
        env = {
            **os.environ,
            "SEMI_MODE": "operational",
            "SEMI_LIDAR_SOURCE": "mock",
            "DJANGO_SETTINGS_MODULE": "config.settings",
        }
        from pathlib import Path

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from django.conf import settings; print(settings.INSTALLED_APPS)",
            ],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Operational mode requires", result.stderr)
