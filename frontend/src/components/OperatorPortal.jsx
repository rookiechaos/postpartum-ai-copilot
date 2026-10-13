import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import LanguageSelector from './LanguageSelector'
import ProductAnalytics from './ProductAnalytics'
import { japanDateTime } from '../utils/japanTime'

export default function OperatorPortal({ onExit }) {
  const { t, i18n } = useTranslation()
  const [requests, setRequests] = useState([])
  const [authorized, setAuthorized] = useState(false)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('received')
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const [drafts, setDrafts] = useState({})
  const [offset, setOffset] = useState(0)
  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    api.get(`/api/admin/account-requests?status=${status}&limit=50&offset=${offset}`).then(data => {
      if (active) { setRequests(data); setAuthorized(true) }
    }).catch(err => {
      if (active) { setAuthorized(false); setRequests([]); setError(t(err.status === 403 ? 'work.operatorDenied' : 'pilot.loadFailed')) }
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [status, attempt, offset])
  const save = async (event, item) => {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError('')
    const draft = drafts[item.reference] || { status: item.status, public_response: item.public_response }
    try {
      await api.post(`/api/admin/account-requests/${item.reference}`, draft)
      setDrafts(previous => { const next = { ...previous }; delete next[item.reference]; return next })
      setAttempt(value => value + 1)
    } catch { setError(t('pilot.saveFailed')) }
    finally { setBusy(false) }
  }
  return <main className="pilot-shell operator-portal">
    <div className="pilot-topbar"><h1>{t('work.operatorTitle')}</h1><LanguageSelector /></div>
    <p>{t('work.operatorScope')}</p>
    <div className="pilot-actions"><button className="pilot-button secondary" onClick={onExit}>{t('pilot.switchEntrance')}</button>
      <button className="pilot-button secondary" onClick={() => api.logout()}>{t('settings.logout')}</button></div>
    {loading && <p role="status">{t('common.loading')}</p>}
    {error && <p role="alert">{error}</p>}
    <button className="pilot-button secondary" disabled={busy || loading} onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button>
    {authorized && <>
      <section className="pilot-panel"><h2>{t('work.accountRequests')}</h2><p>{t('work.operatorVerification')}</p>
        <label>{t('work.requestStatus')}<select value={status} disabled={busy || loading} onChange={event => { setOffset(0); setStatus(event.target.value) }}>
          {['received', 'verifying', 'completed', 'declined'].map(value => <option key={value} value={value}>{t(`work.requestStatuses.${value}`)}</option>)}
        </select></label>
        {!loading && requests.length === 0 && <p>{t('work.noRequests')}</p>}
        {requests.map(item => {
          const draft = drafts[item.reference] || { status: item.status, public_response: item.public_response }
          const update = (key, value) => setDrafts(previous => ({ ...previous, [item.reference]: { ...draft, [key]: value } }))
          return <form key={item.reference} className="support-card" onSubmit={event => save(event, item)}>
            <h3>{t(`work.requestKinds.${item.kind}`)}</h3><p>{item.contact_email} · {item.language}</p>
            <p>{t('work.identity')}: {t(item.user_id ? 'work.signedInRequest' : 'work.unverifiedRequest')}</p>
            {item.updated_by && <p>{t('work.lastHandler')}: <code>{item.updated_by}</code></p>}
            <p>{t('work.reference')}: <code>{item.reference}</code></p><p>{japanDateTime(item.created_at, i18n.language)}</p>
            <fieldset disabled={busy || loading}><legend>{t('work.operatorAction')}</legend>
              <label>{t('work.requestStatus')}<select value={draft.status} onChange={event => update('status', event.target.value)}>
                {['received', 'verifying', 'completed', 'declined'].map(value => <option key={value} value={value}>{t(`work.requestStatuses.${value}`)}</option>)}
              </select></label>
              <label>{t('work.publicResponse')}<textarea rows={3} maxLength={1500} value={draft.public_response}
                required={['completed', 'declined'].includes(draft.status)} onChange={event => update('public_response', event.target.value)} /></label>
              <p>{t('work.responsePrivacy')}</p><button className="pilot-button">{t('work.saveChanges')}</button>
            </fieldset>
          </form>
        })}
        <div className="pilot-actions"><button className="pilot-button secondary" disabled={loading || busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 50))}>{t('work.previousPage')}</button>
          <button className="pilot-button secondary" disabled={loading || busy || requests.length < 50} onClick={() => setOffset(value => value + 50)}>{t('work.nextPage')}</button></div>
      </section>
      <details className="pilot-panel"><summary>{t('work.operatorAnalytics')}</summary><ProductAnalytics /></details>
    </>}
  </main>
}
