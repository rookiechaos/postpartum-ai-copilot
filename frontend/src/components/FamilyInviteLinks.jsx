import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import QRCode from 'qrcode'
import api from '../utils/api'
import { japanDateTime, utcDate } from '../utils/japanTime'
import { revealElement } from '../utils/focusView'

export default function FamilyInviteLinks({ familyId, visible, membershipRevision }) {
  const { t, i18n } = useTranslation()
  const [links, setLinks] = useState([])
  const [issued, setIssued] = useState(null)
  const [qr, setQr] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [attempt, setAttempt] = useState(0)
  const writing = useRef(false)
  useEffect(() => {
    if (!visible) return
    let active = true
    api.get(`/api/families/${familyId}/invite-links`).then(result => {
      if (active) {
        setLinks(result); setIssued(previous => previous && !result.some(link => link.id === previous.id) ? null : previous)
      }
    })
      .catch(() => { if (active) setError(t('pilot.loadFailed')) })
    const refresh = () => setAttempt(value => value + 1)
    window.addEventListener('focus', refresh)
    return () => { active = false; window.removeEventListener('focus', refresh) }
  }, [familyId, visible, attempt, membershipRevision])
  useEffect(() => {
    let active = true
    setQr('')
    if (issued) QRCode.toDataURL(issued.url, { width: 192, margin: 4 }).then(value => { if (active) setQr(value) })
      .catch(() => { if (active) setError(t('work.qrFailed')) })
    return () => { active = false }
  }, [issued])
  useEffect(() => {
    if (!issued) return
    const timer = setTimeout(() => {
      setIssued(previous => previous?.id === issued.id ? null : previous)
      setAttempt(value => value + 1)
    }, Math.max(0, utcDate(issued.expires_at).getTime() - Date.now()))
    return () => clearTimeout(timer)
  }, [issued?.id, issued?.expires_at])
  const issue = async () => {
    if (writing.current) return
    writing.current = true; setBusy(true); setError(''); setNotice(''); setIssued(null)
    try {
      const result = await api.post(`/api/families/${familyId}/invite-links`, {})
      setIssued({ ...result, url: `${window.location.origin}/family#invite=${result.token}` })
      setAttempt(value => value + 1)
    } catch { setError(t('flows.invitation.failed')) }
    finally { writing.current = false; setBusy(false) }
  }
  const revoke = async id => {
    if (writing.current) return
    writing.current = true; setBusy(true); setError('')
    try {
      await api.post(`/api/families/${familyId}/invite-links/${id}/revoke`, {})
      if (issued?.id === id) setIssued(null)
      setAttempt(value => value + 1); setNotice(t('flows.invitation.revoked'))
    } catch { setError(t('flows.invitation.failed')) }
    finally { writing.current = false; setBusy(false) }
  }
  return <section className="pilot-panel family-invite-links"><h3>{t('flows.invitation.title')}</h3><p>{t('flows.invitation.notice')}</p>
    <button type="button" className="pilot-button secondary" disabled={busy} onClick={issue}>{t('flows.invitation.create')}</button>
    {issued && <div><label>{t('flows.invitation.link')}<input readOnly value={issued.url} /></label>
      {qr && <img width={192} height={192} src={qr} alt={t('flows.invitation.qrAlt')} />}
      <button type="button" className="pilot-button secondary" disabled={busy} onClick={async () => {
        try { await navigator.clipboard.writeText(issued.url); setNotice(t('pilot.copied')) }
        catch { setError(t('pilot.copyFailed')) }
      }}>{t('pilot.copyLink')}</button>
    </div>}
    <ul>{links.map(link => <li key={link.id}>{t('flows.invitation.expires', { time: japanDateTime(link.expires_at, i18n.resolvedLanguage || 'ja') })}
      <button type="button" disabled={busy} onClick={() => revoke(link.id)}>{t('flows.invitation.revoke')}</button></li>)}</ul>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
  </section>
}

export function FamilyInviteReview({ token, onHandled }) {
  const { t, i18n } = useTranslation()
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const writing = useRef(false)
  const heading = useRef(null)
  useEffect(() => { revealElement(heading.current) }, [])
  useEffect(() => {
    let active = true
    setPreview(null); setError('')
    api.post('/api/family-invitations/preview', { token }).then(result => { if (active) setPreview(result) })
      .catch(() => { if (active) setError(t('flows.invitation.unavailable')) })
    return () => { active = false }
  }, [token, attempt])
  const accept = async () => {
    if (writing.current || !preview) return
    writing.current = true; setBusy(true); setError('')
    try { const result = await api.post('/api/family-invitations/accept', { token }); onHandled(result.family_id) }
    catch { setError(t('flows.invitation.failed')) }
    finally { writing.current = false; setBusy(false) }
  }
  return <main className="pilot-shell"><section className="pilot-panel"><h1 ref={heading} tabIndex={-1}>{t('flows.invitation.reviewTitle')}</h1>
    <p>{t('flows.invitation.confirmNotice')}</p>
    {preview && <><h2>{preview.name}</h2><p>{t('flows.invitation.expires', { time: japanDateTime(preview.expires_at, i18n.resolvedLanguage || 'ja') })}</p></>}
    {!preview && !error && <p role="status">{t('common.loading')}</p>}
    {error && <p role="alert">{error} <button type="button" disabled={busy} onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
    <div className="pilot-actions"><button type="button" className="pilot-button" disabled={busy || !preview} onClick={accept}>{t('flows.invitation.accept')}</button>
      <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => onHandled(null)}>{t('flows.invitation.cancel')}</button></div>
  </section></main>
}
