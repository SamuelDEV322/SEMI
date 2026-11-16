import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase
from adapters.a1 import StandardParser, SerialLidarProvider, frame
from adapters.lidar_sources import LidarSources
from adapters import registry


def packet(angle=90, distance=1000, quality=20, start=True):
    a = (quality << 2) | (1 if start else 2)
    q = int(angle * 64) << 1 | 1
    d = int(distance * 4)
    return bytes([a, q & 255, q >> 8, d & 255, d >> 8])


def descriptor(size, mode, kind, payload=b""):
    return (
        b"\xa5\x5a"
        + (size | mode << 30).to_bytes(4, "little")
        + bytes([kind])
        + payload
    )


class FakeSerial:
    def __init__(self, **kwargs):
        self.is_open = False
        self.dtr = True
        self.writes = []
        self.closed = False
        self.data = bytearray(
            descriptor(20, 0, 4, bytes([0x18]) + bytes(19))
            + descriptor(3, 0, 6, bytes(3))
            + descriptor(5, 1, 0x81)
        )

    def open(self):
        self.is_open = True

    def reset_input_buffer(self):
        pass

    def read(self, n):
        result = bytes(self.data[:n])
        del self.data[:n]
        return result

    def write(self, data):
        self.writes.append(data)

    def close(self):
        self.is_open = False
        self.closed = True


class LidarTests(SimpleTestCase):
    def test_parser_chunked_and_invalid_nodes(self):
        p = StandardParser()
        data = packet()
        self.assertEqual(p.feed(data[:2]), [])
        node = p.feed(data[2:])[0]
        self.assertEqual(
            (node["angle_deg"], node["distance"], node["quality"]), (90, 1000, 20)
        )
        self.assertTrue(node["valid"])
        self.assertFalse(p.feed(packet(distance=0))[0]["valid"])
        self.assertEqual(p.feed(b"\x00" * 5), [])
        self.assertGreater(p.rejected, 0)

    def test_no_auto_open_and_confirmation(self):
        calls = []
        r = SerialLidarProvider(
            "FAKE", "A1M8 fixture", serial_factory=lambda **k: calls.append(k)
        )
        self.assertEqual(calls, [])
        with self.assertRaises(PermissionError):
            r.start()
        self.assertEqual(calls, [])

    def test_absent_and_busy_port(self):
        for error in [FileNotFoundError("absent"), PermissionError("busy")]:

            def fail(**kwargs):
                raise error

            r = SerialLidarProvider("FAKE", "A1", serial_factory=fail)
            with self.assertRaises(type(error)):
                r.start(confirmed=True)
            self.assertEqual(r.latest()["status"], "error")

    def test_handshake_scan_age_disconnect_and_close(self):
        now = [100.0]
        device = FakeSerial()
        r = SerialLidarProvider(
            "FAKE",
            "A1 fixture",
            serial_factory=lambda **kwargs: device,
            clock=lambda: now[0],
        )
        r.start(confirmed=True)
        self.assertEqual(r.latest()["status"], "no_data")
        device.data.extend(packet(0) + packet(90, start=False) + packet(0))
        data = r.read_once()
        self.assertEqual(data["source"], "real")
        self.assertEqual(data["status"], "valid")
        self.assertEqual(len(data["points"]), 2)
        now[0] += 2.1
        self.assertEqual(r.latest()["status"], "stale")
        self.assertFalse(r.latest()["valid"])
        now[0] += 1.1
        self.assertEqual(r.read_once()["status"], "disconnected")
        self.assertTrue(device.closed)
        r.close()
        self.assertEqual(r.latest()["status"], "disconnected")

    def test_bad_descriptor_closes_device(self):
        device = FakeSerial()
        device.data[0] = 0
        r = SerialLidarProvider("FAKE", "A1", serial_factory=lambda **kwargs: device)
        with self.assertRaises(ValueError):
            r.start(confirmed=True)
        self.assertTrue(device.closed)

    def test_close_releases_handle_even_if_usb_write_fails(self):
        device = FakeSerial()
        r = SerialLidarProvider("FAKE", "A1", serial_factory=lambda **kwargs: device)
        r.start(confirmed=True)

        def fail(data):
            raise OSError("USB removed")

        device.write = fail
        r.close()
        self.assertTrue(device.closed)

    def test_mock_replay_authorization_and_stale_spool(self):
        hub = LidarSources(registry.lidar, clock=lambda: 100)
        self.assertEqual(hub.latest()["source"], "mock")
        hub.select("replay")
        self.assertEqual(hub.latest()["source"], "replay")
        with patch.dict("os.environ", {"SEMI_LIDAR_DIAGNOSTICS": "0"}):
            with self.assertRaises(PermissionError):
                hub.select("real")
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            "os.environ",
            {
                "SEMI_LIDAR_DIAGNOSTICS": "1",
                "SEMI_LIDAR_SPOOL": str(Path(folder) / "scan.json"),
            },
        ):
            hub.select("real")
            self.assertEqual(hub.latest()["status"], "disconnected")
            data = frame(
                "valid",
                [{"angle_deg": 90, "distance": 1000, "quality": 20, "valid": True}],
                clock=lambda: 90,
            )
            Path(folder, "scan.json").write_text(json.dumps(data), encoding="utf8")
            self.assertEqual(hub.latest()["status"], "stale")
            self.assertFalse(hub.latest()["valid"])
            Path(folder, "scan.json").write_text("bad json", encoding="utf8")
            self.assertEqual(hub.latest()["status"], "error")
