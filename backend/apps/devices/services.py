"""SQLite-backed ingestion and STOP-only polling; no outbound hardware transport."""

import hashlib
import json
import uuid
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import APIException
from .models import Device, DeviceMessage


class DeviceFault(APIException):
    def __init__(self, code, detail, status=409):
        self.status_code = status
        super().__init__(detail, code=code)


def require_session(device, session):
    if not device.enabled or device.session_id != session:
        raise DeviceFault(
            "session_invalid",
            "La sesión no está vigente. Revisa el registro del dispositivo.",
        )


def digest(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def locked_device(device):
    # First statement acquires SQLite's write lock, including across workers.
    # select_for_update() alone does NOT lock rows on SQLite.
    Device.objects.filter(pk=device.pk).update(command_seq=F("command_seq"))
    return Device.objects.get(pk=device.pk)


def check_ack(device, ack, now):
    if ack and (
        device.command_id != ack["command_id"] or device.command_seq != ack["seq"]
    ):
        raise DeviceFault(
            "command_unknown",
            "La confirmación no corresponde a la última orden de esta sesión.",
        )
    if ack and (not device.command_expires_at or device.command_expires_at <= now):
        raise DeviceFault(
            "command_expired",
            "La orden ya venció; permanece sin autorización de movimiento.",
        )


class DeviceTelemetryService:
    @staticmethod
    @transaction.atomic
    def receive(device, kind, values, original, now=None):
        now = now or timezone.now()
        device = locked_device(device)
        require_session(device, values["session_id"])
        fingerprint = digest(original)
        existing = DeviceMessage.objects.filter(
            device=device, kind=kind, message_id=values["message_id"]
        ).first()
        if existing:
            if existing.payload_hash != fingerprint:
                raise DeviceFault(
                    "message_conflict",
                    "El identificador ya corresponde a otro contenido.",
                )
            return existing, True  # Exact retries do not renew heartbeat.
        seq_field = f"{kind}_seq"
        if values["seq"] <= getattr(device, seq_field):
            raise DeviceFault(
                "sequence_old", "La secuencia ya fue utilizada o está desactualizada."
            )
        point = None
        if values.get("sampling_point_id") is not None:
            from apps.agriculture.models import SamplingPoint

            point = SamplingPoint.objects.filter(
                pk=values["sampling_point_id"], plot_id=device.plot_id, plot__demo=False
            ).first()
            if not point:
                raise DeviceFault(
                    "point_not_owned",
                    "El lugar no pertenece al cafetal del dispositivo.",
                    400,
                )
        check_ack(device, values.get("ack"), now)
        row = DeviceMessage.objects.create(
            device=device,
            kind=kind,
            session_id=device.session_id,
            message_id=values["message_id"],
            seq=values["seq"],
            measured_at=values.get("measured_at"),
            received_at=now,
            sampling_point=point,
            payload=original,
            payload_hash=fingerprint,
        )
        setattr(device, seq_field, values["seq"])
        fields = [seq_field, "last_seen"]
        device.last_seen = now
        if kind == "status" and "firmware" in values:
            device.firmware = values["firmware"]
            fields.append("firmware")
        device.save(update_fields=fields)
        return row, False


class StopCommandBroker:
    TTL_MS = 450  # STOP receipt lease; never authorizes motion.

    @classmethod
    @transaction.atomic
    def next(cls, device, values, now=None):
        now = now or timezone.now()
        device = locked_device(device)
        require_session(device, values["session_id"])
        fingerprint = digest({k: str(v) for k, v in values.items()})
        duplicate = device.poll_request_id == values["request_id"]
        if duplicate:
            if device.poll_hash != fingerprint:
                raise DeviceFault(
                    "message_conflict", "La solicitud ya corresponde a otro contenido."
                )
            if device.command_expires_at <= now:
                raise DeviceFault(
                    "command_expired",
                    "La respuesta ya venció. Consulta con una secuencia nueva.",
                )
        else:
            if values["seq"] <= device.poll_seq:
                raise DeviceFault(
                    "sequence_old", "La consulta está repetida o desactualizada."
                )
            device.poll_seq = values["seq"]
            device.poll_request_id = values["request_id"]
            device.poll_hash = fingerprint
            device.command_seq += 1
            device.command_id = uuid.uuid4()
            device.command_expires_at = now + timezone.timedelta(
                milliseconds=cls.TTL_MS
            )
            device.save(
                update_fields=[
                    "poll_seq",
                    "poll_request_id",
                    "poll_hash",
                    "command_seq",
                    "command_id",
                    "command_expires_at",
                ]
            )
        # Polling alone does not claim sensor/firmware liveness.
        return {
            "device_id": device.device_id,
            "session_id": str(device.session_id),
            "command_id": str(device.command_id),
            "seq": device.command_seq,
            "action": "stop",
            "motion_enabled": False,
            "authorization": "diagnostic_only",
            "reason": "physical_motion_not_authorized",
            "expires_at": device.command_expires_at.isoformat(),
            "valid_for_ms": max(
                0,
                min(
                    cls.TTL_MS,
                    int((device.command_expires_at - now).total_seconds() * 1000),
                ),
            ),
            "duplicate": duplicate,
        }


def message_data(row, duplicate=False):
    return {
        "device_id": row.device.device_id,
        "message_id": str(row.message_id),
        "seq": row.seq,
        "received_at": row.received_at.isoformat(),
        "measured_at": row.measured_at.isoformat() if row.measured_at else None,
        "sampling_point_id": row.sampling_point_id,
        "source": row.source,
        "duplicate": duplicate,
        "payload": row.payload,
    }
