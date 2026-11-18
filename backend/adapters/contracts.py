from typing import Literal, NotRequired, Protocol, TypedDict

Source = Literal["mock", "replay", "real"]


class ScanPoint(TypedDict):
    angle_deg: float
    distance: float | None
    quality: int | None
    valid: bool


class Scan(TypedDict):
    sensor_id: str
    captured_at: str | None
    status: str
    source: Source
    unit: Literal["mm"]
    valid: bool
    points: list[ScanPoint]


class RobotProvider(Protocol):
    def status(self) -> dict: ...
    def command(self, data: dict) -> tuple[dict, int]: ...


class MotionCommand(TypedDict):
    domain: NotRequired[Literal["traction", "all"]]
    mode: Literal["demonstration", "operational"]
    action: Literal["forward", "backward", "left", "right", "stop"]
    speed: Literal["low", "medium"]
    session_id: str
    seq: int
    epoch: int
    window_id: str


LidarScan = Scan


class TelemetryProvider(Protocol):
    def latest(self) -> dict: ...


class NPKProvider(Protocol):
    def capture(self, point_label: str) -> dict: ...


class LidarProvider(Protocol):
    def latest(self) -> Scan: ...


# SerialLidarProvider is an explicit-start USB diagnostic implementation.
# Future Esp32RobotProvider, RealNPKProvider and WirelessLidarProvider must
# preserve provenance and implement these contracts without synthetic fallback.


class RackCommand(TypedDict):
    mode: Literal["demonstration"]
    domain: Literal["rack"]
    action: Literal["up", "down", "stop"]
    device_id: str
    request_id: str
    session_id: str
    seq: int
    epoch: int
    window_id: str
    max_duration_ms: int


class RackProvider(Protocol):
    def status(self) -> dict: ...
    def command(self, data: RackCommand) -> tuple[dict, int]: ...
