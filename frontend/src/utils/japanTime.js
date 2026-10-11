export function utcDate(value) {
  if (typeof value === 'string' && !/(Z|[+-]\d{2}:\d{2})$/i.test(value)) value += 'Z'
  return new Date(value)
}

export function japanDay(value = new Date()) {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(utcDate(value))
  const part = type => parts.find(value => value.type === type).value
  return `${part('year')}-${part('month')}-${part('day')}`
}

export function japanDateTime(value, language = 'ja') {
  return new Intl.DateTimeFormat(language.startsWith('ja') ? 'ja-JP' : 'en-GB', {
    timeZone: 'Asia/Tokyo', dateStyle: 'medium', timeStyle: 'short',
  }).format(utcDate(value))
}
