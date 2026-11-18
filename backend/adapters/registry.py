import threading
from weakref import WeakKeyDictionary
from .rack import MockRackProvider, BlockedRackProvider
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

from django.conf import settings
from .unconfigured import UnconfiguredRobotProvider

unconfigured_robot = UnconfiguredRobotProvider()
real_lidar = LidarSources(lidar, source="real")
replay_lidar = LidarSources(lidar, source="replay")


def is_demonstration():
    return settings.SEMI_MODE == "demonstration"


def current_robot():
    return robot if is_demonstration() else unconfigured_robot


def current_npk():
    # No guessed sensor protocol or synthetic fallback in operational mode.
    return npk if is_demonstration() else None


_demo_domains = WeakKeyDictionary()
_domains_lock = threading.RLock()
blocked_rack = BlockedRackProvider()


def demo_domains(robot, plot_id=None):
    with _domains_lock:
        entry = _demo_domains.get(robot)
        if entry is None or entry[0] != robot.simulation_id:
            entry = (
                robot.simulation_id,
                MockRackProvider(f"demo-{plot_id or 'default'}"),
                MockLidarProvider(),
            )
            _demo_domains[robot] = entry
        return entry[1], entry[2]
