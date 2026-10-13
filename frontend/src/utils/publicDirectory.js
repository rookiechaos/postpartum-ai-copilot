import { japanDay } from './japanTime'

export function publicHttps(value) {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : null
  } catch { return null }
}

export function phoneHref(value) {
  const number = (value || '').replace(/[\s().-]/g, '')
  return /^\+?[0-9#]{3,20}$/.test(number) ? `tel:${number.replaceAll('#', '%23')}` : null
}

export function needsReview(checkedOn, now = new Date()) {
  if (!checkedOn) return true
  const checked = new Date(`${checkedOn}T00:00:00+09:00`)
  const today = new Date(`${japanDay(now)}T00:00:00+09:00`)
  return !Number.isFinite(checked.getTime()) || today.getTime() - checked.getTime() >= 30 * 86400000
}
