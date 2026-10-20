"""Calendar/rolling windows for viewing records, without inferring care gaps."""
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def period_bounds(period):
    now = datetime.now(timezone.utc)
    midnight = now.astimezone(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "last24":
        start, end = now - timedelta(hours=24), now + timedelta(seconds=60)
    elif period == "yesterday":
        start, end = midnight - timedelta(days=1), midnight
    else:
        start, end = midnight, midnight + timedelta(days=1)
    return start.astimezone(timezone.utc).replace(tzinfo=None), end.astimezone(timezone.utc).replace(tzinfo=None)


def in_period(record, start, end):
    def parse(value):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc).replace(tzinfo=None) if result.tzinfo else result
    event = parse(record["timestamp"])
    finished = parse(record["end_timestamp"]) if record.get("end_timestamp") else event
    return event < end and (event >= start or finished > start)
