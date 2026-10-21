import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useCareSession } from '../utils/CareSession'
import CareScope from './CareScope'

export const babyKinds = ['feeding', 'diaper', 'sleep', 'pumping']
export const privateSubject = subjectId => ({ subject_id: subjectId || null, family_shared: false, sharing_revision: null })

export function CareSubjectFields({ value, onChange, kind = 'feeding' }) {
  const { t } = useTranslation()
  const { subjects, ready, error, reload, rememberSubject } = useCareSession()
  if (!babyKinds.includes(kind)) return <CareScope kind={kind} />
  const selected = subjects.find(item => item.subject_id === value.subject_id)
  return <div className="care-subject-fields">
    <CareScope subjectId={value.subject_id} shared={value.family_shared} onUseLast={id => { rememberSubject(id); onChange(privateSubject(id)) }} />
    <label>{t('continuity.subject.recordFor')}<select value={value.subject_id || ''} disabled={!ready} onChange={event => { rememberSubject(event.target.value); onChange(privateSubject(event.target.value)) }}>
      <option value="">{t('continuity.subject.unknown')}</option>
      {value.subject_id && !selected && <option value={value.subject_id}>{t('continuity.subject.unavailable')}</option>}
      {subjects.map(item => <option key={item.subject_id} value={item.subject_id}>{item.nickname}{item.family_id ? ` · ${item.family_name}` : ` · ${t('continuity.subject.personal')}`}</option>)}
    </select></label>
    {error && <p role="alert">{t('continuity.subject.loadError')} <button type="button" className="text-action" onClick={reload}>{t('pilot.retry')}</button></p>}
    {selected?.family_id && <>
      <label><input type="checkbox" checked={value.family_shared === true} disabled={!selected.may_share && !value.family_shared} onChange={event => onChange({
        subject_id: selected.subject_id, family_shared: event.target.checked,
        sharing_revision: event.target.checked ? selected.sharing_revision : null,
      })} />{t('continuity.subject.shareRecord', { name: selected.family_name })}</label>
      <p className="field-hint">{t(selected.may_share ? 'continuity.subject.shareNotice' : 'continuity.subject.sharingOff')}</p>
      {value.family_shared && value.sharing_revision !== selected.sharing_revision && <p role="alert">{t('continuity.subject.permissionChanged')}</p>}
    </>}
    {!value.subject_id && <p className="field-hint">{t('continuity.subject.unassignedNotice')}</p>}
  </div>
}

export function CareRecordIdentity({ record }) {
  const { t } = useTranslation()
  const { subjects } = useCareSession()
  const name = record.subject_name || subjects.find(item => item.subject_id === record.subject_id)?.nickname
    || t(record.subject_id ? 'continuity.subject.unavailable' : 'continuity.subject.unassignedLabel')
  return <span className="field-hint care-record-identity">{babyKinds.includes(record.entry_type)
    ? t('continuity.subject.recordLabel', { name }) : t('continuity.subject.adult')}</span>
}

export default function CareSubjectManager() {
  const { t } = useTranslation()
  const care = useCareSession()
  const [families, setFamilies] = useState([])
  const [scope, setScope] = useState('')
  const [nickname, setNickname] = useState('')
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const writing = useRef(false)
  useEffect(() => {
    let active = true
    api.get('/api/families/').then(result => { if (active) setFamilies(result) }).catch(() => { if (active) setError('loadError') })
    return () => { active = false }
  }, [care.subjects])
  const save = async event => {
    event.preventDefault()
    if (writing.current) return
    writing.current = true; setBusy(true); setError('')
    try {
      const result = await api.post(editing ? `/api/care-subjects/${editing.subject_id}` : '/api/care-subjects', {
        nickname: nickname.trim(), family_id: editing ? editing.family_id : scope || null, revision: editing?.revision || 0,
      })
      const selected = editing ? editing.subject_id : result.find(item => (scope ? item.family_id === scope : !item.family_id))?.subject_id
      care.reload(); care.setActiveId(selected || ''); care.rememberSubject(selected || ''); setEditing(null); setNickname('')
    } catch (failure) { setError(failure.status === 403 ? 'managerOnly' : failure.status === 409 ? 'conflict' : 'saveError'); care.reload() }
    finally { writing.current = false; setBusy(false) }
  }
  return <details className="pilot-panel subject-manager"><summary>{t('continuity.subject.manage')}</summary>
    <p>{t('continuity.subject.notice')}</p>
    <ul>{care.subjects.map(item => <li key={item.subject_id}>{item.nickname} · {item.family_name || t('continuity.subject.personal')}
      {item.may_edit && <button type="button" className="text-action" disabled={busy} onClick={() => {
        setEditing(item); setNickname(item.nickname); setScope(item.family_id || '')
      }}>{t('continuity.subject.rename')}</button>}
    </li>)}</ul>
    <form onSubmit={save}><fieldset disabled={busy || !care.ready}><legend>{t(editing ? 'continuity.subject.rename' : 'continuity.subject.create')}</legend>
      {!editing && <label>{t('continuity.subject.scope')}<select value={scope} onChange={event => setScope(event.target.value)}>
        <option value="">{t('continuity.subject.personal')}</option>
        {families.map(family => <option key={family.family_id} value={family.family_id}>{family.name}</option>)}
      </select></label>}
      <label>{t('continuity.subject.nickname')}<input required maxLength={40} value={nickname} onChange={event => setNickname(event.target.value)} /></label>
      <p>{t(scope ? 'continuity.subject.familyNotice' : 'continuity.subject.personalNotice')}</p>
      <button type="submit" className="pilot-button" disabled={!nickname.trim()}>{t(editing ? 'work.saveChanges' : 'continuity.subject.createAndSelect')}</button>
      {editing && <button type="button" className="pilot-button secondary" onClick={() => { setEditing(null); setNickname(''); setScope('') }}>{t('tracking.cancel')}</button>}
    </fieldset></form>
    {error && <p role="alert">{t(`continuity.subject.${error}`)}</p>}
  </details>
}
