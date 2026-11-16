import json
import os
import threading
import time
import math
from pathlib import Path
from django.conf import settings
from .a1 import frame


def spool_path():
    return Path(
        os.getenv("SEMI_LIDAR_SPOOL")
        or str(settings.BASE_DIR / "runtime/lidar-latest.json")
    )


class LidarSources:
    """Django never owns a serial handle. Atomic latest-only file IPC."""

    def __init__(self, mock, clock=time.monotonic):
        self.mock, self.clock = mock, clock
        self.source = "mock"
        self.lock = threading.RLock()
        self.played_at = None

    def select(self, source):
        if source not in {"mock", "replay", "real"}:
            raise ValueError("Unknown source")
        if source == "real" and os.getenv("SEMI_LIDAR_DIAGNOSTICS") != "1":
            raise PermissionError(
                "El diagnóstico USB no está habilitado en este equipo."
            )
        with self.lock:
            self.source = source
            self.played_at = self.clock()

    def latest(self):
        with self.lock:
            if self.source == "mock":
                return {
                    **self.mock.latest(),
                    "age_ms": 30000 if self.mock.robot.scenario == "stale" else 0,
                    "error": None,
                }
            if self.source == "replay":
                # Synthetic protocol-compatible fixture; never a physical recording.
                fixture = json.loads(
                    (Path(__file__).parent / "fixtures/a1-replay.json").read_text(
                        encoding="utf8"
                    )
                )
                data = frame("valid", fixture["points"], clock=self.clock)
                return {
                    **data,
                    "source": "replay",
                    "sensor_id": "synthetic-replay-a1",
                    "age_ms": 0,
                    "fixture": True,
                    "recorded_at": None,
                }
            try:
                path = spool_path()
                if path.stat().st_size > 1024 * 1024:
                    raise ValueError("Oversized scan file")
                data = json.loads(path.read_text(encoding="utf8"))
                if (
                    data.get("source") != "real"
                    or data.get("unit") != "mm"
                    or len(data["points"]) > 4096
                ):
                    raise ValueError("Invalid scan contract")
                for point in data["points"]:
                    angle, distance = point.get("angle_deg"), point.get("distance")
                    if (
                        not isinstance(angle, (int, float))
                        or not math.isfinite(angle)
                        or not 0 <= angle < 360
                    ):
                        raise ValueError("Invalid scan angle")
                    if distance is not None and (
                        not isinstance(distance, (int, float))
                        or not math.isfinite(distance)
                        or distance < 0
                    ):
                        raise ValueError("Invalid scan distance")
                stamp = data.get("received_monotonic")
                age = (self.clock() - stamp) * 1000 if stamp is not None else None
                if age is not None and age < 0:
                    raise ValueError("Invalid monotonic clock")
                data["age_ms"] = round(age) if age is not None else None
                if age is not None and age > 2000:
                    data.update(status="stale", freshness="stale", valid=False)
                return data
            except FileNotFoundError:
                return frame(
                    "disconnected", error="Reader not running", clock=self.clock
                )
            except (OSError, ValueError, TypeError, KeyError) as error:
                return frame("error", error=str(error), clock=self.clock)
