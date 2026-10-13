import { japanDay } from './japanTime'

export const RECORD_WINDOW_DAYS = 365

// Include today and the previous 364 Japan calendar days, matching the write API.
export function earliestRecordTime(now = new Date()) {
  const firstDay = japanDay(new Date(now.getTime() - (RECORD_WINDOW_DAYS - 1) * 86400000))
  return new Date(`${firstDay}T00:00:00+09:00`)
}
