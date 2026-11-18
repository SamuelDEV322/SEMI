"""Read-only projection of authenticated device messages into the existing UI contract."""

from django.utils import timezone
from apps.devices.models import Device, DeviceMessage
from .unconfigured import UnconfiguredRobotProvider

HEARTBEAT_MS = 15000
TELEMETRY_MS = 60000


def age_ms(stamp, now):
    if stamp is None or stamp > now:
        return None
    return int((now - stamp).total_seconds() * 1000)


class Esp32DiagnosticProvider(UnconfiguredRobotProvider):
    def command(self, data):
        return {
            "code": "physical_motion_not_authorized",
            "detail": "Movimiento no disponible durante las pruebas de diagnóstico.",
            "hardware_acted": False,
        }, 403

    def __init__(self, plot, now=None):
        super().__init__()
        self.plot = plot
        self.now = now or timezone.now()

    def status(self):
        data = super().status()
        device = (
            Device.objects.filter(plot=self.plot, enabled=True).first()
            if self.plot
            else None
        )
        data["telemetry"] = self.telemetry()
        if not device:
            data["device"] = None
            return data
        elapsed = age_ms(device.last_seen, self.now)
        connected = elapsed is not None and elapsed <= HEARTBEAT_MS
        status = DeviceMessage.objects.filter(
            device=device, session_id=device.session_id, kind="status"
        ).first()
        message = DeviceMessage.objects.filter(
            device=device, session_id=device.session_id, kind="telemetry"
        ).first()
        if connected:
            data.update(
                connection="diagnostic_online",
                hardware_connected=True,
                state="diagnostic",
                scenario="connected",
            )
        data["device"] = {
            "device_id": device.device_id,
            "firmware": device.firmware,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "age_ms": elapsed,
            "integration": "diagnostic",
            "authorization": {"telemetry": True, "motion": False},
            "declared_capabilities": (
                status.payload.get("capabilities") if status else None
            ),
            "firmware_state": status.payload.get("firmware_state") if status else None,
            "uptime_ms": status.payload.get("uptime_ms") if status else None,
            "errors": status.payload.get("errors") if status else None,
            "safety": {
                "motion_authorized": False,
                "reported_motion": (
                    status.payload.get("reported_motion") if status else None
                ),
                "physical_stop_verified": False,
            },
        }
        if message:
            received_age = age_ms(message.received_at, self.now)
            measured_age = age_ms(message.measured_at, self.now)
            elapsed = (
                max(received_age or 0, measured_age or 0)
                if received_age is not None
                else None
            )
            fresh = elapsed is not None and elapsed <= TELEMETRY_MS
            data["telemetry"]["device_reading"] = {
                "message_id": str(message.message_id),
                "sampling_point_id": message.sampling_point_id,
                "measured_at": (
                    message.measured_at.isoformat() if message.measured_at else None
                ),
                "received_at": message.received_at.isoformat(),
                "age_ms": elapsed,
                "source": "real",
                "freshness": "fresh" if fresh else "stale",
                "sensors": message.payload["sensors"],
            }
        return data
