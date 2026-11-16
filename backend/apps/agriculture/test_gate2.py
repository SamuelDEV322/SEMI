from django.test import TestCase, TransactionTestCase, override_settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from rest_framework.test import APIClient
from adapters import registry
from .models import Sample, SamplingPoint


@override_settings(
    SEMI_MODE="demonstration", SEMI_DEV_TOOLS=True, SEMI_LIDAR_SOURCE="mock"
)
class PointTests(TestCase):
    def setUp(self):
        registry.robot.reset()
        self.client = APIClient(enforce_csrf_checks=True)
        self.token = self.client.get("/api/health/").json()["data"]["csrf_token"]

    def post(self, path, data):
        return self.client.post(path, data, format="json", HTTP_X_CSRFTOKEN=self.token)

    def test_point_capture_latest_without_sample_coordinates(self):
        p = self.post(
            "/api/sampling-points/",
            {"name": "Zona D", "position_method": "manual_schematic", "x": 40, "y": 60},
        ).json()["data"]
        old = Sample.objects.create(
            point_label="Zona D",
            sampling_point_id=p["id"],
            captured_at=timezone.now() - timezone.timedelta(hours=1),
            nitrogen=9,
        )
        r = self.post("/api/demo/capture/", {"sampling_point": p["id"]})
        self.assertEqual(r.status_code, 201)
        latest = self.client.get("/api/sampling-points/").json()["data"][0][
            "latest_sample"
        ]
        self.assertEqual(latest["id"], r.json()["data"]["id"])
        self.assertNotEqual(latest["id"], old.id)
        self.assertIsNone(latest["x"])
        self.assertEqual(SamplingPoint.objects.get().x, 40)
        filtered = self.client.get(
            "/api/measurements/history/",
            {
                "point": p["id"],
                "since": (timezone.now() - timezone.timedelta(minutes=5)).isoformat(),
            },
        ).json()["data"]
        self.assertEqual(len(filtered), 1)

    def test_point_position_validation_and_no_delete(self):
        self.assertEqual(
            self.post(
                "/api/sampling-points/",
                {
                    "name": "Bad",
                    "position_method": "manual_schematic",
                    "x": 200,
                    "y": 2,
                },
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post("/api/sampling-points/", {"name": "Good"}).status_code, 201
        )
        self.assertEqual(
            self.post("/api/sampling-points/", {"name": "Good"}).status_code, 400
        )
        self.assertEqual(
            self.client.delete(
                "/api/sampling-points/1/", HTTP_X_CSRFTOKEN=self.token
            ).status_code,
            405,
        )

    def test_related_sample_without_text_label_and_location_update(self):
        point = SamplingPoint.objects.create(name="Identidad")
        response = self.post(
            "/api/npk/samples/",
            {
                "sampling_point": point.id,
                "captured_at": timezone.now().isoformat(),
                "nitrogen": 20,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["point_label"], "Identidad")
        response = self.client.patch(
            f"/api/sampling-points/{point.id}/",
            {"position_method": "manual_schematic", "x": 40, "y": 70},
            format="json",
            HTTP_X_CSRFTOKEN=self.token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["latest_sample"]["nitrogen"], 20)


@override_settings(
    SEMI_MODE="demonstration", SEMI_DEV_TOOLS=True, SEMI_LIDAR_SOURCE="mock"
)
class MigrationPreservationTests(TransactionTestCase):
    def test_non_destructive_association_and_conflicts(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("agriculture", "0001_initial")])
        apps = executor.loader.project_state([("agriculture", "0001_initial")]).apps
        Old = apps.get_model("agriculture", "Sample")
        now = timezone.now()
        a = Old.objects.create(
            point_label="Safe",
            captured_at=now,
            nitrogen=4,
            position_method="manual_schematic",
            x=12,
            y=22,
        )
        b = Old.objects.create(point_label="Safe", captured_at=now, nitrogen=7)
        for x in [10, 90]:
            Old.objects.create(
                point_label="Ambiguous",
                captured_at=now,
                nitrogen=3,
                position_method="manual_schematic",
                x=x,
                y=30,
            )
        executor = MigrationExecutor(connection)
        executor.migrate([("agriculture", "0002_sampling_points")])
        self.assertEqual(Sample.objects.count(), 4)
        self.assertEqual(Sample.objects.get(pk=a.pk).nitrogen, 4)
        self.assertEqual(
            Sample.objects.get(pk=a.pk).sampling_point_id,
            Sample.objects.get(pk=b.pk).sampling_point_id,
        )
        self.assertTrue(
            all(
                x is None
                for x in Sample.objects.filter(point_label="Ambiguous").values_list(
                    "sampling_point_id", flat=True
                )
            )
        )
