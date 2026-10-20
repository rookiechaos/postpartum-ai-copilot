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


def validate_record_interval(values):
    """Keep an explicitly confirmed end time consistent with whole-minute duration."""
    end = values.get("end_timestamp")
    if end is None:
        return
    if values["entry_type"] not in ("feeding", "sleep"):
        raise ValidationError("Only feeding and sleep records can have an end time")
    end = validate_record_time(end)
    if end < values["timestamp"]:
        raise ValidationError("The end time must not precede the start time")
    minutes = int((end - values["timestamp"]).total_seconds() // 60)
    field = "duration_minutes" if values["entry_type"] == "feeding" else "sleep_duration_minutes"
    if values.get(field) is not None and values[field] != minutes:
        raise ValidationError("Review start, end and duration together")
    values["end_timestamp"] = end
    values[field] = minutes
