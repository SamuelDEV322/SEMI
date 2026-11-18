import copy
import io
import json
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
from django.core.management import call_command, CommandError
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.agriculture.models import Plot, SamplingPoint, Sample
from .models import Device, DeviceMessage
from .services import StopCommandBroker, DeviceTelemetryService
from adapters.esp32_diagnostic import Esp32DiagnosticProvider


@override_settings(
    SEMI_MODE="operational", SEMI_DEVICE_INTEGRATION="diagnostic", SEMI_DEV_TOOLS=False
)
class DeviceTests(TestCase):
    def setUp(self):
        self.plot = Plot.objects.create(name="Prueba aislada")
        self.point = SamplingPoint.objects.create(plot=self.plot, name="P1 fixture")
        self.device = Device.objects.create(device_id="test-device", plot=self.plot)
        self.secret = secrets.token_urlsafe(
            32
        )  # Generated per test, never a real credential.
        self.config = override_settings(
            SEMI_DEVICE_TOKENS={self.device.device_id: self.secret}
        )
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.credentials(
            HTTP_X_SEMI_DEVICE_ID=self.device.device_id,
            HTTP_X_SEMI_DEVICE_TOKEN=self.secret,
        )
        self.lease = patch.object(StopCommandBroker, "TTL_MS", 60000)
        self.lease.start()
        self.addCleanup(self.lease.stop)
        self.session = str(self.device.session_id)

    def payload(self, seq=0):
        return {
            "schema_version": "1.0",
            "session_id": self.session,
            "message_id": str(uuid.uuid4()),
            "seq": seq,
            "measured_at": timezone.now().isoformat(),
            "sampling_point_id": self.point.id,
            "sensors": {
                "soil_moisture_adc": {
                    "value": 1700,
                    "adc_max": 4095,
                    "status": "valid",
                    "sensor_id": "test-fixture",
                }
            },
        }

    def send(self, payload=None):
        return self.client.post(
            "/api/device/telemetry/",
            payload if payload is not None else self.payload(),
            format="json",
        )

    def status_payload(self, seq=0):
        return {
            "schema_version": "1.0",
            "session_id": self.session,
            "message_id": str(uuid.uuid4()),
            "seq": seq,
            "uptime_ms": 1200,
            "firmware": "fixture-only",
            "firmware_state": "ready",
            "capabilities": {"telemetry": True, "motion": True},
        }

    def poll(self, seq=0, **changes):
        values = {
            "schema_version": "1.0",
            "session_id": self.session,
            "request_id": str(uuid.uuid4()),
            "seq": seq,
            **changes,
        }
        return self.client.get("/api/device/commands/next/", values), values

    def test_authentication_missing_invalid_unknown_revoked_and_cookie_only(self):
        for headers in [
            {},
            {
                "HTTP_X_SEMI_DEVICE_ID": "unknown",
                "HTTP_X_SEMI_DEVICE_TOKEN": self.secret,
            },
            {
                "HTTP_X_SEMI_DEVICE_ID": self.device.device_id,
                "HTTP_X_SEMI_DEVICE_TOKEN": secrets.token_urlsafe(32),
            },
        ]:
            client = APIClient(enforce_csrf_checks=True)
            client.credentials(**headers)
            for method, path in [
                ("post", "telemetry"),
                ("post", "status"),
                ("get", "commands/next"),
            ]:
                result = getattr(client, method)(
                    f"/api/device/{path}/", {}, format="json"
                )
                self.assertEqual(result.status_code, 401)
                self.assertEqual(result.json()["error"]["code"], "device_auth_failed")
                self.assertFalse(result.json()["data"]["motion_enabled"])
        Device.objects.filter(pk=self.device.pk).update(enabled=False)
        self.assertEqual(self.send().status_code, 401)
        self.assertEqual(DeviceMessage.objects.count(), 0)

    def test_valid_device_auth_without_csrf_but_browser_writes_remain_protected(self):
        self.assertEqual(self.send().status_code, 201)
        for path in [
            "/api/setup/",
            "/api/control/command/",
            "/api/measurements/capture/",
        ]:
            self.assertEqual(self.client.post(path, {}, format="json").status_code, 403)

    @override_settings(SEMI_DEVICE_INTEGRATION="disabled")
    def test_disabled_integration_is_rejected(self):
        self.assertEqual(self.send().status_code, 403)
        self.assertEqual(DeviceMessage.objects.count(), 0)

    @override_settings(SEMI_MODE="demonstration")
    def test_demo_is_not_fed_real_telemetry(self):
        self.assertEqual(self.send().status_code, 403)
        self.assertEqual(DeviceMessage.objects.count(), 0)

    def test_adc_persistence_original_values_time_source_and_no_fake_npk(self):
        payload = self.payload()
        response = self.send(payload)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(set(body), {"schema_version", "mode", "server_time", "data"})
        row = DeviceMessage.objects.get()
        self.assertEqual(row.payload, payload)
        self.assertEqual(row.sampling_point, self.point)
        self.assertEqual(row.source, "real")
        self.assertIsNotNone(row.received_at)
        self.assertLess(row.measured_at, row.received_at)
        self.assertEqual(Sample.objects.count(), 0)
        self.assertIsNone(self.client.get("/api/measurements/latest/").json()["data"])
        self.assertEqual(self.client.get("/api/npk/samples/").json()["data"], [])

    def test_missing_measurement_clock_stays_null(self):
        payload = self.payload()
        del payload["measured_at"]
        self.assertEqual(self.send(payload).status_code, 201)
        self.assertIsNone(DeviceMessage.objects.get().measured_at)

    def test_unavailable_adc_does_not_require_an_invented_resolution(self):
        payload = self.payload()
        payload["sensors"]["soil_moisture_adc"] = {
            "value": None,
            "status": "unavailable",
        }
        self.assertEqual(self.send(payload).status_code, 201)
        self.assertNotIn(
            "adc_max",
            DeviceMessage.objects.get().payload["sensors"]["soil_moisture_adc"],
        )

    def test_zero_adc_is_preserved_not_missing(self):
        payload = self.payload()
        payload["sensors"]["soil_moisture_adc"]["value"] = 0
        self.assertEqual(self.send(payload).status_code, 201)
        self.assertEqual(
            DeviceMessage.objects.get().payload["sensors"]["soil_moisture_adc"][
                "value"
            ],
            0,
        )

    def test_duplicate_idempotent_and_does_not_refresh_heartbeat(self):
        payload = self.payload()
        first = self.send(payload)
        seen = Device.objects.get().last_seen
        second = self.send(payload)
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertTrue(second.json()["data"]["duplicate"])
        self.assertEqual(
            first.json()["data"]["received_at"], second.json()["data"]["received_at"]
        )
        self.assertEqual(Device.objects.get().last_seen, seen)
        self.assertEqual(DeviceMessage.objects.count(), 1)

    def test_message_conflict_and_old_sequences_rollback(self):
        payload = self.payload(3)
        self.assertEqual(self.send(payload).status_code, 201)
        changed = copy.deepcopy(payload)
        changed["sensors"]["soil_moisture_adc"]["value"] = 3
        self.assertEqual(self.send(changed).json()["error"]["code"], "message_conflict")
        for seq in [0, 2, 3]:
            self.assertEqual(
                self.send(self.payload(seq)).json()["error"]["code"], "sequence_old"
            )
        self.assertEqual(DeviceMessage.objects.count(), 1)
        self.assertEqual(self.send(self.payload(4)).status_code, 201)

    def test_cross_plot_unknown_and_demo_points_rejected(self):
        other = Plot.objects.create(name="Other")
        point = SamplingPoint.objects.create(plot=other, name="Other point")
        demo = Plot.objects.create(name="Demo", demo=True)
        dp = SamplingPoint.objects.create(plot=demo, name="Demo point")
        for point_id in [point.id, dp.id, 999999]:
            payload = self.payload()
            payload["sampling_point_id"] = point_id
            result = self.send(payload)
            self.assertEqual(result.status_code, 400)
            self.assertEqual(result.json()["error"]["code"], "point_not_owned")
        self.assertEqual(DeviceMessage.objects.count(), 0)
        self.assertEqual(Device.objects.get().telemetry_seq, -1)

    def test_ranges_types_unknown_fields_and_invalid_clocks(self):
        mutations = [
            lambda p: p["sensors"].update(
                battery={"voltage_v": 10**500, "status": "valid"}
            ),
            lambda p: p.update(seq=True),
            lambda p: p.update(seq=-1),
            lambda p: p.update(seq="1"),
            lambda p: p.update(measured_at="2026-01-01T12:00:00"),
            lambda p: p.update(
                measured_at=(timezone.now() + timedelta(days=1)).isoformat()
            ),
            lambda p: p.update(nitrogen=34),
            lambda p: p["sensors"].update(npk={"nitrogen": 34}),
            lambda p: p["sensors"]["soil_moisture_adc"].update(value=4096),
            lambda p: p["sensors"]["soil_moisture_adc"].update(value=True),
            lambda p: p["sensors"]["soil_moisture_adc"].update(value=None),
            lambda p: p.update(sensors={}),
            lambda p: p["sensors"].update(
                battery={"voltage_v": 101, "status": "valid"}
            ),
        ]
        for mutate in mutations:
            payload = self.payload()
            mutate(payload)
            self.assertEqual(self.send(payload).status_code, 400, payload)
        self.assertEqual(DeviceMessage.objects.count(), 0)

    def test_invalid_json_duplicate_keys_nan_and_size(self):
        for raw in [
            "{",
            "[]",
            '{"schema_version":"1.0","schema_version":"1.0"}',
            '{"schema_version":"1.0","seq":NaN}',
        ]:
            self.assertEqual(
                self.client.post(
                    "/api/device/telemetry/", raw, content_type="application/json"
                ).status_code,
                400,
            )
        self.assertEqual(
            self.client.post(
                "/api/device/telemetry/", " " * 32769, content_type="application/json"
            ).status_code,
            413,
        )
        self.assertEqual(DeviceMessage.objects.count(), 0)

    def test_preliminary_bridge_payload_is_rejected_without_silent_normalization(self):
        # Fictitious packet matching the reviewed download, not a physical reading.
        old = {
            "device_id": self.device.device_id,
            "reading_id": "fixture-reading",
            "sampling_point_id": self.point.id,
            "soil_adc_raw": 1700,
            "calibrated": False,
            "source": "real",
        }
        response = self.send(old)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "schema_version_unsupported")
        self.assertEqual(DeviceMessage.objects.count(), 0)

    def test_contract_version_mandatory_and_supported(self):
        for version in [None, "2.0", 1]:
            payload = self.payload()
            payload["schema_version"] = version
            self.assertEqual(
                self.send(payload).json()["error"]["code"], "schema_version_unsupported"
            )
        self.assertEqual(DeviceMessage.objects.count(), 0)

    def test_sensor_error_or_absence_persists_without_generating_value(self):
        payload = self.payload()
        payload["sensors"]["soil_moisture_adc"].update(value=None, status="error")
        self.assertEqual(self.send(payload).status_code, 201)
        raw = Esp32DiagnosticProvider(self.plot).status()["telemetry"]["device_reading"]
        self.assertIsNone(raw["sensors"]["soil_moisture_adc"]["value"])
        self.assertEqual(raw["sensors"]["soil_moisture_adc"]["status"], "error")
        self.assertEqual(Sample.objects.count(), 0)

    def test_volts_do_not_become_percent_charge(self):
        payload = self.payload()
        payload["sensors"] = {"battery": {"voltage_v": 24.1, "status": "valid"}}
        self.assertEqual(self.send(payload).status_code, 201)
        telemetry = Esp32DiagnosticProvider(self.plot).status()["telemetry"]
        self.assertIsNone(telemetry["battery"]["value"])
        self.assertEqual(
            telemetry["device_reading"]["sensors"]["battery"]["voltage_v"], 24.1
        )

    def test_heartbeat_status_does_not_authorize_motion(self):
        result = self.client.post(
            "/api/device/status/", self.status_payload(), format="json"
        )
        self.assertEqual(result.status_code, 201)
        robot = self.client.get("/api/robot/status/").json()["data"]
        self.assertEqual(robot["connection"], "diagnostic_online")
        self.assertFalse(robot["capabilities"]["manual_control"])
        self.assertFalse(robot["capabilities"]["physical_motion"])
        self.assertIsNone(robot["control"]["action"])
        self.assertTrue(robot["device"]["declared_capabilities"]["motion"])
        self.assertFalse(robot["device"]["authorization"]["motion"])

    def test_stale_and_disconnect_and_reconnection_keep_motion_locked(self):
        payload = self.payload()
        payload["measured_at"] = (timezone.now() - timedelta(minutes=5)).isoformat()
        self.assertEqual(self.send(payload).status_code, 201)
        now = timezone.now()
        stale = Esp32DiagnosticProvider(self.plot, now=now).status()
        self.assertEqual(stale["telemetry"]["device_reading"]["freshness"], "stale")
        lost = Esp32DiagnosticProvider(
            self.plot, now=now + timedelta(seconds=16)
        ).status()
        self.assertEqual(lost["connection"], "disconnected")
        self.assertIsNone(lost["control"]["action"])
        self.assertEqual(self.send(self.payload(1)).status_code, 201)
        self.assertEqual(
            Esp32DiagnosticProvider(self.plot).status()["connection"],
            "diagnostic_online",
        )
        self.assertFalse(
            Esp32DiagnosticProvider(self.plot).status()["capabilities"][
                "physical_motion"
            ]
        )

    def test_stale_heartbeat_on_backwards_clock_does_not_claim_connection(self):
        self.send()
        previous = Device.objects.get().last_seen - timedelta(seconds=1)
        self.assertEqual(
            Esp32DiagnosticProvider(self.plot, now=previous).status()["connection"],
            "disconnected",
        )

    def test_stop_only_poll_sequences_duplicates_expiry_and_no_poll_heartbeat(self):
        response, values = self.poll(4)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        first = response.json()["data"]
        self.assertEqual(first["action"], "stop")
        self.assertFalse(first["motion_enabled"])
        self.assertEqual(first["seq"], 1)
        self.assertIsNone(Device.objects.get().last_seen)
        same = self.client.get("/api/device/commands/next/", values).json()["data"]
        self.assertEqual(same["command_id"], first["command_id"])
        self.assertTrue(same["duplicate"])
        old, _ = self.poll(3)
        self.assertEqual(old.json()["error"]["code"], "sequence_old")
        Device.objects.filter(pk=self.device.pk).update(
            command_expires_at=timezone.now() - timedelta(seconds=1)
        )
        expired = self.client.get("/api/device/commands/next/", values)
        self.assertEqual(expired.json()["error"]["code"], "command_expired")
        self.assertEqual(
            expired.json()["data"], {"action": "stop", "motion_enabled": False}
        )
        next_response, _ = self.poll(5)
        self.assertEqual(next_response.json()["data"]["seq"], 2)
        self.assertEqual(DeviceMessage.objects.count(), 0)

    def test_poll_rejects_conflict_invalid_and_duplicate_parameters(self):
        self.assertEqual(self.poll(seq="1.0")[0].status_code, 400)
        result, values = self.poll()
        values["seq"] = 1
        self.assertEqual(
            self.client.get("/api/device/commands/next/", values).json()["error"][
                "code"
            ],
            "message_conflict",
        )
        self.assertEqual(
            self.client.get(
                "/api/device/commands/next/?schema_version=1.0&seq=1&seq=2"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                "/api/device/commands/next/", {"schema_version": "1.0"}
            ).status_code,
            400,
        )

    def test_receipt_is_not_physical_stop_confirmation(self):
        result, _ = self.poll()
        command = result.json()["data"]
        body = self.status_payload()
        body["ack"] = {
            "command_id": command["command_id"],
            "seq": command["seq"],
            "result": "received",
        }
        self.assertEqual(
            self.client.post("/api/device/status/", body, format="json").status_code,
            201,
        )
        self.assertIsNone(
            Esp32DiagnosticProvider(self.plot).status()["control"]["action"]
        )
        self.assertFalse(
            Esp32DiagnosticProvider(self.plot).status()["device"]["safety"][
                "physical_stop_verified"
            ]
        )
        body = self.status_payload(1)
        body["ack"] = {"command_id": str(uuid.uuid4()), "seq": 1, "result": "received"}
        self.assertEqual(
            self.client.post("/api/device/status/", body, format="json").json()[
                "error"
            ]["code"],
            "command_unknown",
        )
        body["ack"]["command_id"] = command["command_id"]
        Device.objects.filter(pk=self.device.pk).update(
            command_expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(
            self.client.post("/api/device/status/", body, format="json").json()[
                "error"
            ]["code"],
            "command_expired",
        )

    def test_session_rotation_invalidates_old_packets_preserves_history(self):
        self.send()
        self.poll()
        old = self.session
        call_command(
            "register_device",
            device_id=self.device.device_id,
            plot=self.plot.id,
            reset_session=True,
            stdout=io.StringIO(),
        )
        self.device.refresh_from_db()
        self.assertNotEqual(str(self.device.session_id), old)
        self.assertEqual(self.send().json()["error"]["code"], "session_invalid")
        self.assertEqual(self.poll()[0].json()["error"]["code"], "session_invalid")
        self.session = str(self.device.session_id)
        self.assertEqual(self.send().status_code, 201)
        self.assertEqual(DeviceMessage.objects.count(), 2)
        self.assertEqual(self.poll()[0].json()["data"]["seq"], 2)

    def test_registration_scoping_and_reassignment(self):
        other = Plot.objects.create(name="Other")
        demo = Plot.objects.create(name="Demo", demo=True)
        for identity, plot in [
            (self.device.device_id, other.id),
            ("another", self.plot.id),
            ("demo", demo.id),
        ]:
            with self.assertRaises(CommandError):
                call_command(
                    "register_device",
                    device_id=identity,
                    plot=plot,
                    stdout=io.StringIO(),
                )
        self.assertEqual(Device.objects.count(), 1)

    def test_history_scoped_and_survives_provider_recreation(self):
        self.send()
        self.client.post("/api/device/status/", self.status_payload(), format="json")
        rows = self.client.get(
            "/api/device/telemetry/", {"schema_version": "1.0"}
        ).json()["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "real")
        self.assertEqual(
            Esp32DiagnosticProvider(self.plot).status()["telemetry"]["device_reading"][
                "message_id"
            ],
            rows[0]["message_id"],
        )
        other = Plot.objects.create(name="Other")
        response = self.client.get(
            "/api/robot/status/", HTTP_X_SEMI_PLOT=str(other.id)
        ).json()["data"]
        self.assertIsNone(response["device"])
        self.assertNotIn("device_reading", response["telemetry"])

    def test_health_and_browser_control_stay_compatible_and_blocked(self):
        self.send()
        profile = self.client.get("/api/health/").json()
        self.assertEqual(profile["mode"], "operational")
        self.assertEqual(profile["data"]["device_integration"], "diagnostic")
        self.assertFalse(profile["data"]["physical_control"])
        token = profile["data"]["csrf_token"]
        payload = {
            "mode": "operational",
            "action": "forward",
            "speed": "low",
            "seq": 1,
            "epoch": 0,
            "window_id": "",
            "session_id": str(uuid.uuid4()),
        }
        self.assertEqual(
            self.client.post(
                "/api/control/command/", payload, format="json", HTTP_X_CSRFTOKEN=token
            ).status_code,
            403,
        )
        self.assertEqual(Device.objects.get().command_seq, 0)

    def test_database_busy_is_safe_retryable_error(self):
        from django.db import OperationalError

        with patch(
            "apps.devices.views.DeviceTelemetryService.receive",
            side_effect=OperationalError("locked"),
        ):
            response = self.send()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "storage_busy")
        self.assertFalse(response.json()["data"]["motion_enabled"])


@override_settings(SEMI_MODE="operational", SEMI_DEVICE_INTEGRATION="diagnostic")
class ConcurrentDeviceTests(TransactionTestCase):
    def setUp(self):
        # Older gate migration tests deliberately roll back dependent migrations.
        # Restore leaves in the isolated test DB before exercising this app.
        call_command("migrate", verbosity=0)
        self.plot = Plot.objects.create(name="Concurrent fixture")
        self.device = Device.objects.create(
            device_id="parallel-fixture", plot=self.plot
        )
        self.secret = secrets.token_urlsafe(32)
        self.config = override_settings(
            SEMI_DEVICE_TOKENS={self.device.device_id: self.secret}
        )
        self.config.enable()
        self.addCleanup(self.config.disable)

    def test_two_workers_retry_same_reading_without_duplicate_or_lost_sequence(self):
        import threading

        barrier = threading.Barrier(2)
        payload = {
            "schema_version": "1.0",
            "session_id": str(self.device.session_id),
            "message_id": str(uuid.uuid4()),
            "seq": 0,
            "sensors": {
                "soil_moisture_adc": {"value": 1700, "adc_max": 4095, "status": "valid"}
            },
        }

        def post(wait=False):
            try:
                client = APIClient(enforce_csrf_checks=True)
                client.credentials(
                    HTTP_X_SEMI_DEVICE_ID=self.device.device_id,
                    HTTP_X_SEMI_DEVICE_TOKEN=self.secret,
                )
                if wait:
                    barrier.wait(timeout=10)
                return client.post(
                    "/api/device/telemetry/", payload, format="json"
                ).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: post(True), range(2)))
        self.assertTrue(all(s in [200, 201, 503] for s in statuses), statuses)
        # After writers finish, an exact retry succeeds even if both saw a lock.
        self.assertIn(post(), [200, 201])
        self.assertEqual(DeviceMessage.objects.count(), 1)
        self.assertEqual(Device.objects.get().telemetry_seq, 0)


