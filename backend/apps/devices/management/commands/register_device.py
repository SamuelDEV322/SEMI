import re
import uuid
from django.core.management import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from apps.agriculture.models import Plot
from apps.devices.models import Device


class Command(BaseCommand):
    help = "Register a diagnostic-only device. No credentials or hardware operations."

    def add_arguments(self, parser):
        parser.add_argument("--device-id", required=True)
        parser.add_argument("--plot", type=int, required=True)
        parser.add_argument(
            "--reset-session",
            action="store_true",
            help="Explicitly invalidate old packets after firmware reboot; preserves history",
        )
        parser.add_argument("--disable", action="store_true")

    def handle(self, *args, **options):
        identity = options["device_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity):
            raise CommandError(
                "Usa un identificador de 1 a 64 letras, números, guion o guion bajo."
            )
        plot = Plot.objects.filter(pk=options["plot"], demo=False).first()
        if not plot:
            raise CommandError(
                "Selecciona un cafetal existente que no sea de demostración."
            )
        try:
            with transaction.atomic():
                device, created = Device.objects.get_or_create(
                    device_id=identity, defaults={"plot": plot}
                )
                if device.plot_id != plot.id:
                    raise CommandError(
                        "No se reasigna un dispositivo a otro cafetal; conserva sus referencias históricas."
                    )
                device.enabled = not options["disable"]
                if options["reset_session"]:
                    device.session_id = uuid.uuid4()
                    device.telemetry_seq = device.status_seq = device.poll_seq = -1
                    device.poll_request_id = device.command_id = (
                        device.command_expires_at
                    ) = None
                    device.poll_hash = ""
                    device.last_seen = None
                    device.firmware = None
                device.save()
        except IntegrityError:
            raise CommandError(
                "Este cafetal ya tiene un dispositivo habilitado."
            ) from None
        self.stdout.write(
            f"device_id={device.device_id} plot={device.plot_id} session_id={device.session_id} enabled={device.enabled} motion_enabled=False"
        )
