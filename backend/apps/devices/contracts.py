"""Strict wire contract v1.0. No motor or agricultural calibration operations."""

from django.utils import timezone
from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError(
                {"non_field_errors": ["Campos desconocidos o estructura inválida."]}
            )
        return super().to_internal_value(data)


class WireText(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Se requiere texto JSON.")
        return super().to_internal_value(data)


class WireInt(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            raise serializers.ValidationError("Se requiere un entero JSON.")
        return super().to_internal_value(data)


class WireFloat(serializers.FloatField):
    def to_internal_value(self, data):
        import math

        try:
            finite = type(data) in (int, float) and math.isfinite(data)
        except OverflowError:
            finite = False
        if not finite:
            raise serializers.ValidationError("Se requiere un número finito.")
        return super().to_internal_value(data)


class WireBool(serializers.BooleanField):
    def to_internal_value(self, data):
        if type(data) is not bool:
            raise serializers.ValidationError("Se requiere un booleano JSON.")
        return data


class AwareDate(serializers.DateTimeField):
    def to_internal_value(self, data):
        from django.utils.dateparse import parse_datetime

        try:
            parsed = parse_datetime(data) if isinstance(data, str) else None
        except ValueError:
            parsed = None
        if parsed is None or timezone.is_naive(parsed):
            raise serializers.ValidationError(
                "Usa una fecha ISO 8601 con zona horaria."
            )
        if parsed > timezone.now() + timezone.timedelta(seconds=30):
            raise serializers.ValidationError("La fecha de medición está en el futuro.")
        return parsed


class BaseMessage(StrictSerializer):
    schema_version = WireText()
    session_id = serializers.UUIDField()
    message_id = serializers.UUIDField()
    seq = WireInt(min_value=0, max_value=2147483647)
    measured_at = AwareDate(required=False, allow_null=True)


class AdcReading(StrictSerializer):
    value = WireInt(min_value=0, max_value=65535, allow_null=True)
    adc_max = WireInt(min_value=1, max_value=65535, required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=["valid", "invalid", "error", "unavailable"]
    )
    sensor_id = WireText(max_length=80, required=False)

    def validate(self, attrs):
        if attrs["status"] == "valid" and attrs["value"] is None:
            raise serializers.ValidationError("Una lectura válida requiere valor.")
        if attrs["value"] is not None and (
            attrs.get("adc_max") is None or attrs["value"] > attrs["adc_max"]
        ):
            raise serializers.ValidationError("ADC fuera del rango declarado.")
        return attrs


class BatteryReading(StrictSerializer):
    # Transport sanity bound only: not an electrical compatibility claim.
    voltage_v = WireFloat(min_value=0, max_value=100, allow_null=True)
    status = serializers.ChoiceField(
        choices=["valid", "invalid", "error", "unavailable"]
    )
    sensor_id = WireText(max_length=80, required=False)

    def validate(self, attrs):
        if attrs["status"] == "valid" and attrs["voltage_v"] is None:
            raise serializers.ValidationError("Una lectura válida requiere tensión.")
        return attrs


class Sensors(StrictSerializer):
    soil_moisture_adc = AdcReading(required=False)
    battery = BatteryReading(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Incluye al menos una lectura o un estado de sensor."
            )
        return attrs


class TelemetryMessage(BaseMessage):
    sampling_point_id = WireInt(min_value=1, required=False, allow_null=True)
    sensors = Sensors()


class DeclaredCapabilities(StrictSerializer):
    telemetry = WireBool(required=False, allow_null=True)
    motion = WireBool(required=False, allow_null=True)


class Receipt(StrictSerializer):
    command_id = serializers.UUIDField()
    seq = WireInt(min_value=1, max_value=9223372036854775807)
    result = serializers.ChoiceField(choices=["received"])


class StatusMessage(BaseMessage):
    firmware = WireText(max_length=80, required=False, allow_null=True)
    uptime_ms = WireInt(
        min_value=0, max_value=9007199254740991, required=False, allow_null=True
    )
    firmware_state = serializers.ChoiceField(
        choices=["booting", "ready", "error"], required=False, allow_null=True
    )
    reported_motion = serializers.ChoiceField(
        choices=["unknown", "stopped", "moving"], required=False
    )
    capabilities = DeclaredCapabilities(required=False)
    errors = serializers.ListField(
        child=WireText(max_length=160), max_length=10, required=False
    )
    ack = Receipt(required=False)


class PollRequest(StrictSerializer):
    schema_version = WireText()
    session_id = serializers.UUIDField()
    request_id = serializers.UUIDField()
    seq = serializers.IntegerField(min_value=0, max_value=2147483647)

    def validate_seq(self, value):
        import re

        if not re.fullmatch(r"[0-9]+", str(self.initial_data["seq"])):
            raise serializers.ValidationError("Usa una secuencia entera sin decimales.")
        return value
