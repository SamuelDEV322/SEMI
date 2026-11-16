from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from .test_gate3 import SetupTests
from .models import Plot, SamplingPoint, Sample, TerrainZone, SurfaceTrial


@override_settings(DEBUG=True)
class SectorTests(TestCase):
    setUp = SetupTests.setUp
    post = SetupTests.post

    def test_optional_sector_and_position(self):
        self.post("start")
        self.assertEqual(self.post("point", name="Entrada").status_code, 200)
        point = SamplingPoint.objects.get()
        self.assertIsNone(point.zone_id)
        self.assertIsNone(point.x)
        self.assertEqual(point.position_method, "none")
        self.post("capture", point=point.id)
        self.assertEqual(point.samples.count(), 1)

    def test_retire_preserves_point_samples_and_association_history(self):
        self.post("demo")
        self.post("sector", name="Zona alta")
        zone = TerrainZone.objects.get()
        self.post("point", name="Entrada", zone=zone.id)
        point = SamplingPoint.objects.get()
        self.post("capture", point=point.id)
        self.assertEqual(
            self.post("sector_delete", zone=zone.id, confirmed=True).status_code, 409
        )
        self.post("sector", zone=zone.id, name="Parte alta")
        self.post("sector_archive", zone=zone.id)
        zone.refresh_from_db()
        self.assertTrue(zone.archived)
        self.assertEqual(point.samples.count(), 1)
        self.assertEqual(self.post("point", name="Otro", zone=zone.id).status_code, 400)
        self.post("point", point=point.id, zone=None)
        point.refresh_from_db()
        self.assertIsNone(point.zone_id)
        self.assertTrue(point.zone_history.filter(pk=zone.id).exists())
        self.assertEqual(
            self.post("sector_delete", zone=zone.id, confirmed=True).status_code, 409
        )
        with self.assertRaises(ProtectedError):
            zone.delete()
        self.assertEqual(Sample.objects.count(), 1)
        self.assertEqual(self.c.get("/api/measurements/history/").status_code, 200)

    def test_empty_delete_requires_confirmation(self):
        self.post("start")
        self.post("sector", name="Zona baja")
        zone = TerrainZone.objects.get()
        self.assertEqual(self.post("sector_delete", zone=zone.id).status_code, 400)
        self.assertTrue(TerrainZone.objects.filter(pk=zone.id).exists())
        self.assertEqual(
            self.post("sector_delete", zone=zone.id, confirmed=True).status_code, 200
        )
        self.assertFalse(TerrainZone.objects.exists())

    def test_sector_ids_are_scoped(self):
        self.post("start")
        self.post("sector", name="Original")
        zone = TerrainZone.objects.get()
        self.post("demo")
        for action in [
            "sector_delete",
            "sector_archive",
            "sector_restore",
            "sector_detach",
            "sector",
        ]:
            self.assertEqual(
                self.post(
                    action, zone=zone.id, name="Ajeno", confirmed=True
                ).status_code,
                400,
            )
        self.assertEqual(
            self.post("point", zone=zone.id, name="Ajeno").status_code, 400
        )
        self.assertTrue(
            TerrainZone.objects.filter(
                pk=zone.id, name="Original", archived=False
            ).exists()
        )

    def test_material_categories_not_in_agricultural_api(self):
        self.post("start")
        self.assertEqual(
            self.post("sector", name="Arena", category="sand").status_code, 400
        )
        self.post("sector", name="Entrada")
        zone = self.c.get("/api/setup/").json()["data"]["zones"][0]
        self.assertNotIn("category", zone)
        self.assertNotIn("surface", self.c.get("/api/setup/").json()["data"])

    def test_trial_has_own_subsystem_and_never_changes_sector(self):
        self.post("demo")
        self.post("sector", name="Sector norte")
        h = {"HTTP_X_SEMI_PLOT": str(self.plot), "HTTP_X_CSRFTOKEN": self.token}
        r = self.c.post(
            "/api/demo/surface/",
            {"state": "sand", "conservative": True},
            format="json",
            **h
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["data"]["physical_detection"])
        self.assertEqual(Plot.objects.get(pk=self.plot).surface, "inactive")
        self.assertEqual(SurfaceTrial.objects.get().state, "sand")
        self.assertEqual(TerrainZone.objects.get().category, "")
        self.assertEqual(
            self.c.get("/api/robot/status/", **h).json()["data"]["control"]["action"],
            "stop",
        )

    def test_historical_material_cannot_be_deleted_or_restored(self):
        self.post("demo")
        z = TerrainZone.objects.create(
            plot_id=self.plot,
            name="Arena histórica",
            category="sand",
            archived=True,
            historical_surface=True,
        )
        self.assertEqual(
            self.post("sector_delete", zone=z.id, confirmed=True).status_code, 409
        )
        self.assertEqual(self.post("sector_restore", zone=z.id).status_code, 400)
        self.assertTrue(
            TerrainZone.objects.filter(pk=z.id, category="sand", archived=True).exists()
        )

    def test_bulk_unlink_preserves_history(self):
        self.post("start")
        self.post("sector", name="Sector norte")
        z = TerrainZone.objects.get()
        self.post("point", zone=z.id)
        point = SamplingPoint.objects.get()
        self.post("capture", point=point.id)
        self.assertEqual(self.post("sector_detach", zone=z.id).status_code, 400)
        self.assertEqual(
            self.post("sector_detach", zone=z.id, confirmed=True).status_code, 200
        )
        point.refresh_from_db()
        self.assertIsNone(point.zone_id)
        self.assertTrue(point.zone_history.filter(pk=z.id).exists())
        self.assertEqual(point.samples.count(), 1)

    def test_compatible_point_api_assigns_code(self):
        self.post("start")
        response = self.c.post(
            "/api/sampling-points/",
            {"name": "Entrada", "position_method": "none"},
            format="json",
            HTTP_X_CSRFTOKEN=self.token,
            HTTP_X_SEMI_PLOT=str(self.plot),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["code"], "P1")
        self.post("point", name="Centro")
        self.assertEqual(
            set(SamplingPoint.objects.values_list("code", flat=True)), {"P1", "P2"}
        )
