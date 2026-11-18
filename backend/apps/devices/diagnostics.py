"""Non-secret, read-only explanation of the selected plot's device link."""

from django.conf import settings
from django.utils import timezone
from .models import Device, DeviceMessage


def runtime_diagnostics(plot, now=None):
    now = now or timezone.now()
    device = Device.objects.filter(plot=plot).first() if plot else None
    result = {
        "integration": settings.SEMI_DEVICE_INTEGRATION,
        "registered": device is not None,
        "credential_configured": False,
        "authentication": "not_observed",
        "reason": "device_unregistered",
        "status_age_ms": None,
        "telemetry_age_ms": None,
    }
    if device:
        result["credential_configured"] = bool(
            settings.SEMI_DEVICE_TOKENS.get(device.device_id)
        )
        result["authentication"] = (
            "configured_unverified"
            if result["credential_configured"]
            else "credential_missing"
        )
        current = DeviceMessage.objects.filter(
            device=device, session_id=device.session_id
        )
        ages = {}
        for kind in ["status", "telemetry"]:
            row = current.filter(kind=kind).first()
            age = (now - row.received_at).total_seconds() * 1000 if row else None
            ages[kind] = age if age is not None and age >= 0 else None
            result[f"{kind}_age_ms"] = (
                int(ages[kind]) if ages[kind] is not None else None
            )
        if current.exists():
            result["authentication"] = "accepted_messages_present"
        if not device.enabled:
            result["reason"] = "device_disabled"
        elif not result["credential_configured"]:
            result["reason"] = "credential_missing"
        elif device.last_seen is None:
            result["reason"] = (
                "session_waiting" if device.messages.exists() else "registered_waiting"
            )
        elif now < device.last_seen:
            result["reason"] = "clock_invalid"
        elif (now - device.last_seen).total_seconds() > 15:
            result["reason"] = "disconnected"
        elif ages["status"] is not None and ages["status"] <= 15000:
            result["reason"] = "heartbeat_recent"
        else:
            result["reason"] = "telemetry_recent"
    if settings.SEMI_DEVICE_INTEGRATION != "diagnostic":
        result["reason"] = "integration_disabled"
    return result
