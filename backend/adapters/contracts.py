from typing import Literal, Protocol, TypedDict

Source = Literal["mock", "replay", "real"]


class ScanPoint(TypedDict):
    angle_deg: float
    distance: float | None
    quality: int | None
    valid: bool


class Scan(TypedDict):
    sensor_id: str
    captured_at: str
    status: str
    source: Source
    unit: Literal["mm"]
    valid: bool
    points: list[ScanPoint]


class RobotProvider(Protocol):
    def status(self) -> dict: ...
    def command(self, data: dict) -> tuple[dict, int]: ...


class TelemetryProvider(Protocol):
    def latest(self) -> dict: ...


class NPKProvider(Protocol):
    def capture(self, point_label: str) -> dict: ...


class LidarProvider(Protocol):
    def latest(self) -> Scan: ...


# Future Esp32RobotProvider, RealNPKProvider, SerialLidarProvider and
# WirelessLidarProvider must satisfy these protocols. No physical implementation
# or serial dependency is present in Gate 1.
