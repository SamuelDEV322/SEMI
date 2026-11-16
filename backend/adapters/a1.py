"""Classic A1 standard scan protocol only. No navigation or drive outputs.

References: SLAMTEC SDK sl_lidar_cmd.h measurement_node_t and interface protocol.
No port is opened by importing or constructing this adapter.
"""

import time
from datetime import datetime, timezone


class StandardParser:
    def __init__(self):
        self.buffer = bytearray()
        self.rejected = 0

    def feed(self, data):
        self.buffer.extend(data)
        result = []
        while len(self.buffer) >= 5:
            a, b, c, d, e = self.buffer[:5]
            angle = ((b | c << 8) >> 1) / 64
            if (a & 1) == ((a >> 1) & 1) or not b & 1 or not 0 <= angle < 360:
                del self.buffer[0]
                self.rejected += 1
                continue
            del self.buffer[:5]
            distance = (d | e << 8) / 4
            quality = a >> 2
            result.append(
                {
                    "angle_deg": angle,
                    "distance": distance,
                    "quality": quality,
                    "valid": distance > 0 and quality > 0,
                    "start": bool(a & 1),
                }
            )
        return result


def frame(status="disconnected", points=None, error=None, clock=time.monotonic):
    return {
        "sensor_id": "usb-rplidar-a1",
        "source": "real",
        "status": status,
        "captured_at": datetime.now(timezone.utc).isoformat() if points else None,
        "received_monotonic": clock() if points else None,
        "unit": "mm",
        "valid": bool(points) and any(p["valid"] for p in points),
        "freshness": "fresh" if points else "unknown",
        "max_range_mm": 4000,
        "angle_convention": "0=sensor_reference; clockwise; mounting_unverified",
        "points": points or [],
        "error": error,
    }


class SerialLidarProvider:
    def __init__(
        self, port, revision, baud=115200, serial_factory=None, clock=time.monotonic
    ):
        if not port or not revision or baud != 115200:
            raise ValueError(
                "Explicit port, confirmed A1 revision and standard 115200 baud are required."
            )
        self.port, self.revision, self.baud = port, revision, baud
        self.serial_factory, self.clock = serial_factory, clock
        self.device = None
        self.parser = StandardParser()
        self.current = frame(clock=clock)
        self.points = []
        self.last_packet = clock()
        self.started = False
        self.has_boundary = False

    def start(self, *, confirmed=False):
        if not confirmed:
            raise PermissionError(
                "Starting acquisition can rotate the LiDAR. Explicit confirmation required."
            )
        if self.device is not None:
            raise RuntimeError("Reader already open")
        try:
            if self.serial_factory is None:
                from serial import Serial

                factory = Serial
            else:
                factory = self.serial_factory
            # DTR is configured before opening; opening the port can still have
            # electrical effects on a particular USB kit: physical validation pending.
            self.device = factory(
                port=None, baudrate=self.baud, timeout=0.2, write_timeout=0.2
            )
            self.device.port = self.port
            self.device.dtr = True
            self.device.open()
            self.device.reset_input_buffer()
            self.device.write(b"\xa5\x50")  # GET_INFO, no drive motor commands
            info = self._descriptor(20, 0, 4)
            if len(info) != 20 or info[0] >> 4 != 1:
                raise ValueError(
                    "Device does not identify as A1 family; stop and verify revision."
                )
            self.device.write(b"\xa5\x52")
            health = self._descriptor(3, 0, 6)
            if len(health) != 3 or health[0] != 0:
                raise ValueError("LiDAR health is not OK")
            self.device.dtr = False  # Standard compatible A1 USB-kit rotation enable.
            self.device.write(b"\xa5\x20")  # Standard SCAN, not express mode
            self._descriptor(5, 1, 0x81, payload=False)
            self.started = True
            self.current = frame("no_data", clock=self.clock)
            self.last_packet = self.clock()
        except Exception as error:
            self.close()
            self.current = frame("error", error=str(error), clock=self.clock)
            raise

    def _read_exact(self, count):
        result = bytearray()
        deadline = self.clock() + 2
        while len(result) < count:
            part = self.device.read(count - len(result))
            if not part or self.clock() > deadline:
                raise TimeoutError("A1 response timed out")
            result.extend(part)
        return bytes(result)

    def _descriptor(self, size, mode, kind, payload=True):
        header = self._read_exact(7)
        descriptor = int.from_bytes(header[2:6], "little")
        if (
            header[:2] != b"\xa5\x5a"
            or descriptor & 0x3FFFFFFF != size
            or descriptor >> 30 != mode
            or header[6] != kind
        ):
            raise ValueError("Unsupported or invalid A1 response descriptor")
        return self._read_exact(size) if payload else None

    def read_once(self):
        if not self.started:
            raise RuntimeError("Reader is not started")
        try:
            data = self.device.read(512)
            if data:
                decoded = self.parser.feed(data)
                if decoded:
                    self.last_packet = self.clock()
                for point in decoded:
                    if point.pop("start"):
                        if self.has_boundary and self.points:
                            self.current = frame("valid", self.points, clock=self.clock)
                        self.has_boundary = True
                        self.points = []
                    if self.has_boundary:
                        self.points.append(point)
                    if len(self.points) > 4096:
                        raise ValueError("No revolution boundary within bounded scan")
            if self.clock() - self.last_packet > 3:
                raise TimeoutError("No valid A1 packets; check connection")
            return self.latest()
        except Exception as error:
            self.close()
            self.current = frame(
                (
                    "disconnected"
                    if isinstance(error, (OSError, TimeoutError))
                    else "error"
                ),
                error=str(error),
                clock=self.clock,
            )
            return self.latest()

    def latest(self):
        data = dict(self.current)
        stamp = data.get("received_monotonic")
        data["age_ms"] = (
            max(0, int((self.clock() - stamp) * 1000)) if stamp is not None else None
        )
        if (
            data["age_ms"] is not None
            and data["age_ms"] > 2000
            and data["status"] == "valid"
        ):
            data.update(status="stale", freshness="stale", valid=False)
        return data

    def close(self):
        device, self.device = self.device, None
        self.started = False
        if device:
            try:
                if device.is_open:
                    device.write(b"\xa5\x25")
                    device.dtr = True
            except OSError:
                pass  # Cable loss must not prevent releasing the handle.
            finally:
                device.close()
        self.current = frame("disconnected", clock=self.clock)
