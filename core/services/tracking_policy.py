"""Write-time bounds shared by all tracking creation and correction paths."""

from datetime import datetime, time, timedelta, timezone

from exceptions import ValidationError

RECORD_WINDOW_DAYS = 365
JAPAN_TIME = timezone(timedelta(hours=9))


def validate_record_time(value):
    now = datetime.now(timezone.utc)
    timestamp = value or now
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    first_day = now.astimezone(JAPAN_TIME).date() - timedelta(days=RECORD_WINDOW_DAYS - 1)
    earliest = datetime.combine(first_day, time.min, tzinfo=JAPAN_TIME)
    if timestamp < earliest or timestamp > now + timedelta(seconds=60):
        raise ValidationError("Record time must be within the last 365 Japan calendar days and not in the future")
    return timestamp.replace(tzinfo=None)
