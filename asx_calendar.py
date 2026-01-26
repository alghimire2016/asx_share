from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
import pytz

SYD = pytz.timezone("Australia/Sydney")

ASX_OPEN = time(10, 0)   # 10:00
ASX_CLOSE = time(16, 0)  # 16:00


# ---------- Easter (Gregorian) ----------
def easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm for Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def second_monday(year: int, month: int) -> date:
    d = date(year, month, 1)
    # move to Monday
    while d.weekday() != 0:
        d += timedelta(days=1)
    # second Monday
    return d + timedelta(days=7)


def _observed_fixed(d: date) -> date:
    """
    Observed day for fixed-date holidays (New Year, Australia Day).
    Sat/Sun -> next Monday.
    """
    if d.weekday() == 5:      # Sat
        return d + timedelta(days=2)
    if d.weekday() == 6:      # Sun
        return d + timedelta(days=1)
    return d


def _christmas_boxing_observed(year: int) -> set[date]:
    """
    Handles collisions when Christmas/Boxing fall on weekend.
    Typical ASX closures follow observed public holidays:
      - if Dec 25 is Sat -> Christmas observed Mon 27
      - if Dec 26 is Sun -> Boxing observed Tue 28 (because Mon 27 already used)
      - if Dec 25 is Sun -> Boxing is Mon 26, Christmas observed Tue 27
    """
    xmas = date(year, 12, 25)
    boxing = date(year, 12, 26)

    days = set()

    # If both weekday, just those dates:
    if xmas.weekday() not in (5, 6) and boxing.weekday() not in (5, 6):
        days.add(xmas)
        days.add(boxing)
        return days

    # Build observed days avoiding collisions
    # Start with Boxing observed on Monday if weekend
    # then Christmas observed next available weekday
    # (this matches common AU public holiday substitution behaviour)
    obs = set()

    # Boxing observed
    if boxing.weekday() == 5:        # Sat -> Mon 28
        obs_box = boxing + timedelta(days=2)
    elif boxing.weekday() == 6:      # Sun -> Mon 27
        obs_box = boxing + timedelta(days=1)
    else:
        obs_box = boxing

    obs.add(obs_box)

    # Christmas observed
    if xmas.weekday() == 5:          # Sat -> Mon 27
        obs_x = xmas + timedelta(days=2)
    elif xmas.weekday() == 6:        # Sun -> Mon 26 (but might collide with boxing)
        obs_x = xmas + timedelta(days=1)
    else:
        obs_x = xmas

    # avoid collision: push forward until free weekday
    while obs_x in obs or obs_x.weekday() >= 5:
        obs_x += timedelta(days=1)

    obs.add(obs_x)
    return obs


def asx_public_holidays(year: int) -> set[date]:
    """
    ASX cash market commonly closes on:
      - New Year's Day (observed)
      - Australia Day (observed)
      - Good Friday
      - Easter Monday
      - ANZAC Day (Apr 25) (no substitute needed for trading because weekend already closed)
      - King's Birthday (2nd Monday of June, NSW)
      - Christmas Day (observed)
      - Boxing Day (observed)
    """
    hol = set()

    # Fixed + observed
    hol.add(_observed_fixed(date(year, 1, 1)))    # New Year
    hol.add(_observed_fixed(date(year, 1, 26)))   # Australia Day

    # Easter
    easter = easter_sunday(year)
    hol.add(easter - timedelta(days=2))           # Good Friday
    hol.add(easter + timedelta(days=1))           # Easter Monday

    # ANZAC Day (ASX calendar lists it as closed; weekend is already closed anyway)
    hol.add(date(year, 4, 25))

    # King's Birthday (NSW)
    hol.add(second_monday(year, 6))

    # Christmas + Boxing observed with collision handling
    hol |= _christmas_boxing_observed(year)

    return hol


def is_asx_trading_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    hol = asx_public_holidays(d.year)
    return d not in hol


@dataclass
class MarketStatus:
    is_open: bool
    label: str
    now: datetime
    next_open: datetime | None


def next_asx_open(now: datetime) -> datetime:
    """
    Finds next market open datetime (10:00 Sydney) on the next trading day.
    """
    local = now.astimezone(SYD)
    d = local.date()

    # If today is trading day but before open -> today 10:00
    if is_asx_trading_day(d) and local.time() < ASX_OPEN:
        return SYD.localize(datetime(d.year, d.month, d.day, ASX_OPEN.hour, ASX_OPEN.minute))

    # Otherwise go forward day by day
    dd = d + timedelta(days=1)
    while not is_asx_trading_day(dd):
        dd += timedelta(days=1)

    return SYD.localize(datetime(dd.year, dd.month, dd.day, ASX_OPEN.hour, ASX_OPEN.minute))


def get_asx_status(now: datetime | None = None) -> MarketStatus:
    now = now or datetime.now(SYD)
    local = now.astimezone(SYD)
    d = local.date()

    if not is_asx_trading_day(d):
        return MarketStatus(False, "CLOSED (Holiday/Weekend)", local, next_asx_open(local))

    if local.time() < ASX_OPEN:
        return MarketStatus(False, "CLOSED (Pre-open)", local, next_asx_open(local))

    if local.time() > ASX_CLOSE:
        return MarketStatus(False, "CLOSED (After-hours)", local, next_asx_open(local))

    return MarketStatus(True, "OPEN (Live trading)", local, None)
