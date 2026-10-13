import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, X } from 'lucide-react'
import './InstallPrompt.css'

export function InstallInstructions() {
  const { t } = useTranslation()
  return <section className="pilot-panel"><h3>{t('work.installTitle')}</h3>
    <p>{t('work.installManual')}</p><p>{t('work.installNetwork')}</p>
  </section>
}

export default function InstallPrompt({ ready = false }) {
  const { t } = useTranslation()
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [dismissed, setDismissed] = useState(() => {
    const previous = Number(localStorage.getItem('pwa-install-dismissed') || 0)
    return Date.now() - previous < 7 * 86400000
  })
  const [installed, setInstalled] = useState(false)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    if (window.matchMedia?.('(display-mode: standalone)').matches) { setInstalled(true); return }
    const available = event => { event.preventDefault(); setDeferredPrompt(event) }
    const completed = () => { setInstalled(true); setDeferredPrompt(null) }
    window.addEventListener('beforeinstallprompt', available)
    window.addEventListener('appinstalled', completed)
    return () => { window.removeEventListener('beforeinstallprompt', available); window.removeEventListener('appinstalled', completed) }
  }, [])
  if (!ready || dismissed || installed || !deferredPrompt) return null
  return <aside className="install-prompt" aria-label={t('work.installTitle')}>
    <div className="install-prompt-content"><Download aria-hidden="true" size={24} />
      <div className="install-text"><strong>{t('work.installTitle')}</strong><p>{t('work.installDescription')}</p>
        {failed && <p role="status">{t('work.installManual')}</p>}</div>
      <div className="install-actions"><button className="install-button" onClick={async () => {
        try { await deferredPrompt.prompt(); await deferredPrompt.userChoice; setDeferredPrompt(null) }
        catch { setFailed(true) }
      }}>{t('work.install')}</button>
        <button className="dismiss-button" aria-label={t('common.close')} onClick={() => {
          localStorage.setItem('pwa-install-dismissed', String(Date.now())); setDismissed(true)
        }}><X size={20} /></button></div>
    </div>
  </aside>
}
