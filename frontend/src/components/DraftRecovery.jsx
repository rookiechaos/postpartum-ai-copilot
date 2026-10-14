import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { draftPreferenceEvent } from '../utils/useAccountDraft'

export function DraftRecoveryNotice({ draft, disabled = false, compact = false }) {
  const { t } = useTranslation()
  const blocked = disabled || draft.status === 'deleting'
  return <div className="draft-recovery">
    {draft.status === 'off' && <p className="field-hint">{t(compact ? 'ui.draft.offHint' : 'polish.recoveryOff')}</p>}
    {draft.candidate && <section className="pilot-panel" role="status"><h3>{t('polish.draftFound')}</h3>
      <p>{t('polish.draftRestoreNotice')}</p>
      <button type="button" className="pilot-button secondary" disabled={blocked} onClick={draft.recover}>{t('polish.restoreDraft')}</button>
      <button type="button" className="pilot-button secondary" disabled={blocked} onClick={draft.discard}>{t('polish.deleteDraft')}</button>
    </section>}
    {['unsaved', 'saving', 'saved', 'deleting', 'error', 'conflict'].includes(draft.status) && <p role="status">{t(`polish.draftStatus.${draft.status}`)}
      {['error', 'conflict'].includes(draft.status) && <button type="button" disabled={blocked} onClick={draft.reload}>{t('pilot.retry')}</button>}
    </p>}
  </div>
}

export default function DraftRecoverySettings() {
  const { t } = useTranslation()
  const [settings, setSettings] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    api.get('/api/drafts/settings').then(result => { if (active) setSettings(result) })
      .catch(() => { if (active) setError(t('pilot.loadFailed')) })
    return () => { active = false }
  }, [attempt])
  const change = async enabled => {
    if (busy || !settings) return
    setBusy(true); setError('')
    try {
      setSettings(await api.post('/api/drafts/settings', { enabled, revision: settings.revision }))
      window.dispatchEvent(new Event(draftPreferenceEvent))
    } catch { setError(t('polish.preferenceFailed')); setAttempt(value => value + 1) }
    finally { setBusy(false) }
  }
  return <section className="pilot-panel"><h3>{t('polish.draftRecovery')}</h3><p>{t('polish.draftPrivacy')}</p>
    <label><input type="checkbox" disabled={!settings || busy} checked={settings?.enabled || false}
      onChange={event => change(event.target.checked)} />{t('polish.enableRecovery')}</label>
    {error && <p role="alert">{error}<button onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
  </section>
}
