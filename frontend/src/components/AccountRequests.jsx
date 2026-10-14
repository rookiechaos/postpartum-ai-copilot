import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime } from '../utils/japanTime'

const mergeRequests = (previous, incoming) => {
  const rows = new Map(previous.map(item => [item.reference, item]))
  incoming.forEach(item => {
    const current = rows.get(item.reference)
    if (!current || item.updated_at >= current.updated_at) rows.set(item.reference, item)
  })
  return [...rows.values()].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
}

export default function AccountRequests({ publicAccess = false }) {
  const { t, i18n } = useTranslation()
  const [kind, setKind] = useState('privacy')
  const [email, setEmail] = useState('')
  const [reference, setReference] = useState('')
  const [requests, setRequests] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [received, setReceived] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (publicAccess) return
    let active = true
    api.getAccountRequests().then(data => {
      if (active) setRequests(previous => mergeRequests(previous, data))
    })
      .catch(() => { if (active) setError(t('pilot.loadFailed')) })
    return () => { active = false }
  }, [publicAccess, attempt])

  const submit = async event => {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError(''); setReceived(false)
    try {
      const language = i18n.resolvedLanguage || 'ja'
      const result = publicAccess ? await api.requestAccountAccess(email, language) : await api.createAccountRequest(kind, language)
      setReference(result.reference); setReceived(true)
      setRequests(previous => mergeRequests(previous, [result]))
      if (publicAccess) setEmail('')
    } catch { setError(t('work.requestFailed')) }
    finally { setBusy(false) }
  }
  const lookup = async event => {
    event.preventDefault()
    if (busy || !reference.trim()) return
    setBusy(true); setError(''); setReceived(false)
    try {
      const result = await api.getAccountRequestStatus(reference.trim())
      setRequests(previous => mergeRequests(previous, [result]))
    } catch { setError(t('work.lookupFailed')) }
    finally { setBusy(false) }
  }

  return <section className="pilot-panel account-requests">
    <h3>{t(publicAccess ? 'work.accessHelp' : 'work.accountRequests')}</h3>
    <p>{t('work.manualRequestNotice')}</p>
    <form onSubmit={submit}>
      {publicAccess ? <label>{t('auth.email')}<input type="email" required maxLength={255} autoComplete="email"
        value={email} disabled={busy} onChange={event => setEmail(event.target.value)} /></label>
        : <label>{t('work.requestKind')}<select value={kind} disabled={busy} onChange={event => setKind(event.target.value)}>
          {['privacy', 'deletion', 'access'].map(value => <option key={value} value={value}>{t(`work.requestKinds.${value}`)}</option>)}
        </select></label>}
      <button className="pilot-button secondary" disabled={busy}>{t(busy ? 'common.loading' : 'work.submitRequest')}</button>
    </form>
    {received && <p role="status">{t('work.requestReceived')}</p>}
    {error && <p role="alert">{error}</p>}
    <p>{t('work.keepReference')}</p>
    <form onSubmit={lookup}>
      <label>{t('work.reference')}<input value={reference} required maxLength={36} autoComplete="off" spellCheck={false}
        disabled={busy} onChange={event => setReference(event.target.value)} /></label>
      <button className="pilot-button secondary" disabled={busy || !reference.trim()}>{t('work.checkProgress')}</button>
    </form>
    {!publicAccess && <button className="pilot-button secondary" disabled={busy} onClick={() => { setError(''); setAttempt(value => value + 1) }}>{t('pilot.retry')}</button>}
    <div aria-live="polite">{requests.map(item => <article key={item.reference} className="support-card">
      <h4>{t(`work.requestKinds.${item.kind}`)} · {t(`work.requestStatuses.${item.status}`)}</h4>
      <p>{t('work.reference')}: <code>{item.reference}</code></p>
      <p>{japanDateTime(item.updated_at, i18n.language)}</p>
      {item.public_response && <p className="request-response">{item.public_response}</p>}
      <p>{t('flows.account.nextAction')}: {item.next_action || t(['completed', 'declined'].includes(item.status) ? 'flows.account.finalNextAction' : 'flows.account.pendingNextAction')}</p>
      {!['completed', 'declined'].includes(item.status) && <p>{t('flows.account.expectedReply')}: {item.expected_reply_at ? japanDateTime(item.expected_reply_at, i18n.resolvedLanguage || 'ja') : t('flows.account.noReplyTime')}</p>}
      {item.receipt && <section className="account-receipt"><h5>{t('flows.account.receipt')}</h5>
        <p>{t('flows.account.receiptMethod')}</p><p><code>{item.receipt.id}</code></p><time>{japanDateTime(item.receipt.completed_at, i18n.resolvedLanguage || 'ja')}</time>
        <p className="preserve-lines">{item.receipt.outcome}</p>
        {item.receipt.retained_data_notice && <><h6>{t('flows.account.retained')}</h6><p className="preserve-lines">{item.receipt.retained_data_notice}</p></>}
      </section>}
    </article>)}</div>
  </section>
}
