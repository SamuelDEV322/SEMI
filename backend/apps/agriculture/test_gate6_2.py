"""Software-only domain isolation, command contracts and bounded rack intentions."""

import uuid
from unittest.mock import patch
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from adapters import registry
from adapters.rack import MockRackProvider
from .models import Sample


@override_settings(
    SEMI_MODE="demonstration", SEMI_DEV_TOOLS=True, SEMI_LIDAR_SOURCE="mock"
)
class DecoupledControlTests(TestCase):
    def setUp(self):
        monotonic = patch("adapters.mock.time.monotonic", return_value=100)
        monotonic.start()
        self.addCleanup(monotonic.stop)
        registry.robot.reset()
        self.c = APIClient(enforce_csrf_checks=True)
        self.csrf = self.c.get("/api/health/").json()["data"]["csrf_token"]
        self.session = str(uuid.uuid4())

    def post(self, path, data):
        return self.c.post(path, data, format="json", HTTP_X_CSRFTOKEN=self.csrf)

    def state(self):
        return self.c.get("/api/robot/status/").json()["data"]

    def rack_command(self, action="up", seq=1, **changes):
        rack = self.state()["rack"]
        data = dict(
            domain="rack",
            mode="demonstration",
            action=action,
            device_id=rack["device_id"],
            request_id=str(uuid.uuid4()),
            session_id=self.session,
            seq=seq,
            epoch=rack["control"]["epoch"],
            window_id=rack["control"]["window_id"],
            max_duration_ms=0 if action == "stop" else 450,
        )
        return {**data, **changes}

    def traction_command(self, action="forward", seq=1, **changes):
        control = self.state()["control"]
        return dict(
            mode="demonstration",
            action=action,
            speed="low",
            session_id=self.session,
            seq=seq,
            epoch=control["epoch"],
            window_id=control["window_id"],
            **changes
        )

    def scenario(self, domain, scenario):
        response = self.post(
            "/api/demo/scenario/", dict(domain=domain, scenario=scenario)
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_startup_is_stopped_and_no_physical_confirmation(self):
        state = self.state()
        self.assertEqual(state["control"]["action"], "stop")
        self.assertEqual(state["rack"]["state"], "stopped_simulated")
        self.assertFalse(state["rack"]["physical_authorized"])
        self.assertEqual(state["rack"]["execution_state"], "unverified")

    def test_lidar_failure_does_not_stop_or_disable_either_actuator(self):
        self.assertEqual(
            self.post("/api/control/command/", self.traction_command()).status_code, 200
        )
        self.assertEqual(
            self.post("/api/control/command/", self.rack_command()).status_code, 200
        )
        for scenario in ["no_data", "disconnected", "error", "stale"]:
            self.scenario("lidar", scenario)
            self.assertEqual(self.state()["control"]["action"], "forward")
            self.assertEqual(self.state()["rack"]["control"]["action"], "up")
        self.assertEqual(
            self.post(
                "/api/control/command/", self.traction_command(seq=2)
            ).status_code,
            200,
        )
        self.assertEqual(
            self.post("/api/control/command/", self.rack_command(seq=2)).status_code,
            200,
        )

    def test_rack_fault_leaves_traction_and_lidar_unchanged(self):
        self.post("/api/control/command/", self.traction_command())
        self.scenario("rack", "error")
        self.assertEqual(self.state()["control"]["action"], "forward")
        self.assertEqual(self.state()["rack"]["state"], "error")
        self.assertTrue(self.c.get("/api/lidar/latest/").json()["data"]["valid"])
        self.assertEqual(
            self.post("/api/control/command/", self.rack_command()).status_code, 503
        )

    def test_traction_link_failure_leaves_rack_and_lidar_available(self):
        self.scenario("traction", "disconnected")
        self.assertEqual(
            self.post("/api/control/command/", self.rack_command()).status_code, 200
        )
        self.assertTrue(self.c.get("/api/lidar/latest/").json()["data"]["valid"])

    def test_general_stop_cancels_both_and_invalidates_old_leases(self):
        self.post("/api/control/command/", self.traction_command())
        self.post("/api/control/command/", self.rack_command())
        late_rack = self.rack_command(seq=2)
        late_motion = self.traction_command(seq=2)
        response = self.post(
            "/api/control/command/", self.traction_command("stop", seq=3, domain="all")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["hardware_acted"])
        self.assertEqual(self.state()["rack"]["control"]["action"], "stop")
        self.assertEqual(self.state()["control"]["action"], "stop")
        self.assertEqual(self.post("/api/control/command/", late_rack).status_code, 409)
        self.assertEqual(
            self.post("/api/control/command/", late_motion).status_code, 409
        )

    def test_individual_release_does_not_stop_other_domain(self):
        self.post("/api/control/command/", self.traction_command())
        self.post("/api/control/command/", self.rack_command())
        self.post("/api/control/command/", self.rack_command("stop", seq=2))
        self.assertEqual(self.state()["control"]["action"], "forward")
        self.post("/api/control/command/", self.rack_command(seq=3))
        self.post("/api/control/command/", self.traction_command("stop", seq=2))
        self.assertEqual(self.state()["rack"]["control"]["action"], "up")

    def test_rack_opposites_duplicates_and_request_conflict(self):
        data = self.rack_command()
        self.assertEqual(self.post("/api/control/command/", data).status_code, 200)
        response = self.post("/api/control/command/", data)
        self.assertEqual(response.json()["data"]["acceptance"], "duplicate")
        self.assertEqual(
            self.post("/api/control/command/", {**data, "action": "down"}).status_code,
            409,
        )
        self.assertEqual(
            self.post(
                "/api/control/command/", self.rack_command("down", seq=2)
            ).status_code,
            409,
        )
        self.post("/api/control/command/", self.rack_command("stop", seq=3))
        self.assertEqual(
            self.post(
                "/api/control/command/", self.rack_command("down", seq=4)
            ).status_code,
            200,
        )

    def test_contract_validation_and_csrf_remain_enabled(self):
        for changes in [
            {"max_duration_ms": 451},
            {"max_duration_ms": 0},
            {"action": "forward"},
            {"device_id": "different-demo"},
            {"unexpected": True},
        ]:
            self.assertEqual(
                self.post(
                    "/api/control/command/", self.rack_command(**changes)
                ).status_code,
                400,
            )
        self.assertEqual(
            self.c.post(
                "/api/control/command/", self.rack_command(), format="json"
            ).status_code,
            403,
        )
        self.assertEqual(
            self.post(
                "/api/control/command/", self.traction_command(domain="all")
            ).status_code,
            400,
        )

    def test_device_movement_route_remains_authenticated(self):
        self.assertIn(self.c.get("/api/device/commands/next/").status_code, [401, 403])

    @override_settings(SEMI_MODE="operational")
    def test_real_rack_forbidden_even_with_demo_payload(self):
        for action in ["up", "down", "stop"]:
            data = dict(
                domain="rack",
                mode="demonstration",
                action=action,
                device_id="example",
                request_id=str(uuid.uuid4()),
                session_id=self.session,
                seq=1,
                epoch=0,
                window_id="",
                max_duration_ms=450,
            )
            self.assertEqual(self.post("/api/control/command/", data).status_code, 403)
        self.assertFalse(self.state()["rack"]["available"])

    def test_lidar_geometry_is_repeatable_and_does_not_persist_points(self):
        before = Sample.objects.count()
        first = self.c.get("/api/lidar/latest/").json()["data"]
        self.scenario("traction", "disconnected")
        self.scenario("rack", "error")
        second = self.c.get("/api/lidar/latest/").json()["data"]
        self.assertEqual(first["points"], second["points"])
        self.assertEqual(len(first["points"]), 120)
        self.assertEqual(first["source"], "mock")
        self.assertTrue(
            all(0 < p["distance"] <= first["max_range_mm"] for p in first["points"])
        )
        self.assertEqual(Sample.objects.count(), before)

    def test_rack_timeouts_duplicates_and_reconnect_with_monotonic_clock(self):
        with patch("adapters.mock.time.monotonic", return_value=100) as clock:
            rack = MockRackProvider("fake-only")
            lease = rack.status()["control"]
            data = {
                **self.rack_command(),
                "device_id": "fake-only",
                "epoch": lease["epoch"],
                "window_id": lease["window_id"],
                "max_duration_ms": 300,
            }
            self.assertEqual(rack.command(data)[1], 200)
            clock.return_value = 100.2
            self.assertEqual(rack.command(data)[0]["acceptance"], "duplicate")
            clock.return_value = 100.301
            self.assertEqual(rack.status()["control"]["action"], "stop")
            rack.set_scenario("disconnected")
            rack.set_scenario("connected")
            self.assertEqual(
                rack.command({**data, "seq": 2, "request_id": str(uuid.uuid4())})[1],
                409,
            )
            self.assertEqual(rack.status()["state"], "stopped_simulated")

    def test_long_session_bounded_ledger_does_not_disable_stop(self):
        rack = MockRackProvider("fake-only")
        with patch("adapters.mock.time.monotonic", return_value=100):
            original = None
            for seq in range(300):
                lease = rack.status()["control"]
                data = {
                    **self.rack_command(seq=seq),
                    "device_id": "fake-only",
                    "epoch": lease["epoch"],
                    "window_id": lease["window_id"],
                }
                original = original or data
                self.assertEqual(rack.command(data)[1], 200)
            self.assertLessEqual(len(rack.requests), 256)
            self.assertEqual(rack.command(original)[1], 409)
            self.assertEqual(
                rack.command(
                    {
                        **data,
                        "action": "stop",
                        "seq": 301,
                        "request_id": str(uuid.uuid4()),
                        "max_duration_ms": 0,
                    }
                )[1],
                200,
            )
            self.assertEqual(rack.status()["control"]["action"], "stop")
