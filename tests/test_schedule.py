"""Poll-cadence tests.

None of this was covered before, which is how the fast window came to be
anchored to Turkish local time while EDGAR disseminates on the US Eastern
clock. MSTR's weekly 8-K lands in a tight 07:55-08:25 ET band; under the old
TRT-anchored window that band sat inside the ultra window in summer and
entirely outside it — on a 300s poll — from November to March.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


def et(y, m, d, hh, mm, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=bot.ET_TZ)


# Real EDGAR acceptance timestamps for MSTR bitcoin-purchase 8-Ks.
OBSERVED_FILINGS_ET = [
    (2025, 10, 14, 7, 59),   # EDT
    (2025, 11, 17, 8, 24),   # EST
    (2025, 12, 15, 8, 0),    # EST
    (2025, 12, 22, 8, 1),    # EST
    (2026, 6, 29, 8, 18),    # EDT
    (2026, 8, 3, 7, 55),     # EDT
]


@pytest.mark.parametrize("y,m,d,hh,mm", OBSERVED_FILINGS_ET)
def test_every_observed_filing_lands_in_the_ultra_window(y, m, d, hh, mm):
    mode, interval, _ = bot.poll_schedule(et(y, m, d, hh, mm))
    assert mode == "Ultra High-Speed Mode", (
        f"{hh:02d}:{mm:02d} ET fell into {mode}")
    assert interval == bot.POLL_INTERVAL_CRITICAL


@pytest.mark.parametrize("y,m,d,hh,mm", OBSERVED_FILINGS_ET)
def test_dst_does_not_move_the_window_relative_to_edgar(y, m, d, hh, mm):
    """The same ET wall time must get the same cadence in both offsets.

    Under the old TRT-anchored window the winter filings above resolved to
    16:00-16:24 TRT and were polled every 300 seconds.
    """
    when = et(y, m, d, hh, mm)
    trt = when.astimezone(timezone(timedelta(hours=3)))
    mode, _, _ = bot.poll_schedule(when)
    assert mode == "Ultra High-Speed Mode", (
        f"{hh:02d}:{mm:02d} ET == {trt:%H:%M} TRT resolved to {mode}")


def test_window_boundaries():
    us, ue = bot.ULTRA_WINDOW_ET
    fs, fe = bot.FAST_WINDOW_ET
    day = (2026, 8, 3)  # a Monday

    assert bot.poll_schedule(et(*day, us // 60, us % 60))[0] == "Ultra High-Speed Mode"
    assert bot.poll_schedule(et(*day, (us - 1) // 60, (us - 1) % 60))[0] == "Fast Mode"
    # The ultra window is half-open: its end minute belongs to Fast.
    assert bot.poll_schedule(et(*day, ue // 60, ue % 60))[0] == "Fast Mode"
    assert bot.poll_schedule(et(*day, (ue - 1) // 60, (ue - 1) % 60))[0] == "Ultra High-Speed Mode"
    assert bot.poll_schedule(et(*day, fs // 60, fs % 60))[0] == "Fast Mode"
    assert bot.poll_schedule(et(*day, (fs - 1) // 60, (fs - 1) % 60))[0] == "Normal Mode"
    assert bot.poll_schedule(et(*day, fe // 60, fe % 60))[0] == "Normal Mode"


def test_no_minute_of_the_business_day_is_left_at_the_normal_interval():
    """EDGAR disseminates 06:00-22:00 ET; nothing in the fast band may fall
    back to the slow cadence, and no minute may be left unclassified."""
    for minute in range(bot.FAST_WINDOW_ET[0], bot.FAST_WINDOW_ET[1]):
        mode, interval, _ = bot.poll_schedule(et(2026, 8, 3, minute // 60, minute % 60))
        assert mode in ("Fast Mode", "Ultra High-Speed Mode")
        assert interval <= bot.POLL_INTERVAL_FAST


def test_weekend_is_normal_mode():
    # 2026-08-01 is a Saturday, 2026-08-02 a Sunday.
    for day in (1, 2):
        mode, _, _ = bot.poll_schedule(et(2026, 8, day, 8, 0))
        assert mode == "Normal Mode"


def test_sleep_never_overshoots_a_window_opening():
    """The old loop picked an interval and slept it out.

    A tick at 13:59 TRT chose the 300s normal interval and woke at 14:04 —
    five minutes of total blindness beginning one minute before the fast
    window opened. The schedule now reports the distance to the next
    boundary so the loop can cap its sleep.
    """
    us, _ = bot.ULTRA_WINDOW_ET
    fs, _ = bot.FAST_WINDOW_ET

    for edge in (us, fs):
        before = edge - 1
        when = et(2026, 8, 3, before // 60, before % 60, 0)
        _, interval, to_boundary = bot.poll_schedule(when)
        budget = min(interval, to_boundary)
        woke = when + timedelta(seconds=budget)
        woke_minute = woke.hour * 60 + woke.minute
        assert woke_minute <= edge, (
            f"slept past the {edge // 60:02d}:{edge % 60:02d} ET boundary")


def test_normal_interval_is_not_five_minutes():
    """Anything outside the fast band used to be found up to 300s late."""
    assert bot.POLL_INTERVAL_NORMAL <= 60


def test_boundary_distance_is_always_positive():
    for minute in range(0, 24 * 60, 7):
        _, _, to_boundary = bot.poll_schedule(et(2026, 8, 3, minute // 60, minute % 60, 30))
        assert to_boundary > 0
