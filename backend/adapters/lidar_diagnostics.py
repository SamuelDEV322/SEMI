"""Passive USB inventory and scan lifecycle. Never opens a serial handle."""

import os
import time
import threading
from datetime import datetime, timezone

_cache = None
_cache_at = 0.0
_lock = threading.Lock()


def passive_ports():
    global _cache, _cache_at
    with _lock:
        now = time.monotonic()
        if _cache is not None and 0 <= now - _cache_at < 2:
            return _cache
        try:
            from serial.tools import list_ports

            ports = [
                {
                    "port": p.device,
                    "description": p.description,
                    "usb": p.vid is not None and p.pid is not None,
                }
                for p in list_ports.comports()
            ]
            result = {"status": "ok", "ports": ports}
        except (ImportError, OSError):
            result = {"status": "unavailable", "ports": []}
        _cache, _cache_at = result, now
        return result


def annotate(data, clock=time.monotonic):
    inventory = passive_ports()
    reader = data.get("reader") or {}
    if not isinstance(reader, dict):
        reader = {}
    selected = os.getenv("SEMI_LIDAR_PORT") or reader.get("port")
    candidate = next(
        (
            p
            for p in inventory["ports"]
            if selected and p["port"].casefold() == str(selected).casefold()
        ),
        None,
    )
    usb = (
        candidate["usb"]
        if candidate
        else (
            False
            if inventory["status"] == "ok"
            and (selected or not any(p["usb"] for p in inventory["ports"]))
            else None
        )
    )
    stamp = reader.get("heartbeat_monotonic")
    wall = reader.get("heartbeat_at")
    age = None
    if type(stamp) in (int, float) and isinstance(wall, str):
        try:
            import math

            wall_date = datetime.fromisoformat(wall)
            delta = (clock() - stamp) * 1000
            wall_delta = (datetime.now(timezone.utc) - wall_date).total_seconds() * 1000
            if math.isfinite(delta) and delta >= 0 and wall_delta >= -5000:
                age = max(delta, wall_delta, 0)
        except (ValueError, TypeError, OverflowError):
            pass
    running = (
        age is not None
        and age <= 2000
        and reader.get("phase") in ["starting", "reading"]
    )
    identified = reader.get("identity_verified") is True
    if data.get("status") == "error":
        state = "error"
    elif (
        selected
        and reader.get("port")
        and str(selected).casefold() != str(reader["port"]).casefold()
    ):
        state = "error"
        data.update(valid=False, status="error")
    elif reader and not running and reader.get("phase") not in ["closed", "failed"]:
        state = "interrupted"
        data.update(valid=False, status="stale", freshness="stale")
    elif data.get("status") == "stale":
        state = "stale"
    elif data.get("valid") and (not reader or running):
        state = "active"
    elif running and identified and data.get("status") in ["no_data", "valid"]:
        state = "waiting"
    elif data.get("status") == "disconnected" and reader.get("phase") in [
        "closed",
        "failed",
    ]:
        state = "interrupted"
    elif candidate and usb:
        state = "usb_detected"
    elif inventory["status"] == "ok" and not any(p["usb"] for p in inventory["ports"]):
        state = "not_detected"
    elif inventory["status"] == "ok" and selected and not candidate:
        state = "not_detected"
    elif inventory["status"] == "ok" and not selected:
        state = "usb_unidentified"
    else:
        state = "unknown"
    data["acquisition"] = {
        "state": state,
        "selected_port": selected,
        "usb_detected": usb,
        "sensor_identified": identified if reader else None,
        "reader_running": running if reader else None,
        "reader_age_ms": round(age) if age is not None else None,
        "inventory_status": inventory["status"],
        "ports": inventory["ports"],
        "reader_start_authorized": os.getenv("SEMI_LIDAR_DIAGNOSTICS") == "1",
    }
    return data
