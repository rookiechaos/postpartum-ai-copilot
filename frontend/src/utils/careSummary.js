import { japanDateTime, japanDay, utcDate } from './japanTime'

// Deliberate allowlist: chat, identity and free text are never implicitly exported.
export function buildCareSummary(entries, { includeParent = false, includeNotes = false, language = 'ja', t }) {
  const care = new Set(['feeding', 'diaper', 'sleep', 'pumping'])
  const parent = new Set(['mood', 'recovery'])
  return entries.filter(entry => care.has(entry.entry_type) || (includeParent && parent.has(entry.entry_type)))
    .map(entry => {
      const fields = [japanDateTime(entry.timestamp, language), t(`tracking.${entry.entry_type}`)]
      const measurements = {
        feeding: [['amount_ml', 'mL'], ['duration_minutes', t('pilot.minutes')]],
        pumping: [['pumped_amount_ml', 'mL']],
        sleep: [['sleep_duration_minutes', t('pilot.minutes')]],
        recovery: [['weight_kg', 'kg']],
      }
      for (const [key, unit] of measurements[entry.entry_type] || []) {
        if (entry[key] != null) fields.push(`${entry[key]} ${unit}`)
      }
      if (entry.entry_type === 'feeding' && entry.feeding_type) fields.push(t(`tracking.${entry.feeding_type}`))
      if (entry.entry_type === 'diaper' && entry.diaper_type) fields.push(t(`tracking.${entry.diaper_type}`))
      if (includeParent && entry.entry_type === 'mood' && entry.mood_level) fields.push(t(`tracking.${entry.mood_level}`))
      if (includeParent && entry.entry_type === 'recovery' && entry.breast_condition) fields.push(t(`tracking.${entry.breast_condition}`))
      if (includeNotes) {
        if (entry.notes) fields.push(entry.notes)
        if (includeParent && entry.entry_type === 'mood' && entry.mood_notes) fields.push(entry.mood_notes)
        if (includeParent && entry.entry_type === 'recovery' && entry.recovery_notes) fields.push(entry.recovery_notes)
      }
      return fields.join(' / ')
    }).join('\n')
}

export function buildConsultationSheet(entries, { days = 7, questions = [], includeParent = false,
  includeNotes = false, includeDetails = false, language = 'ja', t, now = new Date() }) {
  const end = japanDay(now)
  const start = japanDay(new Date(now.getTime() - (days - 1) * 86400000))
  const types = ['feeding', 'diaper', 'sleep', 'pumping', ...(includeParent ? ['mood', 'recovery'] : [])]
  const selected = entries.filter(entry => {
    if (!types.includes(entry.entry_type) || !Number.isFinite(utcDate(entry.timestamp).getTime())) return false
    const day = japanDay(entry.timestamp)
    return day >= start && day <= end
  }).sort((a, b) => utcDate(b.timestamp).getTime() - utcDate(a.timestamp).getTime())
  const asked = questions.map(value => value.trim()).filter(Boolean)
  if (selected.length === 0 && asked.length === 0) return ''
  const recordedDays = new Set(selected.map(entry => japanDay(entry.timestamp))).size
  const lines = [t('pilot.summaryHeader'), `${t('work.sheetPeriod')}: ${start} — ${end}`, '',
    t('work.sheetQuestions'), ...asked.map((value, index) => `${index + 1}. ${value}`)]
  if (!asked.length) lines.push(t('work.noQuestions'))
  lines.push('', t('work.recordedFacts'))
  for (const type of types) lines.push(`${t(`tracking.${type}`)}: ${selected.filter(entry => entry.entry_type === type).length} ${t('work.recordCount')}`)
  const recordedSleep = selected.reduce((sum, entry) => sum + (entry.entry_type === 'sleep' ? entry.sleep_duration_minutes || 0 : 0), 0)
  lines.push(`${t('work.recordedSleep')}: ${recordedSleep} ${t('pilot.minutes')}`,
    t('work.recordCoverage', { recordedDays, days }), t('work.missingIsUnknown'))
  if (includeDetails) {
    lines.push('', t('work.latestDetails'), buildCareSummary(selected.slice(0, 5), { includeParent, includeNotes, language, t }))
  }
  lines.push('', t('work.sheetFooter'))
  return lines.join('\n')
}
