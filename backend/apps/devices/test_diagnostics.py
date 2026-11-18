import secrets
import uuid
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.agriculture.models import Plot, Sample
from .models import Device, DeviceMessage
from .diagnostics import runtime_diagnostics
from adapters.esp32_diagnostic import Esp32DiagnosticProvider


@override_settings(SEMI_MODE="operational", SEMI_DEVICE_INTEGRATION="diagnostic")
class LinkDiagnosticsTests(TestCase):
    def setUp(self):
        self.plot = Plot.objects.create(name="Test isolated")
        self.device = Device.objects.create(
            plot=self.plot, device_id="diagnostic-fixture"
        )
        self.secret = secrets.token_urlsafe(32)
        config = override_settings(
            SEMI_DEVICE_TOKENS={self.device.device_id: self.secret}
        )
        config.enable()
        self.addCleanup(config.disable)
        self.now = timezone.now()

    def row(self, kind, seconds=0, session=None):
        row = DeviceMessage.objects.create(
            device=self.device,
            session_id=session or self.device.session_id,
            kind=kind,
            message_id=uuid.uuid4(),
            seq=0,
            received_at=self.now - timezone.timedelta(seconds=seconds),
            payload={
                "sensors": {
                    "soil_moisture_adc": {
                        "value": 1700,
                        "adc_max": 4095,
                        "status": "valid",
                    }
                }
            },
            payload_hash="fixture",
        )
        Device.objects.filter(pk=self.device.pk).update(last_seen=row.received_at)
        return row

    @override_settings(SEMI_DEVICE_INTEGRATION="disabled")
    def test_disabled_is_not_misreported_as_usb_or_sensor_failure(self):
        result = APIClient().get("/api/robot/status/").json()["data"]
        self.assertEqual(result["diagnostics"]["reason"], "integration_disabled")
        self.assertFalse(result["capabilities"]["physical_motion"])

    def test_registration_and_unregistered_are_distinct(self):
        self.assertEqual(runtime_diagnostics(self.plot)["reason"], "registered_waiting")
        self.assertEqual(
            runtime_diagnostics(Plot.objects.create(name="Other"))["reason"],
            "device_unregistered",
        )

    @override_settings(SEMI_DEVICE_TOKENS={})
    def test_missing_credentials_not_inferred_authentication_failure(self):
        result = runtime_diagnostics(self.plot)
        self.assertEqual(result["reason"], "credential_missing")
        self.assertEqual(result["authentication"], "credential_missing")

    def test_heartbeat_without_telemetry_does_not_invent_adc(self):
        self.row("status", 5)
        diag = runtime_diagnostics(self.plot, now=self.now)
        self.assertEqual(diag["reason"], "heartbeat_recent")
        self.assertEqual(diag["status_age_ms"], 5000)
        self.assertIsNone(diag["telemetry_age_ms"])
        data = Esp32DiagnosticProvider(self.plot, now=self.now).status()
        self.assertEqual(data["connection"], "diagnostic_online")
        self.assertNotIn("device_reading", data["telemetry"])

    def test_telemetry_and_disconnection_do_not_rewrite_original_adc(self):
        row = self.row("telemetry", 5)
        self.assertEqual(
            runtime_diagnostics(self.plot, now=self.now)["reason"], "telemetry_recent"
        )
        old = self.now + timezone.timedelta(seconds=70)
        self.assertEqual(
            runtime_diagnostics(self.plot, now=old)["reason"], "disconnected"
        )
        reading = Esp32DiagnosticProvider(self.plot, now=old).status()["telemetry"][
            "device_reading"
        ]
        self.assertEqual(reading["freshness"], "stale")
        self.assertEqual(reading["sensors"], row.payload["sensors"])
        self.assertEqual(Sample.objects.count(), 0)

    def test_old_session_is_not_current_communication(self):
        self.row("telemetry", session=uuid.uuid4())
        Device.objects.filter(pk=self.device.pk).update(last_seen=None)
        self.assertEqual(runtime_diagnostics(self.plot)["reason"], "session_waiting")
        self.assertNotIn(
            "device_reading", Esp32DiagnosticProvider(self.plot).status()["telemetry"]
        )

    def test_no_credentials_leaked_in_diagnostics(self):
        result = APIClient().get("/api/robot/status/")
        self.assertNotIn(self.secret, result.content.decode())
        self.assertTrue(result.json()["data"]["diagnostics"]["credential_configured"])

    def test_rejected_authentication_not_claimed_to_be_recent_communication(self):
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(
            HTTP_X_SEMI_DEVICE_ID=self.device.device_id,
            HTTP_X_SEMI_DEVICE_TOKEN=secrets.token_urlsafe(32),
        )
        self.assertEqual(
            client.post("/api/device/status/", {}, format="json").status_code, 401
        )
        self.assertEqual(
            runtime_diagnostics(self.plot)["authentication"], "configured_unverified"
        )
        self.assertEqual(DeviceMessage.objects.count(), 0)
