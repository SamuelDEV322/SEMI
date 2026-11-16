from django.db import connection
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers
from adapters import registry
from adapters.mock import MockTelemetryProvider, MockLidarProvider
from apps.agriculture.models import Sample, SamplingPoint
from apps.agriculture.serializers import SampleSerializer, PointSerializer
from django.utils.dateparse import parse_datetime
from apps.robot.serializers import CommandSerializer
from apps.telemetry.models import SystemEvent
from apps.agriculture.setup_views import scope, robot_for, surface_blocks, next_code


def envelope(data):
    return {
        "schema_version": "1.0",
        "mode": "demonstration",
        "server_time": timezone.now().isoformat(),
        "data": data,
    }


def unavailable(request):
    if robot_for(request).scenario == "error":
        return Response(
            {
                "mode": "demonstration",
                "error": {
                    "code": "simulated_error",
                    "detail": "Error de adquisición simulado.",
                },
            },
            status=503,
        )
    return None


def limit(request):
    try:
        value = int(request.query_params.get("limit", "100"))
        if not 1 <= value <= 200:
            raise ValueError()
        return value
    except (TypeError, ValueError):
        raise serializers.ValidationError({"limit": "Usa un entero entre 1 y 200."})


@api_view(["GET"])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return Response(
        envelope(
            {
                "status": "ok",
                "database": "sqlite",
                "csrf_token": get_token(request),
                "physical_control": False,
            }
        )
    )


@api_view(["GET"])
def robot_status(request):
    data = robot_for(request).status()
    data["telemetry"] = MockTelemetryProvider(robot_for(request)).latest()
    data["events"] = list(
        SystemEvent.objects.values("id", "created_at", "kind", "message", "source")[:8]
    )
    if scope(request) and scope(request).demo:
        from apps.agriculture.setup_views import trial_payload

        data["events"] = []
        data["surface_trial"] = {
            **trial_payload(scope(request)),
            "blocked": surface_blocks(scope(request)),
        }
    return Response(envelope(data))


@api_view(["GET"])
def latest(request):
    failure = unavailable(request)
    if failure is not None:
        return failure
    row = (
        (
            Sample.objects.filter(sampling_point__plot=scope(request)).first()
            if scope(request)
            else Sample.objects.first()
        )
        if robot_for(request).scenario not in {"no_data", "disconnected"}
        else None
    )
    data = SampleSerializer(row).data if row else None
    if data and robot_for(request).scenario == "stale":
        data["freshness"] = "stale"
    return Response(envelope(data))


@api_view(["GET"])
def history(request):
    return Response(
        envelope(
            SampleSerializer(
                filtered_samples(request)[: limit(request)], many=True
            ).data
        )
    )


@csrf_protect
@api_view(["GET", "POST"])
def samples(request):
    if request.method == "GET":
        return Response(
            envelope(
                SampleSerializer(
                    filtered_samples(request)[: limit(request)], many=True
                ).data
            )
        )
    if request.data.get("source", "mock") != "mock":
        return Response(
            {
                "mode": "demonstration",
                "error": {
                    "code": "real_sample_forbidden",
                    "detail": "Gate 1 solo registra muestras de demostración.",
                },
            },
            status=403,
        )
    serializer = SampleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if scope(request) and (
        not serializer.validated_data.get("sampling_point")
        or serializer.validated_data["sampling_point"].plot_id != scope(request).id
    ):
        raise serializers.ValidationError("Selecciona un punto de este terreno.")
    row = serializer.save(source="mock")
    attach_legacy_point(row)
    SystemEvent.objects.create(
        kind="sample", message=f"Muestra demostrativa registrada: {row.point_label}"
    )
    return Response(envelope(SampleSerializer(row).data), status=201)


@api_view(["GET"])
def lidar(request):
    failure = unavailable(request)
    if failure is not None:
        return failure
    if registry.lidar_sources.source == "mock":
        data = MockLidarProvider(robot_for(request)).latest()
        data.update(
            age_ms=30000 if robot_for(request).scenario == "stale" else 0, error=None
        )
        return Response(envelope(data))
    return Response(envelope(registry.lidar_sources.latest()))


@api_view(["POST"])
def lidar_source(request):
    try:
        registry.lidar_sources.select(request.data.get("source"))
    except PermissionError as error:
        return Response(
            {
                "mode": "demonstration",
                "error": {"code": "diagnostic_disabled", "detail": str(error)},
            },
            status=403,
        )
    except ValueError:
        raise serializers.ValidationError({"source": "Usa mock, replay o real."})
    return Response(envelope(registry.lidar_sources.latest()))


@csrf_protect
@api_view(["POST"])
def command(request):
    serializer = CommandSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    robot = robot_for(request)
    if serializer.validated_data["mode"] != "demonstration":
        return Response(
            {
                "mode": "demonstration",
                "error": {
                    "code": "physical_control_forbidden",
                    "detail": "El movimiento físico no está habilitado.",
                },
            },
            status=403,
        )
    plot = scope(request)
    with robot.lock:
        if (
            plot
            and plot.demo
            and serializer.validated_data["action"] != "stop"
            and getattr(robot, "surface_blocked", surface_blocks(plot))
        ):
            return Response(
                {
                    "mode": "demonstration",
                    "error": {
                        "code": "surface_demo_stop",
                        "detail": "Movimiento simulado detenido por el ensayo de superficie.",
                    },
                },
                status=409,
            )
        previous = robot.action
        data, status = robot.command(serializer.validated_data)
    if status != 200:
        return Response({"mode": "demonstration", "error": data}, status=status)
    if previous != robot.action and not (plot and plot.demo):
        SystemEvent.objects.create(
            kind="control", message=f"Control simulado: {robot.action}"
        )
    return Response(envelope(data))


