import { japanDay, utcDate } from './japanTime'

export function periodBounds(period, now = Date.now()) {
  const midnight = new Date(`${japanDay(new Date(now))}T00:00:00+09:00`).getTime()
  return period === 'last24' ? [now - 86400000, now + 60000]
    : period === 'yesterday' ? [midnight - 86400000, midnight] : [midnight, midnight + 86400000]
}
export function inCarePeriod(record, period, now = Date.now()) {
  const [start, end] = periodBounds(period, now)
  const event = utcDate(record.timestamp).getTime()
  const finished = record.end_timestamp ? utcDate(record.end_timestamp).getTime() : event
  return event < end && (event >= start || finished > start)
}
