import os
import json
import time
from datetime import datetime, timezone
from django.core.management import BaseCommand, CommandError
from adapters.a1 import SerialLidarProvider, frame
from adapters.lidar_sources import spool_path
from adapters.lidar_ipc import reader_lock, local_host


class Command(BaseCommand):
    help = "Optional A1 USB diagnostic reader; explicit confirmation required; never drive motors."

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["real"], required=True)
        parser.add_argument("--port", required=True)
        parser.add_argument(
            "--revision",
            required=True,
            help="Revision checked on device label / compatible kit",
        )
        parser.add_argument("--baud", type=int, default=115200)

    def handle(self, *args, **options):
        if os.getenv("SEMI_LIDAR_DIAGNOSTICS") != "1":
            raise CommandError("Diagnostic authorization is disabled.")
        self.stdout.write(
            "ADVERTENCIA: abrir el puerto e iniciar lectura puede activar la rotación del LiDAR. No se conectarán motores del vehículo."
        )
        if input("Escribe INICIAR A1 para confirmar: ").strip() != "INICIAR A1":
            raise CommandError("Inicio cancelado; no se abrió el puerto.")
        path = spool_path()
        try:
            with reader_lock(path):
                self.run_reader(options, path)
        except RuntimeError as error:
            raise CommandError(str(error)) from error

    def run_reader(self, options, path):
        reader = SerialLidarProvider(
            options["port"], options["revision"], options["baud"]
        )

        verified = False
        phase = "starting"

        def publish(value):
            value = {
                **value,
                "reader": {
                    "host": local_host(),
                    "transport": "local_usb",
                    "port": options["port"],
                    "revision": options["revision"],
                    "identity_verified": verified,
                    "phase": phase,
                    "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                    "heartbeat_monotonic": time.monotonic(),
                },
            }
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(value, allow_nan=False), encoding="utf8")
            temporary.replace(path)

        failure = None
        terminal = None
        try:
            publish(frame("no_data"))
            reader.start(confirmed=True)
            verified = True
            phase = "reading"
            publish(reader.latest())
            while reader.started:
                snapshot = reader.read_once()
                publish(snapshot)
                if not reader.started:
                    terminal = snapshot
                    if snapshot.get("error"):
                        self.stderr.write(snapshot["error"])
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        except Exception as error:
            phase = "failed"
            failure = str(error)
            publish(frame("error", error=str(error)))
            raise CommandError(str(error))
        finally:
            phase = "failed" if failure or terminal else "closed"
            reader.close()
            publish(
                frame("error", error=failure)
                if failure
                else terminal or reader.latest()
            )