class StopLeaseClockTests(TestCase):
    def test_expiry_is_deterministic_without_sleep_or_a_new_incoming_order(self):
        from .contracts import PollRequest
        from .services import DeviceFault

        plot = Plot.objects.create(name="Clock fixture")
        device = Device.objects.create(device_id="clock-fixture", plot=plot)
        values = {
            "schema_version": "1.0",
            "session_id": device.session_id,
            "request_id": uuid.uuid4(),
            "seq": 0,
        }
        now = timezone.now()
        command = StopCommandBroker.next(device, values, now=now)
        self.assertEqual(command["valid_for_ms"], 450)
        retry = StopCommandBroker.next(
            device, values, now=now + timedelta(milliseconds=100)
        )
        self.assertEqual(retry["valid_for_ms"], 350)
        with self.assertRaises(DeviceFault) as caught:
            StopCommandBroker.next(
                device, values, now=now + timedelta(milliseconds=450)
            )
        self.assertEqual(caught.exception.get_codes(), "command_expired")
        self.assertFalse(command["motion_enabled"])


class DeviceConfigurationTests(SimpleTestCase):
    def test_configuration_cannot_enable_physical_operation(self):
        import os
        import subprocess
        import sys
        from django.conf import settings

        env = {
            **os.environ,
            "SEMI_MODE": "operational",
            "SEMI_LIDAR_SOURCE": "real",
            "SEMI_DEVICE_TOKENS": "{}",
            "SEMI_DEVICE_INTEGRATION": "operational",
        }
        result = subprocess.run(
            [sys.executable, "-c", "import config.settings"],
            cwd=settings.BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Only disabled or diagnostic", result.stderr)


class DemonstrationIsolationTests(SimpleTestCase):
    def test_demo_cannot_consume_real_lidar(self):
        import os
        import subprocess
        import sys
        from django.conf import settings

        env = {
            **os.environ,
            "SEMI_MODE": "demonstration",
            "SEMI_LIDAR_SOURCE": "real",
            "SEMI_DEVICE_TOKENS": "{}",
            "SEMI_DEVICE_INTEGRATION": "disabled",
        }
        result = subprocess.run(
            [sys.executable, "-c", "import config.settings"],
            cwd=settings.BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Demonstration cannot consume", result.stderr)
