from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import Plot, Sample, SamplingPoint
from .setup_views import robots
import uuid


@override_settings(DEBUG=True)
class SetupTests(TestCase):
    def setUp(self):
        robots.clear()
        self.c = APIClient(enforce_csrf_checks=True)
        self.token = self.c.get("/api/health/").json()["data"]["csrf_token"]
        self.plot = None

    def post(self, action, **data):
        r = self.c.post(
            "/api/setup/",
            {"action": action, **data},
            format="json",
            HTTP_X_CSRFTOKEN=self.token,
            **({"HTTP_X_SEMI_PLOT": str(self.plot)} if self.plot else {}),
        )
        if r.status_code == 200:
            self.plot = r.json()["data"]["id"]
        return r

    def test_first_resume_and_complete(self):
        self.assertIsNone(self.c.get("/api/setup/").json()["data"])
        self.post("start")
        self.post("save", name="Mi cafetal", step=4)
        self.assertEqual(self.c.get("/api/setup/").json()["data"]["step"], 4)
        self.post("complete")
        self.assertTrue(Plot.objects.get().completed)

    def test_isolated_demo_and_readings(self):
        self.post("demo")
        first = self.plot
        self.post("zone", name="Tierra")
        self.post("zone", name="Arena")
        self.post("point", name="Central", x=20, y=50)
        self.post("point", name="Entrada", x=80, y=50)
        points = list(SamplingPoint.objects.filter(plot_id=first))
        self.post("capture", point=points[0].id)
        self.assertEqual(points[0].samples.count(), 1)
        self.assertEqual(points[1].samples.count(), 0)
        self.post("demo")
        self.assertNotEqual(first, self.plot)
        self.assertEqual(Plot.objects.get(pk=self.plot).points.count(), 0)
        self.assertEqual(Sample.objects.count(), 1)
        self.assertEqual(self.post("capture", point=points[0].id).status_code, 400)

    def test_surface_stop_and_no_geofence(self):
        self.post("demo")
        p = Plot.objects.get(pk=self.plot)
        r = robots.setdefault(
            p.id,
            __import__(
                "adapters.mock", fromlist=["MockRobotProvider"]
            ).MockRobotProvider(),
        )
        session = str(uuid.uuid4())

        def command(seq):
            state = r.status()["control"]
            return self.c.post(
                "/api/control/command/",
                {
                    "mode": "demonstration",
                    "action": "forward",
                    "speed": "low",
                    "session_id": session,
                    "seq": seq,
                    "epoch": state["epoch"],
                    "window_id": state["window_id"],
                },
                format="json",
                HTTP_X_SEMI_PLOT=str(p.id),
                HTTP_X_CSRFTOKEN=self.token,
            )

        self.assertEqual(command(1).status_code, 200)  # no points or position required
        self.post("surface", surface="sand")
        self.assertEqual(r.status()["control"]["action"], "stop")
        self.assertEqual(command(2).status_code, 409)
        self.post("surface", surface="soil")
        self.assertEqual(command(3).status_code, 200)
        self.post("surface", surface="lost")
        self.assertEqual(r.status()["control"]["action"], "stop")
        self.assertFalse(r.status()["hardware_connected"])
        self.post("surface", surface="unknown", conservative=True)
        self.assertEqual(command(4).status_code, 409)
        self.post("surface", surface="unknown", conservative=False)
        self.assertEqual(command(5).status_code, 200)
        self.post("surface", surface="soil")
        self.assertEqual(self.post("capture", point=None).status_code, 400)

    def test_scope_prevents_cross_plot_access(self):
        self.post("start")
        primary = self.plot
        self.post("point", name="Original", x=0, y=0)
        original = SamplingPoint.objects.get(plot_id=primary)
        original.position_method = "none"
        original.x = original.y = None
        original.save()
        self.post("point", point=original.id, x=25, y=75)
        original.refresh_from_db()
        self.assertEqual(original.position_method, "manual_schematic")
        self.post("demo")
        headers = {"HTTP_X_SEMI_PLOT": str(self.plot)}
        self.assertEqual(
            self.c.get("/api/sampling-points/", **headers).json()["data"], []
        )
        self.assertEqual(
            self.c.get(f"/api/sampling-points/{original.id}/", **headers).status_code,
            404,
        )
        self.assertEqual(
            self.c.get("/api/measurements/history/", **headers).json()["data"], []
        )
        self.assertEqual(
            self.post("point", point=original.id, x=40, y=40).status_code, 400
        )
        self.assertTrue(
            SamplingPoint.objects.filter(pk=original.id, plot_id=primary).exists()
        )

    @override_settings(DEBUG=False)
    def test_tutorial_demo_disabled_outside_development(self):
        self.assertEqual(self.post("demo").status_code, 403)

    def test_demo_scenarios_are_scoped(self):
        self.post("start")
        primary = self.plot
        self.post("demo")
        demo = self.plot
        headers = {"HTTP_X_SEMI_PLOT": str(demo), "HTTP_X_CSRFTOKEN": self.token}
        response = self.c.post(
            "/api/demo/scenario/", {"scenario": "no_data"}, format="json", **headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            self.c.get("/api/measurements/latest/", **headers).json()["data"]
        )
        self.assertEqual(
            self.c.get("/api/lidar/latest/", **headers).json()["data"]["points"], []
        )
        self.assertIsNone(
            self.c.get("/api/robot/status/", **headers).json()["data"]["telemetry"][
                "battery"
            ]["value"]
        )
        self.assertEqual(self.c.get("/api/setup/").json()["data"]["id"], primary)
