from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from adapters import registry
from apps.agriculture.models import Plot, SamplingPoint
from apps.agriculture.setup_views import scope
from .models import DeviceMessage, ReadingLocation
from .views import envelope


@api_view(["GET"])
def plots(request):
    return Response(
        envelope(
            list(
                Plot.objects.filter(demo=False)
                .order_by("name", "id")
                .values("id", "name")
            )
        )
    )


@api_view(["GET", "POST"])
def adc_history(request):
    from config.views import limit

    plot = scope(request)
    if registry.is_demonstration() or plot is None:
        if request.method == "POST":
            raise PermissionDenied("Elige un cafetal con lecturas reales.")
        return Response(envelope([]))
    rows = DeviceMessage.objects.filter(
        device__plot=plot,
        kind="telemetry",
        payload__sensors__has_key="soil_moisture_adc",
    )
    if request.method == "POST":
        row_id, point_id = request.data.get("reading"), request.data.get("point")
        if type(row_id) is not int or type(point_id) is not int:
            raise ValidationError("Selecciona una lectura y un punto.")
        with transaction.atomic():
            row = rows.filter(pk=row_id, sampling_point__isnull=True).first()
            point = SamplingPoint.objects.filter(pk=point_id, plot=plot).first()
            if not row or not point:
                raise NotFound(
                    "Revisa el cafetal, la lectura y el punto seleccionados."
                )
            location, created = ReadingLocation.objects.get_or_create(
                reading=row, defaults={"point": point}
            )
            if location.point_id != point.id:
                raise ValidationError("La lectura ya tiene un punto asignado.")
        return Response(
            envelope({"reading": row.id, "point": point.id}),
            status=201 if created else 200,
        )
    point = request.query_params.get("point")
    if point:
        if not point.isdecimal() or len(point) > 12:
            raise ValidationError("Punto inválido.")
        rows = rows.filter(
            Q(sampling_point_id=int(point)) | Q(location__point_id=int(point))
        )
    data = []
    for row in rows.select_related("sampling_point", "location__point")[
        : limit(request)
    ]:
        location = getattr(row, "location", None)
        point = location.point if location else row.sampling_point
        data.append(
            {
                "id": row.id,
                "source": row.source,
                "plot": plot.name,
                "point": point.name if point else None,
                "assigned_by": (
                    "operator" if location else ("device" if point else None)
                ),
                "received_at": row.received_at,
                "adc": row.payload["sensors"]["soil_moisture_adc"],
            }
        )
    return Response(envelope(data))
