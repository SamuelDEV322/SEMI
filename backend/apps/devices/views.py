from django.conf import settings
from django.db import OperationalError
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ParseError
from .authentication import DeviceAuthentication
from .contracts import TelemetryMessage, StatusMessage, PollRequest
from .services import (
    DeviceFault,
    DeviceTelemetryService,
    StopCommandBroker,
    message_data,
)
from .models import DeviceMessage


def envelope(data):
    return {
        "schema_version": "1.0",
        "mode": settings.SEMI_MODE,
        "server_time": timezone.now().isoformat(),
        "data": data,
    }


class DeviceJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        import json

        raw = stream.read(32769)
        if len(raw) > 32768:
            raise DeviceFault("payload_too_large", "El mensaje supera 32 KiB.", 413)

        def pairs(values):
            result = {}
            for key, value in values:
                if key in result:
                    raise ValueError("duplicate key")
                result[key] = value
            return result

        def invalid_constant(value):
            raise ValueError("non-finite value")

        try:
            return json.loads(
                raw, object_pairs_hook=pairs, parse_constant=invalid_constant
            )
        except (ValueError, UnicodeError, RecursionError):
            raise ParseError("JSON inválido.") from None


class DeviceAPIView(APIView):
    authentication_classes = [DeviceAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [DeviceJSONParser]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    @classmethod
    def as_view(cls, **kwargs):
        view = super().as_view(**kwargs)
        view.semi_device_endpoint = True
        return view

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if (
            settings.SEMI_MODE != "operational"
            or settings.SEMI_DEVICE_INTEGRATION != "diagnostic"
        ):
            raise DeviceFault(
                "integration_disabled",
                "La recepción de dispositivos está deshabilitada.",
                403,
            )
        version = (
            request.query_params.get("schema_version")
            if request.method == "GET"
            else (
                request.data.get("schema_version")
                if isinstance(request.data, dict)
                else None
            )
        )
        if version != "1.0":
            raise DeviceFault(
                "schema_version_unsupported", "Se requiere schema_version 1.0.", 400
            )

    def handle_exception(self, exc):
        if isinstance(exc, OperationalError):
            exc = DeviceFault(
                "storage_busy",
                "No pudimos guardar la solicitud. Reintenta con el mismo identificador.",
                503,
            )
        response = super().handle_exception(exc)
        code = exc.get_codes() if isinstance(exc, APIException) else "device_error"
        response.data = {
            **envelope({"action": "stop", "motion_enabled": False}),
            "error": {
                "code": code if isinstance(code, str) else "validation_error",
                "detail": (
                    "JSON inválido."
                    if isinstance(exc, ParseError)
                    else (
                        str(exc.detail)
                        if isinstance(exc, APIException)
                        else "Error de dispositivo."
                    )
                ),
            },
        }
        return response


class NextCommandView(DeviceAPIView):
    def get(self, request):
        # Reject ambiguous/repeated query keys.
        if any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
            raise DeviceFault("validation_error", "Parámetros duplicados.", 400)
        serializer = PollRequest(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)
        return Response(
            envelope(StopCommandBroker.next(request.auth, serializer.validated_data))
        )


class TelemetryView(DeviceAPIView):
    def post(self, request):
        serializer = TelemetryMessage(data=request.data)
        serializer.is_valid(raise_exception=True)
        row, duplicate = DeviceTelemetryService.receive(
            request.auth, "telemetry", serializer.validated_data, request.data
        )
        return Response(
            envelope(message_data(row, duplicate)), status=200 if duplicate else 201
        )

    def get(self, request):
        # Authenticated diagnostic history, not a cross-device browser endpoint.
        unknown = set(request.query_params) - {"schema_version", "limit"}
        try:
            limit = int(request.query_params.get("limit", 20))
            if unknown or not 1 <= limit <= 100:
                raise ValueError()
        except (ValueError, TypeError):
            raise DeviceFault("validation_error", "Usa limit de 1 a 100.", 400)
        rows = DeviceMessage.objects.filter(device=request.auth, kind="telemetry")[
            :limit
        ]
        return Response(envelope([message_data(row) for row in rows]))


class StatusView(DeviceAPIView):
    def post(self, request):
        serializer = StatusMessage(data=request.data)
        serializer.is_valid(raise_exception=True)
        row, duplicate = DeviceTelemetryService.receive(
            request.auth, "status", serializer.validated_data, request.data
        )
        return Response(
            envelope({**message_data(row, duplicate), "motion_enabled": False}),
            status=200 if duplicate else 201,
        )
