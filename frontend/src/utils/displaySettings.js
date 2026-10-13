const defaults = { highContrast: false, fontSize: 'medium', reducedMotion: false }
const sizes = { small: '14px', medium: '16px', large: '18px', xlarge: '20px' }

export function readDisplaySettings() {
  try {
    const saved = JSON.parse(localStorage.getItem('accessibility_settings') || '{}')
    return { highContrast: saved?.highContrast === true,
      fontSize: Object.keys(sizes).includes(saved?.fontSize) ? saved.fontSize : 'medium',
      reducedMotion: saved?.reducedMotion === true }
  } catch { return { ...defaults } }
}

export function applyDisplaySettings(settings) {
  const root = document.documentElement
  root.classList.toggle('high-contrast', settings.highContrast)
  root.classList.toggle('reduced-motion', settings.reducedMotion)
  root.style.setProperty('--font-size-base', sizes[settings.fontSize] || sizes.medium)
}

export function saveDisplaySettings(settings) {
  applyDisplaySettings(settings)
  try { localStorage.setItem('accessibility_settings', JSON.stringify(settings)); return true }
  catch { return false }
}
