from datetime import datetime, time
import pytz

ASX_TZ = pytz.timezone("Australia/Sydney")

ASX_OPEN = time(10, 0)
ASX_CLOSE = time(16, 0)

def is_asx_open(now: datetime | None = None) -> bool:
    """
    Returns True if ASX is currently open (Mon–Fri, 10:00–16:00 Sydney time)
    """
    now = now or datetime.now(ASX_TZ)
    if now.weekday() >= 5:  # Saturday / Sunday
        return False

    t = now.time()
    return ASX_OPEN <= t <= ASX_CLOSE


def asx_status():
    """
    Returns (OPEN/CLOSED, human-readable reason)
    """
    now = datetime.now(ASX_TZ)
    if now.weekday() >= 5:
        return "CLOSED", "Weekend"
    if now.time() < ASX_OPEN:
        return "CLOSED", "Pre-market"
    if now.time() > ASX_CLOSE:
        return "CLOSED", "After-hours"
    return "OPEN", "Live trading"
