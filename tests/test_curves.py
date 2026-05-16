import pytest
from app.curves import get_volume, MAX_VOLUME, RAMP_SECONDS, MIN_VOLUME


def test_starts_at_zero():
    assert get_volume(0, "linear") == MIN_VOLUME


def test_ends_at_max_volume():
    assert get_volume(RAMP_SECONDS, "linear") == MAX_VOLUME
    assert get_volume(RAMP_SECONDS, "logarithmic") == MAX_VOLUME
    assert get_volume(RAMP_SECONDS, "exponential") == MAX_VOLUME


def test_linear_midpoint():
    vol = get_volume(RAMP_SECONDS / 2, "linear")
    expected = MIN_VOLUME + (MAX_VOLUME - MIN_VOLUME) / 2
    assert abs(vol - expected) < 0.01


def test_log_rises_faster_than_linear_early():
    t = RAMP_SECONDS * 0.1
    assert get_volume(t, "logarithmic") > get_volume(t, "linear")


def test_exp_rises_slower_than_linear_early():
    t = RAMP_SECONDS * 0.1
    assert get_volume(t, "exponential") < get_volume(t, "linear")


def test_never_exceeds_max():
    for curve in ["linear", "logarithmic", "exponential"]:
        for t in range(0, RAMP_SECONDS + 60, 60):
            assert get_volume(t, curve) <= MAX_VOLUME


def test_unknown_curve_falls_back_to_linear():
    vol = get_volume(RAMP_SECONDS / 2, "unknown")
    assert abs(vol - get_volume(RAMP_SECONDS / 2, "linear")) < 0.001

def test_volume_ramp_progression():
    curve = "linear"
    volumes = [get_volume(t, curve) for t in range(0, RAMP_SECONDS + 1, 60)]

    for i in range(1, len(volumes)):
        assert volumes[i] >= volumes[i - 1]

    assert volumes[0] == MIN_VOLUME
    assert volumes[-1] == MAX_VOLUME


def test_never_exceeds_max():
    for curve in ["linear", "logarithmic", "exponential"]:
        for t in range(0, RAMP_SECONDS + 60, 60):
            assert get_volume(t, curve) <= MAX_VOLUME


def test_never_below_min():
    for curve in ["linear", "logarithmic", "exponential"]:
        for t in range(0, RAMP_SECONDS + 60, 60):
            assert get_volume(t, curve) >= MIN_VOLUME