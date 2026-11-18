"""Installation and descriptive sectors. No geographic or material inference."""

import math
from django.conf import settings
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import (
    ValidationError,
    NotFound,
    PermissionDenied,
    APIException,
)
from adapters.mock import MockRobotProvider
from adapters import registry
from .models import Plot, TerrainZone, SamplingPoint, Sample, SurfaceTrial
from .serializers import SampleSerializer, visible_samples

robots = {}


def scope(request):
    value = request.headers.get("X-SEMI-Plot")
    if not value:
        return Plot.objects.filter(demo=False).first()
    try:
        p = Plot.objects.get(pk=int(value))
        return (
            Plot.objects.filter(demo=False).first()
            if p.demo and not registry.is_demonstration()
            else p
        )
    except (ValueError, Plot.DoesNotExist):
        raise NotFound("No se encontró este terreno.")


def surface_blocks(plot):
    trial = (
        SurfaceTrial.objects.filter(plot=plot).first() if plot and plot.demo else None
    )
    return bool(
        trial
        and (
            trial.state in ["sand", "lost"]
            or trial.state == "unknown"
            and trial.conservative
        )
    )


def robot_for(request):
    if not registry.is_demonstration():
        if settings.SEMI_DEVICE_INTEGRATION == "diagnostic":
            from adapters.esp32_diagnostic import Esp32DiagnosticProvider

            return Esp32DiagnosticProvider(scope(request))
        return registry.unconfigured_robot
    p = scope(request)
    if p and p.demo:
        if p.id not in robots:
            robot = MockRobotProvider()
            robot.surface_blocked = surface_blocks(p)
            robots[p.id] = robot
        return robots[p.id]
    return registry.robot


def own(rows, value, label):
    try:
        if isinstance(value, bool):
            raise ValueError()
        return rows.get(pk=int(value))
    except (ValueError, TypeError, rows.model.DoesNotExist):
        raise ValidationError(f"Selecciona {label} de este cafetal.")


def clean_name(value, label, maximum=80):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValidationError(f"Revisa el nombre de {label}.")
    return value.strip()


def next_code(plot):
    existing = set(plot.points.values_list("code", flat=True))
    n = 1
    while f"P{n}" in existing:
        n += 1
    return f"P{n}"


def payload(p):
    if p is None:
        return None
    return {
        "id": p.id,
        "name": p.name,
        "crop": p.crop,
        "demo": p.demo,
        "step": p.step,
        "completed": p.completed,
        "zones": [
            {
                "id": z.id,
                "name": z.name,
                "archived": z.archived,
                "historical_surface": z.historical_surface,
                "point_count": z.samplingpoint_set.count(),
                "has_history": z.historical_points.exists(),
            }
            for z in p.zones.all()
        ],
        "points": [
            {
                "id": x.id,
                "code": x.code,
                "name": x.name,
                "x": x.x,
                "y": x.y,
                "zone": x.zone_id,
                "latest_sample": (
                    SampleSerializer(visible_samples(x.samples).first()).data
                    if visible_samples(x.samples).exists()
                    else None
                ),
            }
            for x in p.points.all()
        ],
    }


def result(p):
    return Response(
        {"schema_version": "1.0", "mode": settings.SEMI_MODE, "data": payload(p)}
    )


def trial_payload(p):
    trial = SurfaceTrial.objects.filter(plot=p).first()
    return {
        "state": trial.state if trial else "inactive",
        "conservative": trial.conservative if trial else True,
        "source": "simulation",
        "physical_detection": False,
    }


def update_trial(request, p, data):
    if not p or not p.demo or not settings.SEMI_DEV_TOOLS or not settings.DEBUG:
        raise PermissionDenied(
            "El ensayo solo está disponible en un recorrido de demostración."
        )
    value = data.get("state", data.get("surface"))
    conservative = data.get("conservative", True)
    if value not in ["soil", "sand", "unknown", "lost", "inactive"] or not isinstance(
        conservative, bool
    ):
        raise ValidationError("Revisa la condición de ensayo.")
    robot = robot_for(request)
    with robot.lock:
        SurfaceTrial.objects.update_or_create(
            plot=p, defaults={"state": value, "conservative": conservative}
        )
        robot.surface_blocked = surface_blocks(p)
        if robot.surface_blocked:
            robot.set_scenario("connected")


@api_view(["GET", "POST"])
@transaction.atomic
def surface_trial(request):
    p = scope(request)
    if not p or not p.demo or not settings.SEMI_DEV_TOOLS or not settings.DEBUG:
        raise PermissionDenied("Abre primero un recorrido de demostración.")
    if request.method == "POST":
        update_trial(request, p, request.data)
    return Response(
        {"schema_version": "1.0", "mode": settings.SEMI_MODE, "data": trial_payload(p)}
    )


