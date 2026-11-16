import math
from django.utils import timezone
from rest_framework import serializers
from .models import Sample, SamplingPoint
from django.conf import settings


def visible_samples(rows):
    return (
        rows.filter(source="real")
        if settings.SEMI_MODE == "operational"
        else rows.exclude(source="real")
    )


class SampleSerializer(serializers.ModelSerializer):
    freshness = serializers.SerializerMethodField()
    calibration = serializers.SerializerMethodField()

    class Meta:
        model = Sample
        fields = [
            "id",
            "sampling_point",
            "captured_at",
            "point_label",
            "nitrogen",
            "phosphorus",
            "potassium",
            "soil_moisture",
            "npk_unit",
            "moisture_unit",
            "status",
            "source",
            "position_method",
            "x",
            "y",
            "freshness",
            "calibration",
        ]
        read_only_fields = ["id", "source", "npk_unit", "moisture_unit"]
        extra_kwargs = {"point_label": {"required": False}}

    def get_freshness(self, obj):
        return (
            "stale"
            if (timezone.now() - obj.captured_at).total_seconds() > 300
            else "fresh"
        )

    def get_calibration(self, obj):
        return (
            "not_validated"
            if obj.source == "real"
            else "demonstration_not_agronomically_validated"
        )

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: "Campo no permitido." for key in unknown}
            )
        if self.initial_data.get("source", "mock") != "mock":
            raise serializers.ValidationError(
                "Gate 1 no acepta muestras físicas ni replay."
            )
        for field, expected in [("npk_unit", "mg/kg"), ("moisture_unit", "%")]:
            if self.initial_data.get(field, expected) != expected:
                raise serializers.ValidationError(
                    {
                        field: f"La demostración utiliza {expected}; no se convierte automáticamente."
                    }
                )
        for key in ["nitrogen", "phosphorus", "potassium", "soil_moisture", "x", "y"]:
            value = attrs.get(key)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise serializers.ValidationError(
                    {key: "Debe ser un número finito no negativo."}
                )
        moisture = attrs.get("soil_moisture")
        if moisture is not None and moisture > 100:
            raise serializers.ValidationError(
                {"soil_moisture": "El porcentaje debe estar entre 0 y 100."}
            )
        if not any(
            attrs.get(key) is not None
            for key in ["nitrogen", "phosphorus", "potassium", "soil_moisture"]
        ):
            raise serializers.ValidationError(
                "Incluye al menos una lectura; los valores ausentes se conservan como null."
            )
        if attrs["captured_at"] > timezone.now() + timezone.timedelta(seconds=5):
            raise serializers.ValidationError(
                {"captured_at": "No se permiten muestras futuras."}
            )
        method, x, y = (
            attrs.get("position_method", "none"),
            attrs.get("x"),
            attrs.get("y"),
        )
        if method not in ["none", "manual_schematic"]:
            raise serializers.ValidationError(
                {"position_method": "Gate 1 admite none o manual_schematic."}
            )
        if method == "none" and (x is not None or y is not None):
            raise serializers.ValidationError(
                "Una posición requiere un método explícito."
            )
        if method == "manual_schematic" and (
            x is None or y is None or x > 100 or y > 100
        ):
            raise serializers.ValidationError(
                "El esquema requiere x e y entre 0 y 100; no son coordenadas geográficas."
            )
        point = attrs.get("sampling_point")
        if point:
            attrs["point_label"] = point.name
        elif not attrs.get("point_label"):
            raise serializers.ValidationError(
                {"point_label": "Selecciona un punto o indica una etiqueta."}
            )
        return attrs


class PointSerializer(serializers.ModelSerializer):
    sector_history = serializers.SerializerMethodField()

    def get_sector_history(self, obj):
        return list(obj.zone_history.values("id", "name", "archived"))

    display_name = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        suffix = f" · T{obj.plot_id}"
        return (
            obj.name[: -len(suffix)]
            if obj.code and obj.name.endswith(suffix)
            else obj.name
        )

    latest_sample = serializers.SerializerMethodField()

    class Meta:
        model = SamplingPoint
        fields = [
            "id",
            "name",
            "display_name",
            "sector_history",
            "code",
            "zone",
            "position_method",
            "x",
            "y",
            "created_at",
            "latest_sample",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "latest_sample",
            "display_name",
            "sector_history",
            "code",
            "zone",
        ]

    def get_latest_sample(self, obj):
        sample = visible_samples(obj.samples).first()
        return SampleSerializer(sample).data if sample else None

    def validate(self, attrs):
        method = attrs.get(
            "position_method", getattr(self.instance, "position_method", "none")
        )
        x, y = attrs.get("x", getattr(self.instance, "x", None)), attrs.get(
            "y", getattr(self.instance, "y", None)
        )
        if method not in ["none", "manual_schematic"]:
            raise serializers.ValidationError(
                "Ubicación no admitida. Usa un esquema manual o sin ubicación."
            )
        if method == "none" and (x is not None or y is not None):
            raise serializers.ValidationError(
                "Una posición requiere un método explícito."
            )
        if method == "manual_schematic" and any(
            v is None or not math.isfinite(v) or not 0 <= v <= 100 for v in [x, y]
        ):
            raise serializers.ValidationError(
                "Indica X e Y entre 0 y 100; no son coordenadas geográficas."
            )
        return attrs
