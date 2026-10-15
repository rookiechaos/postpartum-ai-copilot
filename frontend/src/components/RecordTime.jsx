import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { japanDateTime, utcDate } from '../utils/japanTime'

// One clock per visible record list; hidden pages do not keep interval timers.
export function useRecordClock(visible) {
  const [now, setNow] = useState(Date.now)
  useEffect(() => {
    if (!visible) return
    const update = () => { if (document.visibilityState === 'visible') setNow(Date.now()) }
    update()
    const timer = setInterval(update, 60000)
    document.addEventListener('visibilitychange', update)
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', update) }
  }, [visible])
  return now
}

export default function RecordTime({ value, now }) {
  const { t, i18n } = useTranslation()
  const date = utcDate(value)
  if (value == null || !Number.isFinite(date.getTime())) return <span>{t('flows.overview.unknown')}</span>
  const language = i18n.resolvedLanguage || 'ja'
  const elapsed = (now ?? Date.now()) - date.getTime()
  let relative = ''
  // A future timestamp or a device clock difference must not appear as a past event.
  if (elapsed >= 0) {
    const [unit, size] = elapsed < 3600000 ? ['minute', 60000] : elapsed < 86400000 ? ['hour', 3600000] : ['day', 86400000]
    relative = elapsed < 60000 ? t('friendly.time.justNow')
      : new Intl.RelativeTimeFormat(language, { numeric: 'always' }).format(-Math.floor(elapsed / size), unit)
  }
  return <span className="record-time">
    {relative && <span className="record-time-relative">{relative}</span>}
    <time dateTime={date.toISOString()}>{t('friendly.time.jst', { time: japanDateTime(date, language) })}</time>
  </span>
}