@api_view(["GET", "POST"])
@transaction.atomic
def setup(request):
    p = scope(request)
    if request.method == "GET":
        return result(p)
    action = request.data.get("action")
    if action in ["start", "demo"]:
        if action == "demo" and (not settings.SEMI_DEV_TOOLS or not settings.DEBUG):
            raise PermissionDenied(
                "Recorrido de demostración disponible solo en desarrollo."
            )
        if action == "start":
            p = Plot.objects.filter(demo=False).first()
        if p is None or action == "demo":
            p = Plot.objects.create(demo=action == "demo")
    elif p is None:
        raise ValidationError("Selecciona tu cafetal.")
    if action == "save":
        name = clean_name(request.data.get("name", p.name), "tu cafetal")
        step = request.data.get("step", p.step)
        if type(step) != int or not 1 <= step <= 4:
            raise ValidationError("Revisa la etapa de configuración.")
        p.name = name
        p.step = step
    elif action in ["zone", "sector"]:
        if "category" in request.data:
            raise ValidationError(
                "Los sectores se organizan por nombre; no clasifican superficies."
            )
        name = clean_name(request.data.get("name"), "este sector")
        if request.data.get("zone"):
            z = own(p.zones, request.data["zone"], "un sector")
            z.name = name
            z.save(update_fields=["name"])
        else:
            TerrainZone.objects.create(plot=p, name=name)
    elif action in [
        "sector_delete",
        "sector_archive",
        "sector_restore",
        "sector_detach",
    ]:
        z = own(p.zones, request.data.get("zone"), "un sector")
        if action == "sector_delete":
            if request.data.get("confirmed") is not True:
                raise ValidationError("Confirma antes de eliminar el sector vacío.")
            if (
                z.historical_surface
                or z.samplingpoint_set.exists()
                or z.historical_points.exists()
            ):
                return Response(
                    {
                        "mode": settings.SEMI_MODE,
                        "error": {
                            "code": "sector_in_use",
                            "detail": "Este sector tiene lugares o referencias históricas. Puedes archivarlo sin perder mediciones.",
                        },
                    },
                    status=409,
                )
            z.delete()
        elif action == "sector_detach":
            if request.data.get("confirmed") is not True:
                raise ValidationError("Confirma antes de desvincular los lugares.")
            for point in p.points.filter(zone=z):
                point.zone_history.add(z)
                point.zone = None
                point.save(update_fields=["zone"])
        else:
            if action == "sector_restore" and z.historical_surface:
                raise ValidationError(
                    "Esta es información histórica de ensayo; se conserva archivada."
                )
            z.archived = action == "sector_archive"
            z.save(update_fields=["archived"])
    elif action == "point":
        point = (
            own(p.points, request.data["point"], "un lugar")
            if request.data.get("point")
            else None
        )
        x = request.data.get("x", point.x if point else None)
        y = request.data.get("y", point.y if point else None)
        if not (x is None and y is None) and any(
            type(v) not in [int, float] or not math.isfinite(v) or not 0 <= v <= 100
            for v in [x, y]
        ):
            raise ValidationError(
                "Marca una ubicación en el esquema o guarda sin ubicación."
            )
        zone_id = request.data.get("zone", point.zone_id if point else None)
        zone = own(p.zones, zone_id, "un sector") if zone_id is not None else None
        if zone and zone.archived and (not point or point.zone_id != zone.id):
            raise ValidationError("Elige un sector activo o deja el lugar sin sector.")
        if point is None:
            code = next_code(p)
            name = request.data.get("name", "")
            if not isinstance(name, str) or len(name.strip()) > 40:
                raise ValidationError("Usa un nombre de hasta 40 letras para el lugar.")
            point = SamplingPoint(
                plot=p,
                code=code,
                name=f'{code} {name.strip() or "Lugar para medir"} · T{p.id}',
            )
        elif "name" in request.data:
            if not point.code:
                point.code = next_code(p)
            name = request.data["name"]
            if not isinstance(name, str) or len(name.strip()) > 40:
                raise ValidationError("Revisa el nombre del lugar.")
            point.name = f'{point.code} {name.strip() or "Lugar para medir"} · T{p.id}'
        if point.pk and point.zone_id:
            point.zone_history.add(point.zone)
        point.x = x
        point.y = y
        point.position_method = "none" if x is None else "manual_schematic"
        point.zone = zone
        point.save()
        if zone:
            point.zone_history.add(zone)
    elif action == "capture":
        if registry.current_npk() is None:
            error = APIException(
                "Sensor de suelo no conectado. No se generó ninguna medición."
            )
            error.status_code = 503
            raise error
        pt = own(p.points, request.data.get("point"), "un lugar")
        robot = robot_for(request)
        if robot.status()["control"]["action"] != "stop":
            raise ValidationError("Detén el simulador antes de medir.")
        if robot.scenario != "connected":
            raise ValidationError(
                "No pudimos obtener una medición. Comprueba la conexión e inténtalo de nuevo."
            )
        Sample.objects.create(
            sampling_point=pt, **registry.current_npk().capture(pt.name)
        )
    elif action == "complete":
        p.completed = True
        p.step = 4
    elif action == "surface":
        # Compatibility for Gate 3 clients only. New UI uses /api/demo/surface/.
        update_trial(request, p, request.data)
    elif action not in ["start", "demo"]:
        raise ValidationError("Acción no válida.")
    p.save()
    return result(p)
