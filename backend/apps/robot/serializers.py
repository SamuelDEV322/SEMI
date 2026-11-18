from rest_framework import serializers


class CommandSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(
        choices=["traction", "rack", "all"], default="traction"
    )
    mode = serializers.CharField()
    action = serializers.ChoiceField(
        choices=["forward", "backward", "left", "right", "up", "down", "stop"]
    )
    speed = serializers.ChoiceField(choices=["low", "medium"], required=False)
    session_id = serializers.UUIDField(format="hex_verbose")
    seq = serializers.IntegerField(min_value=0, max_value=2147483647)
    epoch = serializers.IntegerField(min_value=0)
    window_id = serializers.CharField(max_length=60, allow_blank=True)

    device_id = serializers.CharField(max_length=64, required=False)
    request_id = serializers.UUIDField(required=False)
    max_duration_ms = serializers.IntegerField(
        min_value=0, max_value=450, required=False
    )

    def validate(self, attrs):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError("Campos de comando no permitidos.")
        domain = attrs["domain"]
        if domain == "rack":
            if attrs["action"] not in ["up", "down", "stop"]:
                raise serializers.ValidationError(
                    "La cremallera admite subir, bajar o detener."
                )
            if any(
                field not in attrs
                for field in ["device_id", "request_id", "max_duration_ms"]
            ):
                raise serializers.ValidationError(
                    "Falta identificación, solicitud o duración del módulo."
                )
            if attrs["action"] != "stop" and attrs["max_duration_ms"] == 0:
                raise serializers.ValidationError(
                    "La intención simulada necesita duración limitada."
                )
        else:
            if (
                attrs["action"] not in ["forward", "backward", "left", "right", "stop"]
                or domain == "all"
                and attrs["action"] != "stop"
            ):
                raise serializers.ValidationError(
                    "La parada general no acepta movimiento."
                )
            if "speed" not in attrs:
                raise serializers.ValidationError("Selecciona velocidad baja o media.")
            if any(
                field in attrs
                for field in ["device_id", "request_id", "max_duration_ms"]
            ):
                raise serializers.ValidationError(
                    "Campos de cremallera fuera de su dominio."
                )
        attrs["session_id"] = str(attrs["session_id"])
        return attrs
