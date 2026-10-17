export const quickChoices = [
  { key: 'wet', data: { entry_type: 'diaper', diaper_type: 'wet' } },
  { key: 'dirty', data: { entry_type: 'diaper', diaper_type: 'dirty' } },
  { key: 'breast', data: { entry_type: 'feeding', feeding_type: 'breast' } },
  { key: 'formula', data: { entry_type: 'feeding', feeding_type: 'formula' } },
  { key: 'sleep', timer: 'sleep' }, { key: 'feedingTimer', timer: 'feeding' },
]
export const defaultQuickKeys = ['wet', 'dirty', 'breast', 'formula']
export function readQuickPreferences(userId) {
  try {
    const saved = JSON.parse(localStorage.getItem(`quick-actions:${userId}`) || 'null')
    if (Array.isArray(saved) && saved.length >= 1 && saved.length <= 4 && new Set(saved).size === saved.length
      && saved.every(key => quickChoices.some(choice => choice.key === key))) return saved
  } catch { /* A blocked browser store uses the default layout. */ }
  return [...defaultQuickKeys]
}
export function saveQuickPreferences(userId, keys) {
  // Only shortcut identifiers are stored on this device, never care data.
  try { localStorage.setItem(`quick-actions:${userId}`, JSON.stringify(keys)); return true }
  catch { return false }
}
