import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime } from '../utils/japanTime'
import FamilyInviteLinks from './FamilyInviteLinks'
import { subjectsChanged, useCareWork } from '../utils/CareSession'
import { CareRecordIdentity } from './CareSubject'
import { revealElement } from '../utils/focusView'
import { Button, StatusMessage } from './ui'
import './FamilySharingFlow.css'

const emptyScope = { share_baby: false, share_parent: false, share_notes: false, display_label: '' }
const scopeValues = permissions => ({ share_baby: permissions?.share_baby === true,
  share_parent: permissions?.share_parent === true, share_notes: permissions?.share_notes === true,
  display_label: typeof permissions?.display_label === 'string' ? permissions.display_label : '' })
const sameScope = (left, right) => Object.keys(emptyScope).every(key => left?.[key] === right?.[key])

export default function FamilySharing({ userId, visible = true, refreshKey = 0, initialFamilyId = '', familyRequestKey = 0, navigationRequest }) {
  const { t, i18n } = useTranslation()
  const [families, setFamilies] = useState([])
  const [invitations, setInvitations] = useState([])
  const [selected, setSelected] = useState(initialFamilyId)
  const [members, setMembers] = useState([])
  const [records, setRecords] = useState([])
  const [scope, setScope] = useState(emptyScope)
  const [scopeBaseline, setScopeBaseline] = useState(null)
  const [scopeStatus, setScopeStatus] = useState('idle')
  const [pendingScope, setPendingScope] = useState(null)
  const [checkedScope, setCheckedScope] = useState(null)
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
  const scopeHeading = useRef(null)
  const handledNavigation = useRef(0)
  const identity = useRef({ userId, selected })
  identity.current = { userId, selected }
  const lifecycle = useRef(0)
  const pendingScopeRef = useRef(pendingScope)
  pendingScopeRef.current = pendingScope
  const scopeConflictRef = useRef(scopeConflict)
  scopeConflictRef.current = scopeConflict
  const scopeDirty = Boolean(scopeBaseline && scopeBaseline.familyId === selected && !sameScope(scopeBaseline.values, scope))
  scopeEdited.current = scopeDirty
  const family = families.find(item => item.family_id === selected)
  const me = members.find(item => item.user_id === userId)
  const canManage = family?.created_by === userId || me?.role === 'admin'
  const controlsBlocked = busy || Boolean(pendingScope)
  const scopeWork = pendingScope || scopeDirty || scopeConflict
  useCareWork('family-sharing', scopeWork ? {
    version: `${scopeStatus}:${Boolean(pendingScope)}:${scopeConflict}`,
    title: scopeStatus === 'saving' ? 'familyFlow.workSaving' : pendingScope ? 'familyFlow.workPending'
      : scopeConflict ? 'familyFlow.workConflict' : 'familyFlow.workDraft',
    priority: busy || pendingScope ? 0 : 2, critical: busy || Boolean(pendingScope), attention: scopeConflict, protectLeave: true,
    tab: 'family', detail: { action: 'sharing' }, action: 'experience.trackedWorkOpen'
  } : null)
  useEffect(() => {
    lifecycle.current += 1
    return () => { lifecycle.current += 1 }
  }, [userId])
  useEffect(() => {
    if (!visible || navigationRequest?.action !== 'sharing' || !navigationRequest.key
      || handledNavigation.current === navigationRequest.key) return
    if (revealElement(scopeHeading.current)) handledNavigation.current = navigationRequest.key
  }, [visible, navigationRequest?.key, navigationRequest?.action, selected, scopeWork])
  const currentSession = operation => lifecycle.current === operation.lifecycle && identity.current.userId === operation.userId
  const currentOperation = operation => currentSession(operation) && identity.current.selected === operation.familyId
  const resetScope = () => {
    scopeEdited.current = false; scopeRevision.current = null; setScopeConflict(false); setScope(emptyScope)
    pendingScopeRef.current = null
    setScopeBaseline(null); setScopeStatus('idle'); setPendingScope(null); setCheckedScope(null)
  }

  useEffect(() => {
    if (!initialFamilyId || initialFamilyId === selected) return
    if (actionBusy.current || pendingScopeRef.current) return
    if ((scopeEdited.current || scopeConflictRef.current) && !window.confirm(t('polish.discardSharingChanges'))) return
    resetScope()
    setMembers([]); setRecords([]); setSelected(initialFamilyId)
  }, [initialFamilyId, familyRequestKey])

  useEffect(() => {
    if (!visible) return
    let active = true
    const operation = { familyId: selected, userId, lifecycle: lifecycle.current }
    setLoading(true)
    Promise.all([api.get('/api/families/'), api.get('/api/families/invitations')]).then(([groups, pending]) => {
      if (!active || !currentOperation(operation)) return
      setFamilies(groups); setInvitations(pending)
      if (!groups.some(group => group.family_id === selected)) {
        if (actionBusy.current || pendingScopeRef.current) { setMembers([]); setRecords([]); setScopeConflict(true); return }
        resetScope()
        setSelected(groups[0]?.family_id || ''); setMembers([]); setRecords([])
      }
    }).catch(() => { if (active && currentOperation(operation)) { setError(t('pilot.loadFailed')); setMembers([]); setRecords([]) } })
      .finally(() => { if (active && currentOperation(operation)) setLoading(false) })
    return () => { active = false }
  }, [visible, attempt, selected, userId])
  useEffect(() => {
    if (!selected || !visible || pendingScope || actionBusy.current) return
    let active = true
    const operation = { familyId: selected, userId, lifecycle: lifecycle.current }
    Promise.all([api.get(`/api/families/${selected}/members`), api.get(`/api/families/${selected}/shared-data?days=7`)]).then(([people, shared]) => {
      if (!active || !currentOperation(operation) || pendingScopeRef.current || actionBusy.current) return
      setMembers(people.members); setRecords(shared.data)
      setError('')
      const ownMembership = people.members.find(item => item.user_id === userId)
      if (!scopeEdited.current && !scopeConflictRef.current) {
        const preferences = scopeValues(ownMembership?.permissions)
        scopeRevision.current = ownMembership?.revision ?? null
        setScopeConflict(false)
        setScope(preferences); setScopeBaseline({ familyId: selected, values: preferences })
      } else if (ownMembership?.revision !== scopeRevision.current) setScopeConflict(true)
    }).catch(() => { if (active && currentOperation(operation) && !pendingScopeRef.current && !actionBusy.current) {
      setMembers([]); setRecords([]); setError(t('polish.familyAccessChanged'))
    } })
    return () => { active = false }
  }, [selected, visible, attempt, refreshKey, userId, scopeConflict, pendingScope])
  useEffect(() => {
    if (!visible) return
    const refresh = () => setAttempt(value => value + 1)
    const timer = setInterval(refresh, 30000)
    window.addEventListener('focus', refresh)
    return () => { clearInterval(timer); window.removeEventListener('focus', refresh) }
  }, [visible])

  const run = async action => {
    if (actionBusy.current || pendingScopeRef.current) return
    const operation = { familyId: selected, userId, lifecycle: lifecycle.current }
    actionBusy.current = true; setBusy(true); setError('')
    try { await action(() => currentSession(operation)); if (currentSession(operation)) {
      setAttempt(value => value + 1); window.dispatchEvent(new Event(subjectsChanged))
    } }
    catch {
      if (currentSession(operation)) setError(t('polish.familyActionFailed'))
    }
    finally { if (currentSession(operation)) { actionBusy.current = false; setBusy(false) } }
  }
  const editScope = (key, value) => {
    if (scopeConflict || actionBusy.current || pendingScopeRef.current) return
    scopeEdited.current = true
    setScope(previous => {
      const next = { ...previous, [key]: value }
      if (!next.share_baby && !next.share_parent) next.share_notes = false
      return next
    })
    setScopeStatus('idle')
  }
  const saveScope = async event => {
    event.preventDefault()
    if (actionBusy.current || pendingScopeRef.current || !scopeDirty || scopeConflict || !me
      || !Number.isInteger(scopeRevision.current)) return
    const operation = { familyId: selected, userId, lifecycle: lifecycle.current,
      revision: scopeRevision.current, values: { ...scope } }
    pendingScopeRef.current = operation
    setPendingScope(operation); setCheckedScope(null); setScopeStatus('saving')
    actionBusy.current = true; setBusy(true); setError('')
    try {
      const result = await api.post(`/api/families/${operation.familyId}/sharing`, { ...operation.values, revision: operation.revision })
      if (!currentOperation(operation)) return
      if (!Number.isInteger(result?.revision) || result.revision !== operation.revision + 1) {
        const failure = new Error('Sharing result unavailable'); failure.resultUnconfirmed = true; throw failure
      }
      scopeRevision.current = result.revision; scopeEdited.current = false
      setScopeBaseline({ familyId: operation.familyId, values: operation.values }); setScope(operation.values)
      pendingScopeRef.current = null; setPendingScope(null); setScopeConflict(false); setScopeStatus('saved')
      setAttempt(value => value + 1); window.dispatchEvent(new Event(subjectsChanged))
    } catch (failure) {
      if (!currentOperation(operation)) return
      if (failure.resultUnconfirmed) setScopeStatus('unconfirmed')
      else {
        pendingScopeRef.current = null; setPendingScope(null)
        setScopeStatus(failure.status === 409 ? 'conflict' : 'failed')
        if (failure.status === 409) { setScopeConflict(true); setAttempt(value => value + 1) }
      }
    } finally { if (currentSession(operation)) { actionBusy.current = false; setBusy(false) } }
  }
  const checkScope = async () => {
    const operation = pendingScopeRef.current
    if (!operation || actionBusy.current || !currentOperation(operation)) return
    actionBusy.current = true; setBusy(true); setScopeStatus('checking'); setCheckedScope(null)
    try {
      const people = await api.get(`/api/families/${operation.familyId}/members`)
      if (!currentOperation(operation) || pendingScopeRef.current !== operation) return
      const membership = people.members?.find(item => item.user_id === operation.userId && item.status === 'active')
      if (!membership || !Number.isInteger(membership.revision)) throw new Error('Family access unavailable')
      const values = scopeValues(membership.permissions)
      if (membership.revision === operation.revision + 1 && sameScope(values, operation.values)) {
        scopeRevision.current = membership.revision; scopeEdited.current = false
        setScopeBaseline({ familyId: operation.familyId, values }); setScope(values)
        pendingScopeRef.current = null; setPendingScope(null); setScopeConflict(false); setScopeStatus('saved')
        setAttempt(value => value + 1); window.dispatchEvent(new Event(subjectsChanged))
      } else {
        setCheckedScope({ ...operation, revision: membership.revision, values }); setScopeStatus('different')
      }
    } catch {
      if (currentOperation(operation) && pendingScopeRef.current === operation) setScopeStatus('checkFailed')
    } finally { if (currentSession(operation)) { actionBusy.current = false; setBusy(false) } }
  }
  const restoreCheckedScope = () => {
    if (!checkedScope || actionBusy.current || !currentOperation(checkedScope)
      || !window.confirm(t('familyFlow.useCheckedConfirm'))) return
    scopeRevision.current = checkedScope.revision; scopeEdited.current = false
    setScopeBaseline({ familyId: checkedScope.familyId, values: checkedScope.values }); setScope(checkedScope.values)
    pendingScopeRef.current = null; setPendingScope(null); setCheckedScope(null); setScopeConflict(false); setScopeStatus('checked')
    setAttempt(value => value + 1)
  }
  const discardScope = () => {
    if (!scopeBaseline || scopeBaseline.familyId !== selected || actionBusy.current || pendingScopeRef.current
      || !scopeDirty || !window.confirm(t('familyFlow.discardConfirm'))) return
    scopeEdited.current = false; setScope({ ...scopeBaseline.values }); setScopeStatus('idle')
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
      <button className="pilot-button secondary" disabled={controlsBlocked} onClick={() => run(() => api.post(`/api/families/${invitation.family_id}/accept`, {}))}>{t('polish.acceptInvitation')}</button>
      <button className="pilot-button secondary" disabled={controlsBlocked} onClick={() => run(() => api.post(`/api/families/${invitation.family_id}/decline`, {}))}>{t('polish.declineInvitation')}</button>
    </section>)}
    {families.length > 0 && <label>{t('polish.chooseFamily')}<select value={selected} disabled={busy || Boolean(pendingScope)} onChange={event => {
      if (actionBusy.current || pendingScopeRef.current) return
      if ((scopeEdited.current || scopeConflict) && !window.confirm(t('polish.discardSharingChanges'))) return
      resetScope()
      setMembers([]); setRecords([]); setSelected(event.target.value)
    }}>{families.map(group => <option key={group.family_id} value={group.family_id}>{group.name}</option>)}</select></label>}
    {(selected || pendingScope) && <section className="family-sharing-flow" aria-labelledby="family-sharing-heading">
      <h3 id="family-sharing-heading" ref={scopeHeading} tabIndex={-1}>{t('polish.mySharing')}</h3>
      {!pendingScope && scopeBaseline && <StatusMessage tone={scopeStatus === 'failed' && scopeDirty ? 'error' : 'info'}
        title={t(scopeConflict ? 'familyFlow.conflict' : scopeStatus === 'failed' && scopeDirty ? 'familyFlow.failed'
          : scopeDirty ? 'familyFlow.unsaved' : scopeStatus === 'saved' ? 'familyFlow.saved' : 'familyFlow.unchanged')}>
        <p>{t('familyFlow.localHint')}</p>
      </StatusMessage>}
      {pendingScope && <StatusMessage tone={scopeStatus === 'checkFailed' ? 'error' : 'info'}
        title={t(scopeStatus === 'saving' ? 'familyFlow.saving' : scopeStatus === 'checking' ? 'familyFlow.checking'
          : scopeStatus === 'checkFailed' ? 'familyFlow.checkFailed' : scopeStatus === 'different' ? 'familyFlow.different' : 'familyFlow.unconfirmed')}
        actions={<>
          <Button variant="secondary" disabled={busy} onClick={checkScope}>{t('familyFlow.check')}</Button>
          {checkedScope && <Button variant="secondary" disabled={busy} onClick={restoreCheckedScope}>{t('familyFlow.useChecked')}</Button>}
          <Button variant="secondary" disabled={busy} onClick={() => {
            if (!window.confirm(t('familyFlow.stopConfirm'))) return
            resetScope(); setSelected(''); setMembers([]); setRecords([]); setAttempt(value => value + 1)
          }}>{t('familyFlow.stop')}</Button>
        </>}>
        <p>{t('familyFlow.pendingHint')}</p>
        {checkedScope && <div className="family-sharing-comparison" role="region" tabIndex={0} aria-label={t('familyFlow.comparison')}>
          <table><caption>{t('familyFlow.comparison')}</caption>
            <thead><tr><th scope="col">{t('familyFlow.preference')}</th><th scope="col">{t('familyFlow.submitted')}</th><th scope="col">{t('familyFlow.checked')}</th></tr></thead>
            <tbody>{Object.keys(emptyScope).map(key => <tr key={key}>
              <th scope="row">{t(key === 'display_label' ? 'polish.recorderLabel' : `polish.sharingScopes.${key}`)}</th>
              {[pendingScope.values, checkedScope.values].map((values, index) => <td key={index}>{key === 'display_label'
                ? values[key] || t('familyFlow.noLabel') : t(values[key] ? 'familyFlow.allowed' : 'familyFlow.notAllowed')}</td>)}
            </tr>)}</tbody>
          </table>
        </div>}
      </StatusMessage>}
    </section>}
    {family && me && <>
      <form onSubmit={saveScope}><fieldset disabled={busy || scopeConflict || Boolean(pendingScope)}><legend>{t('polish.mySharing')}</legend>
        <label>{t('polish.recorderLabel')}<input value={scope.display_label} maxLength={40} onChange={event => editScope('display_label', event.target.value)} /></label>
        {['share_baby', 'share_parent', 'share_notes'].map(key => <label key={key}><input type="checkbox" checked={scope[key]}
          disabled={key === 'share_notes' && !scope.share_baby && !scope.share_parent} onChange={event => editScope(key, event.target.checked)} />{t(`polish.sharingScopes.${key}`)}</label>)}
        <p>{t('polish.sharingScopeNotice')}</p><p>{t('continuity.subject.shareNotice')}</p>{scopeEdited.current && <p role="status">{t('polish.sharingNotSaved')}</p>}
        <button className="pilot-button secondary" type="submit" disabled={!Number.isInteger(scopeRevision.current) || !scopeDirty}>{t('work.saveChanges')}</button>
        <Button variant="secondary" disabled={!scopeDirty} onClick={discardScope}>{t('familyFlow.discard')}</Button>
      </fieldset></form>
      {scopeConflict && <section className="pilot-panel" role="alert"><p>{t('polish.sharingConflict')}</p>
        <button type="button" className="pilot-button secondary" disabled={controlsBlocked} onClick={() => {
          if (actionBusy.current || pendingScopeRef.current) return
          if (scopeEdited.current && !window.confirm(t('polish.reloadSharingConfirm'))) return
          resetScope()
          setMembers([]); setRecords([]); setAttempt(value => value + 1)
        }}>{t('polish.reloadSharing')}</button>
      </section>}
      <section><h3>{t('polish.familyMembers')}</h3><ul>{members.map(member => <li key={member.id}>
        {memberLabel(member)} {member.user_id === userId ? `(${t('polish.you')})` : ''} · {t(`polish.memberStatus.${member.status}`)}
        {canManage && member.user_id !== family.created_by && (family.created_by === userId || !['owner', 'admin'].includes(member.role))
          && <button type="button" disabled={controlsBlocked} onClick={() => {
          if (window.confirm(t('polish.revokeConfirm'))) run(() => api.delete(`/api/families/${selected}/members/${encodeURIComponent(member.user_id)}`))
        }}>{t('polish.revokeMember')}</button>}
      </li>)}</ul></section>
      {canManage && <fieldset className="family-sharing-invite-controls" disabled={controlsBlocked} aria-label={t('flows.invitation.title')}>
        <FamilyInviteLinks key={selected} familyId={selected} visible={visible} membershipRevision={me.revision} />
      </fieldset>}
      {canManage && <details><summary>{t('flows.invitation.manual')}</summary><form onSubmit={event => { event.preventDefault(); run(async isCurrent => {
        await api.post(`/api/families/${selected}/invite`, { invitee_user_id: inviteId.trim(), role: 'member' })
        if (isCurrent()) setInviteId('')
      }) }}><label>{t('polish.inviteeId')}<input required maxLength={100} disabled={controlsBlocked} value={inviteId} onChange={event => setInviteId(event.target.value)} /></label>
        <button className="pilot-button secondary" disabled={controlsBlocked}>{t('polish.inviteMember')}</button></form></details>}
      {family.created_by !== userId && <button className="pilot-button secondary" disabled={controlsBlocked} onClick={() => {
        if (window.confirm([t('polish.leaveFamilyConfirm'), (scopeEdited.current || scopeConflict) && t('familyFlow.leaveDiscard')].filter(Boolean).join('\n\n'))) run(() => api.post(`/api/families/${selected}/leave`, {}))
      }}>{t('polish.leaveFamily')}</button>}
      <section><h3>{t('polish.sharedRecentRecords')}</h3><p>{t('polish.familyRecordedByNotice')}</p>
        {records.length === 0 ? <p>{t('polish.noSharedRecords')}</p> : <ol className="recent-records">{records.map(record => <li key={record.record_key}>
          <strong>{t(`tracking.${record.entry_type}`)}</strong><time>{japanDateTime(record.timestamp, i18n.resolvedLanguage || 'ja')}</time>
          <CareRecordIdentity record={record} />
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
    <form onSubmit={event => { event.preventDefault();
      if ((scopeEdited.current || scopeConflict) && !window.confirm(t('polish.discardSharingChanges'))) return
      run(async isCurrent => {
      const created = await api.post('/api/families/', { name })
      if (!isCurrent()) return
      resetScope()
      setSelected(created.family_id); setName('')
    }) }}><fieldset disabled={controlsBlocked}><legend>{t('polish.createFamily')}</legend>
      <label>{t('polish.familyName')}<input value={name} required maxLength={100} onChange={event => setName(event.target.value)} /></label>
      <button className="pilot-button secondary">{t('polish.createFamily')}</button>
    </fieldset></form>
  </div>
}
