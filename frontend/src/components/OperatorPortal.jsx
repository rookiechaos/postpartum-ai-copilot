import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import LanguageSelector from './LanguageSelector'
import ProductAnalytics from './ProductAnalytics'
import { japanDateTime, japanDateTimeInput } from '../utils/japanTime'
import ConnectionNotice from './ConnectionNotice'
import OperatorActions from './OperatorActions'
import { revealElement } from '../utils/focusView'

const workflowDraft = item => ({ status: item.status, public_response: item.public_response,
  revision: item.revision || 0, identity_verified: item.workflow?.identity_verified === true,
  verification_reference: item.workflow?.verification_reference || '', execution_reference: item.workflow?.execution_reference || '',
  steps: item.workflow?.steps || [], next_action: item.next_action || '',
  expected_reply_at: item.expected_reply_at ? japanDateTimeInput(item.expected_reply_at) : '',
  outcome: item.workflow?.outcome || '', retained_data_notice: item.workflow?.retained_data_notice || '' })

export default function OperatorPortal({ onExit, onOrganization, registerLeaveGuard }) {
  const { t, i18n } = useTranslation()
  const [requests, setRequests] = useState([])
  const [authorized, setAuthorized] = useState(false)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('received')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const [drafts, setDrafts] = useState({})
  const [offset, setOffset] = useState(0)
  const writing = useRef(false)
  const dirty = Object.keys(drafts).length > 0
  useEffect(() => {
    if (!dirty && !busy) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty, busy])
  const canLeave = useCallback(() => {
    if (writing.current) { setError(t('work.saveInProgress')); return false }
    return !dirty || window.confirm(t('flows.account.discardConfirm'))
  }, [dirty, t])
  useLayoutEffect(() => registerLeaveGuard?.(canLeave), [registerLeaveGuard, canLeave])
  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    const query = new URLSearchParams({ limit: 50, offset, ...(status ? { status } : {}), ...(overdueOnly ? { overdue_only: true } : {}) })
    api.get(`/api/admin/account-requests?${query}`).then(data => {
      if (active) { setRequests(data); setAuthorized(true) }
    }).catch(err => {
      if (active) { setAuthorized(false); setRequests([]); setError(t(err.status === 403 ? 'work.operatorDenied' : 'pilot.loadFailed')) }
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [status, overdueOnly, attempt, offset])
  const save = async (event, item) => {
    event.preventDefault()
    if (writing.current) return
    const draft = drafts[item.reference] || workflowDraft(item)
    const done = draft.status === 'completed'
    if (done && (!(item.required_steps || []).every(step => draft.steps.includes(step)) || !draft.outcome.trim()
      || !draft.execution_reference.trim() || (item.kind !== 'privacy' && (!draft.identity_verified || !draft.verification_reference.trim()))
      || (item.kind === 'deletion' && !draft.retained_data_notice.trim()))) {
      setError(t('flows.account.incomplete')); return
    }
    const deadline = draft.expected_reply_at ? new Date(`${draft.expected_reply_at}:00+09:00`) : null
    if (deadline && !Number.isFinite(deadline.getTime())) { setError(t('work.invalidTime')); return }
    writing.current = true; setBusy(true); setError('')
    try {
      await api.post(`/api/admin/account-requests/${item.reference}`, { ...draft, expected_reply_at: deadline?.toISOString() || null })
      setDrafts(previous => { const next = { ...previous }; delete next[item.reference]; return next })
      setAttempt(value => value + 1)
    } catch (failure) { setError(t(failure.status === 409 ? 'flows.account.conflict' : failure.status === 422 ? 'flows.account.incomplete' : 'pilot.saveFailed')) }
    finally { writing.current = false; setBusy(false) }
  }
  return <main className="pilot-shell operator-portal">
    <div className="pilot-topbar"><h1>{t('work.operatorTitle')}</h1><LanguageSelector /></div>
    <p>{t('work.operatorScope')}</p>
    <ConnectionNotice />
    <div className="pilot-actions"><button className="pilot-button secondary" disabled={busy} onClick={() => { if (registerLeaveGuard || canLeave()) onExit() }}>{t('pilot.switchEntrance')}</button>
      <button className="pilot-button secondary" disabled={busy} onClick={() => { if (canLeave()) api.logout() }}>{t('settings.logout')}</button></div>
    {loading && <p role="status">{t('common.loading')}</p>}
    {error && <p role="alert">{error}</p>}
    <button className="pilot-button secondary" disabled={busy || loading} onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button>
    {authorized && <>
      <OperatorActions refreshKey={attempt} blocked={busy || loading} onRequests={value => {
        setOverdueOnly(value === 'overdue'); setStatus(value === 'overdue' ? '' : value); setOffset(0)
        revealElement(document.getElementById('operator-request-heading'))
      }} onOrganization={onOrganization ? () => { if (registerLeaveGuard || canLeave()) onOrganization() } : undefined} />
      <section className="pilot-panel"><h2 id="operator-request-heading" tabIndex={-1}>{t('work.accountRequests')}</h2><p>{t('work.operatorVerification')}</p>
        <label>{t('work.requestStatus')}<select value={status} disabled={busy || loading} onChange={event => { setOffset(0); setOverdueOnly(false); setStatus(event.target.value) }}>
          <option value="">{t('workflow.operator.allRequests')}</option>
          {['received', 'verifying', 'completed', 'declined'].map(value => <option key={value} value={value}>{t(`work.requestStatuses.${value}`)}</option>)}
        </select></label>
        {overdueOnly && <p>{t('workflow.operator.overdueFilter')} <button type="button" className="text-action" disabled={busy || loading} onClick={() => { setOverdueOnly(false); setOffset(0) }}>{t('workflow.operator.clearFilter')}</button></p>}
        {!loading && requests.length === 0 && <p>{t('work.noRequests')}</p>}
        {requests.map(item => {
          const draft = drafts[item.reference] || workflowDraft(item)
          const finalized = ['completed', 'declined'].includes(item.status)
          const update = (key, value) => setDrafts(previous => ({ ...previous, [item.reference]: { ...draft, [key]: value } }))
          return <form key={item.reference} className="support-card" onSubmit={event => save(event, item)}>
            <h3>{t(`work.requestKinds.${item.kind}`)}</h3><p>{item.contact_email} · {item.language}</p>
            <p>{t('work.identity')}: {t(item.user_id ? 'work.signedInRequest' : 'work.unverifiedRequest')}</p>
            {item.updated_by && <p>{t('work.lastHandler')}: <code>{item.updated_by}</code></p>}
            <p>{t('work.reference')}: <code>{item.reference}</code></p><p>{japanDateTime(item.created_at, i18n.language)}</p>
            <p>{t('flows.account.manualNotice')}</p>
            <fieldset disabled={busy || loading || finalized}><legend>{t('work.operatorAction')}</legend>
              <label>{t('work.requestStatus')}<select value={draft.status} onChange={event => update('status', event.target.value)}>
                {['received', 'verifying', 'completed', 'declined'].map(value => <option key={value} value={value}>{t(`work.requestStatuses.${value}`)}</option>)}
              </select></label>
              {item.kind !== 'privacy' && <>
                <label><input type="checkbox" checked={draft.identity_verified} onChange={event => {
                  const checked = event.target.checked
                  setDrafts(previous => ({ ...previous, [item.reference]: { ...draft, identity_verified: checked,
                    steps: checked ? [...new Set([...draft.steps, 'identity_checked'])] : draft.steps.filter(step => step !== 'identity_checked') } }))
                }} />{t('flows.account.verified')}</label>
                <label>{t('flows.account.verificationReference')}<input maxLength={200} value={draft.verification_reference}
                  required={draft.identity_verified} onChange={event => update('verification_reference', event.target.value)} /></label>
              </>}
              <p>{t('flows.account.privateReferenceNotice')}</p>
              <fieldset><legend>{t('flows.account.stepsTitle')}</legend>
                {(item.required_steps || []).filter(step => step !== 'identity_checked').map(step => <label key={step}>
                  <input type="checkbox" checked={draft.steps.includes(step)} onChange={event => update('steps', event.target.checked
                    ? [...new Set([...draft.steps, step])] : draft.steps.filter(value => value !== step))} />{t(`flows.account.steps.${step}`)}
                </label>)}
              </fieldset>
              <label>{t('flows.account.executionReference')}<input maxLength={200} value={draft.execution_reference}
                required={draft.status === 'completed'} onChange={event => update('execution_reference', event.target.value)} /></label>
              <label>{t('flows.account.nextAction')}<textarea rows={2} maxLength={500} value={draft.next_action}
                required={['received', 'verifying'].includes(draft.status)} onChange={event => update('next_action', event.target.value)} /></label>
              <label>{t('flows.account.expectedReply')}<input type="datetime-local" value={draft.expected_reply_at}
                required={['received', 'verifying'].includes(draft.status)} onChange={event => update('expected_reply_at', event.target.value)} /></label>
              <label>{t('flows.account.outcome')}<textarea rows={3} maxLength={1000} value={draft.outcome}
                required={draft.status === 'completed'} onChange={event => update('outcome', event.target.value)} /></label>
              {item.kind === 'deletion' && <label>{t('flows.account.retained')}<textarea rows={3} maxLength={1000} value={draft.retained_data_notice}
                required={draft.status === 'completed'} onChange={event => update('retained_data_notice', event.target.value)} /></label>}
              <label>{t('work.publicResponse')}<textarea rows={3} maxLength={1500} value={draft.public_response}
                required={['completed', 'declined'].includes(draft.status)} onChange={event => update('public_response', event.target.value)} /></label>
              <p>{t('work.responsePrivacy')}</p><button type="submit" className="pilot-button">{t('work.saveChanges')}</button>
            </fieldset>
            {item.receipt && <section><h4>{t('flows.account.receipt')}</h4><p>{item.receipt.id}</p><p className="preserve-lines">{item.receipt.outcome}</p></section>}
            {drafts[item.reference] && <button type="button" className="pilot-button secondary" disabled={busy || loading} onClick={() => {
              if (!window.confirm(t('flows.account.discardConfirm'))) return
              setDrafts(previous => { const next = { ...previous }; delete next[item.reference]; return next }); setAttempt(value => value + 1)
            }}>{t('flows.account.reload')}</button>}
            {item.events?.length > 0 && <details><summary>{t('flows.account.history')}</summary><ol>{item.events.map((event, index) => <li key={index}>
              {japanDateTime(event.at, i18n.resolvedLanguage || 'ja')} · {t(`work.requestStatuses.${event.status}`)}
            </li>)}</ol></details>}
          </form>
        })}
        <div className="pilot-actions"><button className="pilot-button secondary" disabled={loading || busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 50))}>{t('work.previousPage')}</button>
          <button className="pilot-button secondary" disabled={loading || busy || requests.length < 50} onClick={() => setOffset(value => value + 50)}>{t('work.nextPage')}</button></div>
      </section>
      <details className="pilot-panel"><summary>{t('work.operatorAnalytics')}</summary><ProductAnalytics /></details>
    </>}
  </main>
}
