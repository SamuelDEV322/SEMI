from rest_framework import serializers


class CommandSerializer(serializers.Serializer):
    mode = serializers.CharField()
    action = serializers.ChoiceField(
        choices=["forward", "backward", "left", "right", "stop"]
    )
    speed = serializers.ChoiceField(choices=["low", "medium"])
    session_id = serializers.UUIDField(format="hex_verbose")
    seq = serializers.IntegerField(min_value=0, max_value=2147483647)
    epoch = serializers.IntegerField(min_value=0)
    window_id = serializers.CharField(max_length=60, allow_blank=True)

    def validate(self, attrs):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError("Campos de comando no permitidos.")
        attrs["session_id"] = str(attrs["session_id"])
        return attrs