@csrf_protect
@api_view(["POST"])
def scenario(request):
    value = request.data.get("scenario")
    if value not in registry.robot.scenarios:
        raise serializers.ValidationError(
            {"scenario": "Usa connected, disconnected, no_data, error o stale."}
        )
    robot_for(request).set_scenario(value)
    SystemEvent.objects.create(
        kind="scenario", message=f"Escenario de demostración: {value}"
    )
    return Response(envelope(robot_for(request).status()))


@csrf_protect
@api_view(["POST"])
def capture(request):
    if (
        robot_for(request).scenario != "connected"
        or robot_for(request).status()["control"]["action"] != "stop"
    ):
        return Response(
            {
                "mode": "demonstration",
                "error": {
                    "code": "capture_unavailable",
                    "detail": "Restablece el escenario conectado para generar una muestra.",
                },
            },
            status=409,
        )
    point = None
    if scope(request) and request.data.get("sampling_point") is None:
        raise serializers.ValidationError(
            "Selecciona un lugar para guardar la medición."
        )
    if request.data.get("sampling_point") is not None:
        try:
            point = (
                SamplingPoint.objects.filter(plot=scope(request))
                if scope(request)
                else SamplingPoint.objects
            ).get(pk=int(request.data["sampling_point"]))
        except (ValueError, TypeError, SamplingPoint.DoesNotExist):
            raise serializers.ValidationError(
                {"sampling_point": "Selecciona un punto existente."}
            )
    label = point.name if point else request.data.get("point_label", "Punto de prueba")
    if not isinstance(label, str) or not label.strip() or len(label) > 60:
        raise serializers.ValidationError(
            {"point_label": "Usa una etiqueta de 1 a 60 caracteres."}
        )
    row = Sample.objects.create(**registry.npk.capture(label.strip()))
    if point:
        row.sampling_point = point
        row.save(update_fields=["sampling_point"])
    else:
        attach_legacy_point(row)
    SystemEvent.objects.create(
        kind="sample", message=f"Captura simulada: {row.point_label}"
    )
    return Response(envelope(SampleSerializer(row).data), status=201)


def attach_legacy_point(row):
    # Compatibility with Gate 1 labels; never relocate an existing point.
    if row.sampling_point_id is None:
        point, _ = SamplingPoint.objects.get_or_create(
            name=row.point_label,
            defaults={"position_method": row.position_method, "x": row.x, "y": row.y},
        )
        row.sampling_point = point
        row.save(update_fields=["sampling_point"])


def filtered_samples(request):
    rows = Sample.objects.all()
    plot = scope(request)
    if plot:
        rows = rows.filter(sampling_point__plot=plot)
    if request.query_params.get("point"):
        try:
            rows = rows.filter(sampling_point_id=int(request.query_params["point"]))
        except ValueError:
            raise serializers.ValidationError({"point": "Punto inválido."})
    for key, lookup in [("since", "captured_at__gte"), ("until", "captured_at__lte")]:
        if request.query_params.get(key):
            stamp = parse_datetime(request.query_params[key])
            if stamp is None or timezone.is_naive(stamp):
                raise serializers.ValidationError(
                    {key: "Usa fecha ISO 8601 con zona horaria."}
                )
            rows = rows.filter(**{lookup: stamp})
    return rows


@api_view(["GET", "POST", "PATCH"])
def points(request, point_id=None):
    if request.method == "GET":
        if point_id is not None:
            from django.shortcuts import get_object_or_404

            return Response(
                envelope(
                    PointSerializer(
                        get_object_or_404(
                            (
                                SamplingPoint.objects.filter(plot=scope(request))
                                if scope(request)
                                else SamplingPoint.objects.all()
                            ),
                            pk=point_id,
                        )
                    ).data
                )
            )
        return Response(
            envelope(
                PointSerializer(
                    (
                        SamplingPoint.objects.filter(plot=scope(request))
                        if scope(request)
                        else SamplingPoint.objects.all()
                    ),
                    many=True,
                ).data
            )
        )
    instance = None
    if request.method == "PATCH":
        from django.shortcuts import get_object_or_404

        instance = get_object_or_404(
            (
                SamplingPoint.objects.filter(plot=scope(request))
                if scope(request)
                else SamplingPoint.objects.all()
            ),
            pk=point_id,
        )
    serializer = PointSerializer(
        instance, data=request.data, partial=instance is not None
    )
    serializer.is_valid(raise_exception=True)
    row = serializer.save(**({"plot": scope(request)} if scope(request) else {}))
    if row.plot_id and not row.code:
        row.code = next_code(row.plot)
        row.save(update_fields=["code"])
    return Response(envelope(serializer.data), status=200 if instance else 201)
