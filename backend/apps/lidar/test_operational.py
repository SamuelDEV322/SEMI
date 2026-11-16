import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from django.test import SimpleTestCase
from adapters.a1 import frame
from adapters.lidar_sources import LidarSources
from adapters import registry


class RealFrameTests(SimpleTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "scan.json"
        env = patch.dict("os.environ", {"SEMI_LIDAR_SPOOL": str(self.path)})
        env.start()
        self.addCleanup(env.stop)
        self.clock = [100.0]
        self.hub = LidarSources(
            registry.lidar, clock=lambda: self.clock[0], source="real"
        )

    def data(self):
        return frame(
            "valid",
            [{"angle_deg": 90, "distance": 1200, "quality": 20, "valid": True}],
            clock=lambda: 100,
        )

    def publish(self, data):
        self.path.write_text(json.dumps(data), encoding="utf8")
        return self.hub.latest()

    def test_valid_frame_expires_without_a_new_reader_write(self):
        data = self.data()
        self.assertTrue(self.publish(data)["valid"])
        self.clock[0] = 102.1
        self.assertEqual(self.hub.latest()["status"], "stale")
        self.assertFalse(self.hub.latest()["valid"])

    def test_old_file_from_another_boot_is_not_fresh(self):
        data = self.data()
        data["captured_at"] = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat()
        self.assertEqual(self.publish(data)["status"], "stale")

    def test_corrupt_or_incomplete_frames_cannot_become_measurements(self):
        mutations = [
            lambda d: d.update(received_monotonic=-1e308),
            lambda d: d.pop("received_monotonic"),
            lambda d: d.update(captured_at=None),
            lambda d: d.update(source="mock"),
            lambda d: d.update(points="bad"),
            lambda d: d.update(max_range_mm=0),
            lambda d: d["points"][0].update(distance=float("nan")),
            lambda d: d["points"][0].update(angle_deg=360),
            lambda d: d["points"][0].update(quality=64),
            lambda d: d["points"][0].update(valid="true"),
            lambda d: d.update(status="disconnected"),
            lambda d: d.update(
                captured_at=(
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat()
            ),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                data = self.data()
                mutate(data)
                result = self.publish(data)
                self.assertEqual(result["status"], "error")
                self.assertFalse(result["valid"])
                self.assertEqual(result["points"], [])

    def test_disconnection_and_no_data_remain_distinct(self):
        for status in ["disconnected", "no_data", "error"]:
            result = self.publish(frame(status))
            self.assertEqual(result["status"], status)
            self.assertIsNone(result["age_ms"])
            self.assertFalse(result["valid"])
