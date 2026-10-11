import { japanDateTime } from './japanTime'

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
