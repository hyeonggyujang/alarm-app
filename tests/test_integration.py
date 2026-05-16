"""
Integration test — verifies the full alarm flow without real audio.

Run with:
    pytest tests/test_integration.py -v

Audio is mocked so this runs safely on Windows dev machines
with no speaker or pygame dependency issues.
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


# ── Mock pygame before any app module imports it ──────────────────────────────
pygame_mock = MagicMock()
pygame_mock.mixer.music.get_busy.return_value = True

import sys
sys.modules["pygame"] = pygame_mock
sys.modules["pygame.mixer"] = pygame_mock.mixer
# ─────────────────────────────────────────────────────────────────────────────

from app.main import app
from app.state import state, CurveType
from app.curves import get_volume, RAMP_SECONDS, MAX_VOLUME, MIN_VOLUME
from app import scheduler as sched_module

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def reset_state():
    """Reset shared state and cancel any scheduled jobs between tests."""
    if state.job_id:
        try:
            sched_module.scheduler.remove_job(state.job_id)
        except Exception:
            pass
    state.wake_time = None
    state.is_running = False
    state.current_volume = 0.0
    state.job_id = None
    sched_module._stop_event.set()  # kill any running audio thread


# ── Status endpoint ───────────────────────────────────────────────────────────

def test_status_idle():
    reset_state()
    r = client.get("/alarm/status")
    assert r.status_code == 200
    body = r.json()
    assert body["is_running"] is False
    assert body["wake_time"] is None
    assert body["current_volume"] == 0.0


# ── Set alarm endpoint ────────────────────────────────────────────────────────

def test_set_alarm_valid():
    reset_state()
    wake = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
    r = client.post("/alarm/set", json={"wake_time": wake, "curve": "linear"})
    assert r.status_code == 200
    body = r.json()
    assert body["message"] == "Alarm scheduled"
    assert body["curve"] == "linear"
    assert "ramp_starts_at" in body


def test_set_alarm_invalid_format():
    reset_state()
    r = client.post("/alarm/set", json={"wake_time": "7:5", "curve": "linear"})
    assert r.status_code == 400
    assert "HH:MM" in r.json()["detail"]


def test_set_alarm_past_time_schedules_tomorrow():
    reset_state()
    # Use a time 1 minute in the past — should roll to tomorrow
    past = (datetime.now() - timedelta(minutes=1)).strftime("%H:%M")
    r = client.post("/alarm/set", json={"wake_time": past, "curve": "linear"})
    assert r.status_code == 200
    wake_dt = datetime.strptime(r.json()["wake_time"], "%Y-%m-%d %H:%M")
    assert wake_dt > datetime.now()


def test_set_alarm_all_curves():
    for curve in ["linear", "logarithmic", "exponential"]:
        reset_state()
        wake = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
        r = client.post("/alarm/set", json={"wake_time": wake, "curve": curve})
        assert r.status_code == 200
        assert r.json()["curve"] == curve


def test_set_alarm_invalid_curve():
    reset_state()
    wake = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
    r = client.post("/alarm/set", json={"wake_time": wake, "curve": "random"})
    assert r.status_code == 422  # pydantic validation error


# ── Stop endpoint ─────────────────────────────────────────────────────────────

def test_stop_with_no_alarm():
    reset_state()
    r = client.delete("/alarm/stop")
    assert r.status_code == 404


def test_stop_active_alarm():
    reset_state()
    wake = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
    client.post("/alarm/set", json={"wake_time": wake, "curve": "linear"})
    r = client.delete("/alarm/stop")
    assert r.status_code == 200
    assert r.json()["message"] == "Alarm stopped"


def test_stop_clears_state():
    reset_state()
    wake = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
    client.post("/alarm/set", json={"wake_time": wake, "curve": "linear"})
    client.delete("/alarm/stop")
    status = client.get("/alarm/status").json()
    assert status["is_running"] is False
    assert status["wake_time"] is None


# ── Volume curve progression ──────────────────────────────────────────────────

def test_volume_ramp_progression():
    """Simulate a full 30-minute ramp and verify volume increases monotonically."""
    curve = "linear"
    volumes = [get_volume(t, curve) for t in range(0, RAMP_SECONDS + 1, 60)]

    # Must be monotonically increasing
    for i in range(1, len(volumes)):
        assert volumes[i] >= volumes[i - 1], (
            f"Volume dropped at t={i*60}s: {volumes[i-1]} → {volumes[i]}"
        )

    # Must start near 0 and end at max
    assert volumes[0] == MIN_VOLUME
    assert volumes[-1] == MAX_VOLUME


def test_volume_never_exceeds_80_percent():
    """Volume must never exceed 0.8 regardless of elapsed time or curve."""
    for curve in ["linear", "logarithmic", "exponential"]:
        # Test beyond the ramp window too
        for t in range(0, RAMP_SECONDS + 300, 30):
            v = get_volume(t, curve)
            assert v <= MAX_VOLUME, f"{curve} exceeded MAX_VOLUME at t={t}: {v}"


def test_logarithmic_rises_faster_early():
    """Log curve should be louder than linear in the first 20% of the ramp."""
    t = int(RAMP_SECONDS * 0.2)
    assert get_volume(t, "logarithmic") > get_volume(t, "linear")


def test_exponential_rises_slower_early():
    """Exponential curve should be quieter than linear in the first 20% of the ramp."""
    t = int(RAMP_SECONDS * 0.2)
    assert get_volume(t, "exponential") < get_volume(t, "linear")


def test_all_curves_converge_at_end():
    """All curves must reach exactly MAX_VOLUME at the end of the ramp."""
    for curve in ["linear", "logarithmic", "exponential"]:
        assert get_volume(RAMP_SECONDS, curve) == MAX_VOLUME, (
            f"{curve} did not reach MAX_VOLUME at end of ramp"
        )