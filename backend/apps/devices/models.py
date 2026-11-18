import uuid
from django.db import models


class Device(models.Model):
    device_id = models.SlugField(max_length=64, unique=True)
    plot = models.ForeignKey("agriculture.Plot", on_delete=models.PROTECT)
    enabled = models.BooleanField(default=True)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    firmware = models.CharField(max_length=80, null=True)
    last_seen = models.DateTimeField(null=True)
    telemetry_seq = models.BigIntegerField(default=-1)
    status_seq = models.BigIntegerField(default=-1)
    poll_seq = models.BigIntegerField(default=-1)
    command_seq = models.BigIntegerField(default=0)
    poll_request_id = models.UUIDField(null=True)
    command_id = models.UUIDField(null=True)
    command_expires_at = models.DateTimeField(null=True)
    poll_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plot"],
                condition=models.Q(enabled=True),
                name="one_enabled_device_per_plot",
            )
        ]


class DeviceMessage(models.Model):
    """Immutable accepted messages. Raw ADC is not a calibrated agricultural sample."""

    device = models.ForeignKey(
        Device, on_delete=models.PROTECT, related_name="messages"
    )
    session_id = models.UUIDField()
    kind = models.CharField(
        max_length=12, choices=[("telemetry", "telemetry"), ("status", "status")]
    )
    message_id = models.UUIDField()
    seq = models.BigIntegerField()
    measured_at = models.DateTimeField(null=True)
    received_at = models.DateTimeField()
    sampling_point = models.ForeignKey(
        "agriculture.SamplingPoint", null=True, on_delete=models.PROTECT
    )
    payload = models.JSONField()
    payload_hash = models.CharField(max_length=64)
    source = models.CharField(max_length=8, default="real", editable=False)

    class Meta:
        ordering = ["-received_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["device", "kind", "message_id"], name="device_message_id_unique"
            ),
            models.UniqueConstraint(
                fields=["device", "session_id", "kind", "seq"],
                name="device_message_sequence_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(source="real"), name="device_message_real_provenance"
            ),
        ]
