from .mock import (
    MockRobotProvider,
    MockTelemetryProvider,
    MockNPKProvider,
    MockLidarProvider,
)

robot = MockRobotProvider()
telemetry = MockTelemetryProvider(robot)
npk = MockNPKProvider()
lidar = MockLidarProvider(robot)
from .lidar_sources import LidarSources

lidar_sources = LidarSources(lidar)
