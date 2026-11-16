from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.agriculture.models import Sample, SamplingPoint
from apps.telemetry.models import SystemEvent


class Command(BaseCommand):
    help = (
        "Carga/actualiza 12 muestras mock identificadas. No borra muestras del usuario."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        for i in range(12):
            Sample.objects.update_or_create(
                demo_key=f"gate1-{i}",
                defaults={
                    "captured_at": now - timedelta(minutes=(11 - i) * 20),
                    "point_label": ["Zona A", "Zona B", "Zona C"][i % 3],
                    "nitrogen": 28 + i % 5 * 2,
                    "phosphorus": 14 + i % 4 * 2,
                    "potassium": 76 + i,
                    "soil_moisture": 37 + i % 6,
                    "source": "mock",
                    "status": "valid",
                    "position_method": "manual_schematic",
                    "x": [22, 52, 78][i % 3],
                    "y": [65, 30, 62][i % 3],
                },
            )
        for sample in Sample.objects.filter(demo_key__startswith="gate1-"):
            point, _ = SamplingPoint.objects.get_or_create(
                name=sample.point_label,
                defaults={
                    "position_method": sample.position_method,
                    "x": sample.x,
                    "y": sample.y,
                },
            )
            sample.sampling_point = point
            sample.save(update_fields=["sampling_point"])
        SystemEvent.objects.get_or_create(
            kind="seed",
            message="Datos de demostraciÃ³n cargados. NingÃºn sensor fÃ­sico conectado.",
        )
        self.stdout.write(
            self.style.SUCCESS(
                "12 muestras mock disponibles; carga repetible sin duplicarlas."
            )
        )
