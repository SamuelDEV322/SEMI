from pathlib import Path
from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Prepare isolated E2E SQLite; refuse any other database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--empty",
            action="store_true",
            help="Start a genuine first installation in the isolated E2E database",
        )

    def handle(self, *args, **kwargs):
        if Path(settings.DATABASES["default"]["NAME"]).name != "e2e.sqlite3":
            raise RuntimeError("E2E preparation only accepts e2e.sqlite3")
        call_command("migrate", verbosity=0)
        # This database was created only for E2E; never accept the demo DB here.
        call_command("flush", interactive=False, verbosity=0)
        if kwargs["empty"]:
            return
        call_command("seed_demo", verbosity=0)

        from apps.agriculture.models import Plot, SamplingPoint

        p = Plot.objects.create(name="Terreno de pruebas", completed=True, step=4)
        SamplingPoint.objects.filter(plot__isnull=True).update(plot=p)
