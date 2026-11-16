"""MVP profile tests. Hardware is never opened; real provenance fixtures are test-only."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from adapters import registry
from .models import Plot, SamplingPoint, Sample


@override_settings(
    SEMI_MODE="operational", SEMI_DEV_TOOLS=False, SEMI_LIDAR_SOURCE="real"
)
class OperationalTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.token = self.client.get("/api/health/").json()["data"]["csrf_token"]
        self.plot = Plot.objects.create(name="Mi cafetal")
        self.point = SamplingPoint.objects.create(
            plot=self.plot, code="P1", name="Lugar"
        )

    def post(self, path, data):
        return self.client.post(path, data, format="json", HTTP_X_CSRFTOKEN=self.token)

    def test_honest_capabilities_no_fabricated_battery_or_stop(self):
        profile = self.client.get("/api/health/").json()
        self.assertEqual(profile["mode"], "operational")
        self.assertFalse(profile["data"]["dev_tools"])
        self.assertFalse(profile["data"]["npk_capture"])
        robot = self.client.get("/api/robot/status/").json()["data"]
        self.assertEqual(robot["source"], "real")
        self.assertFalse(robot["hardware_connected"])
        self.assertIsNone(robot["control"]["action"])
        self.assertIsNone(robot["telemetry"]["battery"]["value"])
        self.assertFalse(robot["capabilities"]["manual_control"])
        self.assertNotIn("surface_trial", robot)

    def test_no_mock_fallback_or_automatic_serial_open(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            "os.environ", {"SEMI_LIDAR_SPOOL": str(Path(folder) / "missing.json")}
        ), patch("adapters.a1.SerialLidarProvider.start") as start:
            scan = self.client.get("/api/lidar/latest/").json()["data"]
        self.assertEqual((scan["source"], scan["status"]), ("real", "disconnected"))
        self.assertEqual(scan["points"], [])
        self.assertFalse(scan["valid"])
        start.assert_not_called()

    def test_sources_are_immutable_and_demo_api_is_blocked(self):
        for source in ["mock", "replay", "real"]:
            self.assertEqual(
                self.post("/api/lidar/source/", {"source": source}).status_code, 405
            )
        self.assertEqual(
            self.post("/api/demo/scenario/", {"scenario": "connected"}).status_code, 403
        )
        self.assertEqual(
            self.post(
                "/api/demo/capture/", {"sampling_point": self.point.id}
            ).status_code,
            403,
        )
        self.assertEqual(self.post("/api/setup/", {"action": "demo"}).status_code, 403)
        self.assertEqual(self.client.get("/api/demo/surface/").status_code, 403)
        self.assertEqual(Plot.objects.count(), 1)

    def test_capture_cannot_generate_or_accept_fake_real_samples(self):
        self.assertEqual(
            self.post(
                "/api/measurements/capture/", {"sampling_point": self.point.id}
            ).status_code,
            503,
        )
        self.assertEqual(
            self.post(
                "/api/setup/", {"action": "capture", "point": self.point.id}
            ).status_code,
            503,
        )
        for source in ["mock", "real"]:
            self.assertEqual(
                self.post(
                    "/api/npk/samples/",
                    {"sampling_point": self.point.id, "source": source, "nitrogen": 34},
                ).status_code,
                403,
            )
        self.assertEqual(Sample.objects.count(), 0)

    def test_commands_have_no_physical_or_simulated_side_effect_in_operational_mode(
        self,
    ):
        for mode, status in [
            ("operational", 503),
            ("demonstration", 403),
            ("real", 403),
        ]:
            for action in ["forward", "backward", "left", "right", "stop"]:
                response = self.post(
                    "/api/control/command/",
                    {
                        "mode": mode,
                        "action": action,
                        "speed": "low",
                        "session_id": "d4dc3fb6-7b9c-4f57-b3b9-c176a551e095",
                        "seq": 1,
                        "epoch": 0,
                        "window_id": "",
                    },
                )
                self.assertEqual(response.status_code, status)
                self.assertNotIn("data", response.json())
        self.assertIsNone(registry.unconfigured_robot.action)

    def test_old_mock_history_is_preserved_but_not_misrepresented(self):
        old = Sample.objects.create(
            sampling_point=self.point,
            point_label="Lugar",
            captured_at=timezone.now(),
            nitrogen=34,
            source="mock",
        )
        for path in ["/api/measurements/history/", "/api/npk/samples/"]:
            self.assertEqual(self.client.get(path).json()["data"], [])
        self.assertIsNone(self.client.get("/api/measurements/latest/").json()["data"])
        self.assertIsNone(
            self.client.get("/api/sampling-points/").json()["data"][0]["latest_sample"]
        )
        self.assertIsNone(
            self.client.get("/api/setup/").json()["data"]["points"][0]["latest_sample"]
        )
        self.assertTrue(Sample.objects.filter(pk=old.pk).exists())
        # This row is a test fixture, never loaded into a user's SQLite.
        real = Sample.objects.create(
            sampling_point=self.point,
            point_label="Lugar",
            captured_at=timezone.now(),
            source="real",
            nitrogen=12,
        )
        self.assertEqual(
            self.client.get("/api/measurements/latest/").json()["data"]["id"], real.id
        )
        self.assertEqual(
            len(self.client.get("/api/measurements/history/").json()["data"]), 1
        )

    def test_demo_header_does_not_switch_robot_or_modify_demo_plot(self):
        demo = Plot.objects.create(name="Old tutorial", demo=True)
        request = self.client.get("/api/setup/", HTTP_X_SEMI_PLOT=str(demo.id))
        self.assertEqual(request.json()["data"]["id"], self.plot.id)
        robot = self.client.get(
            "/api/robot/status/", HTTP_X_SEMI_PLOT=str(demo.id)
        ).json()["data"]
        self.assertEqual(robot["source"], "real")
        self.assertIsNone(robot["control"]["action"])
