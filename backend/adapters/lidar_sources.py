import json
import os
import threading
import time
import math
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from .a1 import frame


def spool_path():
    return Path(
        os.getenv("SEMI_LIDAR_SPOOL")
        or str(settings.BASE_DIR / "runtime/lidar-latest.json")
    )


class LidarSources:
    """Django never owns a serial handle. Atomic latest-only file IPC."""

    def __init__(self, mock, clock=time.monotonic, source="mock"):
        self.mock, self.clock = mock, clock
        self.source = source
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
        data = self._latest()
        if self.source == "real":
            from .lidar_diagnostics import annotate

            return annotate(data, clock=self.clock)
        return data

    def _latest(self):
        with self.lock:
            if self.source == "mock":
                return {
                    **self.mock.latest(),
                    "age_ms": 30000 if self.mock.scenario == "stale" else 0,
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

                def reject_constant(value):
                    raise ValueError("Non-finite scan value")

                data = json.loads(
                    path.read_text(encoding="utf8"), parse_constant=reject_constant
                )
                statuses = {"valid", "stale", "disconnected", "no_data", "error"}
                if (
                    not isinstance(data, dict)
                    or data.get("source") != "real"
                    or data.get("unit") != "mm"
                    or data.get("status") not in statuses
                ):
                    raise ValueError("Invalid scan contract")
                reader = data.get("reader") or {}
                if isinstance(reader, dict) and reader.get("host"):
                    from .lidar_ipc import local_host

                    if reader["host"] != local_host():
                        raise ValueError(
                            "Remote scan spool is unsupported; use an authenticated transport"
                        )
                points = data.get("points")
                if (
                    not isinstance(points, list)
                    or len(points) > 4096
                    or type(data.get("valid")) is not bool
                ):
                    raise ValueError("Invalid scan points")
                maximum = data.get("max_range_mm")
                if (
                    type(maximum) not in (int, float)
                    or not math.isfinite(maximum)
                    or maximum <= 0
                ):
                    raise ValueError("Invalid display range")
                for point in points:
                    if not isinstance(point, dict):
                        raise ValueError("Invalid scan node")
                    angle, distance, quality = (
                        point.get("angle_deg"),
                        point.get("distance"),
                        point.get("quality"),
                    )
                    if (
                        type(angle) not in (int, float)
                        or not math.isfinite(angle)
                        or not 0 <= angle < 360
                    ):
                        raise ValueError("Invalid scan angle")
                    if distance is not None and (
                        type(distance) not in (int, float)
                        or not math.isfinite(distance)
                        or distance < 0
                    ):
                        raise ValueError("Invalid scan distance")
                    if quality is not None and (
                        type(quality) is not int or not 0 <= quality <= 63
                    ):
                        raise ValueError("Invalid scan quality")
                    if (
                        type(point.get("valid")) is not bool
                        or point["valid"]
                        and (not distance or quality == 0)
                    ):
                        raise ValueError("Invalid scan validity")
                stamp = data.get("received_monotonic")
                age = None
                if data["status"] in {"valid", "stale"}:
                    if type(stamp) not in (int, float) or not math.isfinite(stamp):
                        raise ValueError("Missing acquisition clock")
                    age = (self.clock() - stamp) * 1000
                    if not math.isfinite(age) or age < 0:
                        raise ValueError("Invalid monotonic clock")
                    captured = datetime.fromisoformat(data.get("captured_at") or "")
                    if captured.tzinfo is None:
                        raise ValueError("Missing timestamp timezone")
                    wall_age = (
                        datetime.now(timezone.utc) - captured
                    ).total_seconds() * 1000
                    if wall_age < -5000:
                        raise ValueError("Future scan timestamp")
                    # Wall age also rejects files left from another system boot.
                    age = max(age, wall_age, 0)
                    if data["valid"] and not any(p["valid"] for p in points):
                        raise ValueError("Scan marked valid without valid points")
                elif data["valid"] or points:
                    raise ValueError("Unavailable scan cannot contain active points")
                data["age_ms"] = round(age) if age is not None else None
                if data["status"] == "stale" or age is not None and age > 2000:
                    data.update(status="stale", freshness="stale", valid=False)
                return data
            except FileNotFoundError:
                return frame(
                    "disconnected", error="Reader not running", clock=self.clock
                )
            except (OSError, ValueError, TypeError, KeyError) as error:
                return frame("error", error=str(error), clock=self.clock)
