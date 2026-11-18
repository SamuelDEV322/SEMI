from django.urls import path
from . import views
from apps.agriculture.setup_views import setup, surface_trial

from apps.devices.views import NextCommandView, TelemetryView, StatusView

from apps.devices.locations import adc_history, plots
from apps.devices.manual import BenchPoll, manual_control

urlpatterns = [
    path("api/device/bench/", BenchPoll.as_view()),
    path("api/control/manual/", manual_control),
    path("api/measurements/adc/", adc_history),
    path("api/setup/plots/", plots),
    path("api/device/commands/next/", NextCommandView.as_view()),
    path("api/device/telemetry/", TelemetryView.as_view()),
    path("api/device/status/", StatusView.as_view()),
    path("api/setup/", setup),
    path("api/demo/surface/", surface_trial),
    path("api/lidar/source/", views.lidar_source),
    path("api/sampling-points/", views.points),
    path("api/sampling-points/<int:point_id>/", views.points),
    path("api/health/", views.health),
    path("api/robot/status/", views.robot_status),
    path("api/measurements/latest/", views.latest),
    path("api/measurements/capture/", views.capture),
    path("api/measurements/history/", views.history),
    path("api/npk/samples/", views.samples),
    path("api/lidar/latest/", views.lidar),
    path("api/control/command/", views.command),
    path("api/demo/scenario/", views.scenario),
    path("api/demo/capture/", views.capture),
]
