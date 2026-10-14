import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime } from '../utils/japanTime'
import FamilyInviteLinks from './FamilyInviteLinks'

const emptyScope = { share_baby: false, share_parent: false, share_notes: false, display_label: '' }

export default function FamilySharing({ userId, visible = true, refreshKey = 0, initialFamilyId = '', familyRequestKey = 0 }) {
  const { t, i18n } = useTranslation()
  const [families, setFamilies] = useState([])
  const [invitations, setInvitations] = useState([])
  const [selected, setSelected] = useState(initialFamilyId)
  const [members, setMembers] = useState([])
  const [records, setRecords] = useState([])
  const [scope, setScope] = useState(emptyScope)
  const [scopeConflict, setScopeConflict] = useState(false)
  const [name, setName] = useState('')
  const [inviteId, setInviteId] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const scopeEdited = useRef(false)
  const scopeRevision = useRef(null)
  const actionBusy = useRef(false)
  const family = families.find(item => item.family_id === selected)
  const me = members.find(item => item.user_id === userId)
  const canManage = family?.created_by === userId || me?.role === 'admin'

  useEffect(() => {
    if (!initialFamilyId || initialFamilyId === selected) return
    if (scopeEdited.current && !window.confirm(t('polish.discardSharingChanges'))) return
    scopeEdited.current = false; scopeRevision.current = null; setScopeConflict(false); setScope(emptyScope)
    setMembers([]); setRecords([]); setSelected(initialFamilyId)
  }, [initialFamilyId, familyRequestKey])

  useEffect(() => {
    if (!visible) return
    let active = true
    setLoading(true)
    Promise.all([api.get('/api/families/'), api.get('/api/families/invitations')]).then(([groups, pending]) => {
      if (!active) return
      setFamilies(groups); setInvitations(pending)
      if (!groups.some(group => group.family_id === selected)) {
        scopeEdited.current = false; scopeRevision.current = null; setScopeConflict(false); setScope(emptyScope)
        setSelected(groups[0]?.family_id || ''); setMembers([]); setRecords([])
      }
    }).catch(() => { if (active) { setError(t('pilot.loadFailed')); setMembers([]); setRecords([]) } })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [visible, attempt, selected])
  useEffect(() => {
    if (!selected || !visible) return
    let active = true
    Promise.all([api.get(`/api/families/${selected}/members`), api.get(`/api/families/${selected}/shared-data?days=7`)]).then(([people, shared]) => {
      if (!active) return
      setMembers(people.members); setRecords(shared.data)
      setError('')
      const ownMembership = people.members.find(item => item.user_id === userId)
      if (!scopeEdited.current && !scopeConflict) {
        const preferences = ownMembership?.permissions || {}
        scopeRevision.current = ownMembership?.revision ?? null
        setScopeConflict(false)
        setScope({ share_baby: preferences.share_baby === true, share_parent: preferences.share_parent === true,
          share_notes: preferences.share_notes === true, display_label: preferences.display_label || '' })
      } else if (ownMembership?.revision !== scopeRevision.current) setScopeConflict(true)
    }).catch(() => { if (active) { setMembers([]); setRecords([]); setError(t('polish.familyAccessChanged')) } })
    return () => { active = false }
  }, [selected, visible, attempt, refreshKey, userId, scopeConflict])
  useEffect(() => {
    if (!visible) return
    const refresh = () => setAttempt(value => value + 1)
    const timer = setInterval(refresh, 30000)
    window.addEventListener('focus', refresh)
    return () => { clearInterval(timer); window.removeEventListener('focus', refresh) }
  }, [visible])

  const run = async (action, sharing = false) => {
    if (actionBusy.current) return
    actionBusy.current = true; setBusy(true); setError('')
    try { await action(); setAttempt(value => value + 1) }
    catch (error) {
      if (sharing && error.status === 409) {
        setScopeConflict(true); setError(t('polish.sharingConflict')); setAttempt(value => value + 1)
      } else setError(t('polish.familyActionFailed'))
    }
    finally { actionBusy.current = false; setBusy(false) }
  }
  const editScope = (key, value) => {
    if (scopeConflict || actionBusy.current) return
    scopeEdited.current = true
    setScope(previous => {
      const next = { ...previous, [key]: value }
      if (!next.share_baby && !next.share_parent) next.share_notes = false
      return next
    })
  }
  const memberLabel = member => member.permissions?.display_label || (members.includes(member)
    ? t('polish.memberNumber', { number: members.indexOf(member) + 1 }) : t('polish.formerRecorder'))

  return <div className="family-sharing pilot-panel"><h2>{t('polish.familyHandoff')}</h2><p>{t('polish.familySharingNotice')}</p>
    <details><summary>{t('flows.invitation.manual')}</summary>
    <label>{t('polish.yourInviteId')}<input readOnly value={userId} /></label><p>{t('polish.inviteIdNotice')}</p>
    <button type="button" className="pilot-button secondary" onClick={async () => {
      try { await navigator.clipboard.writeText(userId); setCopied(true) }
      catch { setError(t('pilot.copyFailed')) }
    }}>{t(copied ? 'pilot.copied' : 'polish.copyAccountId')}</button></details>
    {error && <p role="alert">{error}<button type="button" onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
    {loading && <p role="status">{t('common.loading')}</p>}
    {invitations.map(invitation => <section key={invitation.family_id} className="pilot-panel"><h3>{t('polish.invitationFrom', { name: invitation.name })}</h3>
      <p>{t('polish.invitationNotice')}</p>
      <button className="pilot-button secondary" disabled={busy} onClick={() => run(() => api.post(`/api/families/${invitation.family_id}/accept`, {}))}>{t('polish.acceptInvitation')}</button>
      <button className="pilot-button secondary" disabled={busy} onClick={() => run(() => api.post(`/api/families/${invitation.family_id}/decline`, {}))}>{t('polish.declineInvitation')}</button>
    </section>)}
    {families.length > 0 && <label>{t('polish.chooseFamily')}<select value={selected} disabled={busy} onChange={event => {
      if (scopeEdited.current && !window.confirm(t('polish.discardSharingChanges'))) return
      scopeEdited.current = false; scopeRevision.current = null; setScopeConflict(false)
      setMembers([]); setRecords([]); setScope(emptyScope); setSelected(event.target.value)
    }}>{families.map(group => <option key={group.family_id} value={group.family_id}>{group.name}</option>)}</select></label>}
    {family && me && <>
      <form onSubmit={event => { event.preventDefault(); if (scopeConflict) return; run(async () => {
        const result = await api.post(`/api/families/${selected}/sharing`, { ...scope, revision: scopeRevision.current })
        scopeRevision.current = result.revision; scopeEdited.current = false; setScopeConflict(false)
      }, true) }}><fieldset disabled={busy || scopeConflict}><legend>{t('polish.mySharing')}</legend>
        <label>{t('polish.recorderLabel')}<input value={scope.display_label} maxLength={40} onChange={event => editScope('display_label', event.target.value)} /></label>
        {['share_baby', 'share_parent', 'share_notes'].map(key => <label key={key}><input type="checkbox" checked={scope[key]}
          disabled={key === 'share_notes' && !scope.share_baby && !scope.share_parent} onChange={event => editScope(key, event.target.checked)} />{t(`polish.sharingScopes.${key}`)}</label>)}
        <p>{t('polish.sharingScopeNotice')}</p>{scopeEdited.current && <p role="status">{t('polish.sharingNotSaved')}</p>}
        <button className="pilot-button secondary" type="submit" disabled={!Number.isInteger(scopeRevision.current)}>{t('work.saveChanges')}</button>
      </fieldset></form>
      {scopeConflict && <section className="pilot-panel" role="alert"><p>{t('polish.sharingConflict')}</p>
        <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => {
          if (scopeEdited.current && !window.confirm(t('polish.reloadSharingConfirm'))) return
          scopeEdited.current = false; scopeRevision.current = null; setScopeConflict(false); setScope(emptyScope)
          setMembers([]); setRecords([]); setAttempt(value => value + 1)
        }}>{t('polish.reloadSharing')}</button>
      </section>}
      <section><h3>{t('polish.familyMembers')}</h3><ul>{members.map(member => <li key={member.id}>
        {memberLabel(member)} {member.user_id === userId ? `(${t('polish.you')})` : ''} · {t(`polish.memberStatus.${member.status}`)}
        {canManage && member.user_id !== family.created_by && (family.created_by === userId || !['owner', 'admin'].includes(member.role))
          && <button type="button" disabled={busy} onClick={() => {
          if (window.confirm(t('polish.revokeConfirm'))) run(() => api.delete(`/api/families/${selected}/members/${encodeURIComponent(member.user_id)}`))
        }}>{t('polish.revokeMember')}</button>}
      </li>)}</ul></section>
      {canManage && <FamilyInviteLinks key={selected} familyId={selected} visible={visible} membershipRevision={me.revision} />}
      {canManage && <details><summary>{t('flows.invitation.manual')}</summary><form onSubmit={event => { event.preventDefault(); run(async () => {
        await api.post(`/api/families/${selected}/invite`, { invitee_user_id: inviteId.trim(), role: 'member' }); setInviteId('')
      }) }}><label>{t('polish.inviteeId')}<input required maxLength={100} disabled={busy} value={inviteId} onChange={event => setInviteId(event.target.value)} /></label>
        <button className="pilot-button secondary" disabled={busy}>{t('polish.inviteMember')}</button></form></details>}
      {family.created_by !== userId && <button className="pilot-button secondary" disabled={busy} onClick={() => {
        if (window.confirm(t('polish.leaveFamilyConfirm'))) run(() => api.post(`/api/families/${selected}/leave`, {}))
      }}>{t('polish.leaveFamily')}</button>}
      <section><h3>{t('polish.sharedRecentRecords')}</h3><p>{t('polish.familyRecordedByNotice')}</p>
        {records.length === 0 ? <p>{t('polish.noSharedRecords')}</p> : <ol className="recent-records">{records.map(record => <li key={record.record_key}>
          <strong>{t(`tracking.${record.entry_type}`)}</strong><time>{japanDateTime(record.timestamp, i18n.resolvedLanguage || 'ja')}</time>
          <span>{t('polish.recordedBy', { name: record.recorder_label || memberLabel(members.find(member => member.user_id === record.recorded_by) || { permissions: {} }) })}</span>
          {record.diaper_type && <span>{t(`tracking.${record.diaper_type}`)}</span>}{record.feeding_type && <span>{t(`tracking.${record.feeding_type}`)}</span>}
          {['duration_minutes', 'sleep_duration_minutes'].map(key => record[key] != null && <span key={key}>{record[key]} {t('pilot.minutes')}</span>)}
          {['amount_ml', 'pumped_amount_ml'].map(key => record[key] != null && <span key={key}>{record[key]} mL</span>)}
          {record.mood_level && <span>{t(`tracking.${record.mood_level}`)}</span>}{record.weight_kg != null && <span>{record.weight_kg} kg</span>}
          {record.breast_condition && <span>{t(`tracking.${record.breast_condition}`)}</span>}{record.sleep_quality && <span>{t(`tracking.${record.sleep_quality}`)}</span>}
          {['notes', 'mood_notes', 'recovery_notes'].map(key => record[key] && <p key={key}>{record[key]}</p>)}
        </li>)}</ol>}
      </section>
    </>}
    <form onSubmit={event => { event.preventDefault(); run(async () => {
      const created = await api.post('/api/families/', { name })
      scopeEdited.current = false; scopeRevision.current = null; setScopeConflict(false); setScope(emptyScope)
      setSelected(created.family_id); setName('')
    }) }}><fieldset disabled={busy}><legend>{t('polish.createFamily')}</legend>
      <label>{t('polish.familyName')}<input value={name} required maxLength={100} onChange={event => setName(event.target.value)} /></label>
      <button className="pilot-button secondary">{t('polish.createFamily')}</button>
    </fieldset></form>
  </div>
}
