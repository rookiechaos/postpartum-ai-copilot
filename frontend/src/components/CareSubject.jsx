import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useCareSession } from '../utils/CareSession'
import CareScope from './CareScope'
import { Button, EmptyState, ErrorMessage, FormField } from './ui'

export const babyKinds = ['feeding', 'diaper', 'sleep', 'pumping']
export const privateSubject = subjectId => ({ subject_id: subjectId || null, family_shared: false, sharing_revision: null })

export function CareSubjectFields({ value, onChange, kind = 'feeding', compact = false }) {
  const { t } = useTranslation()
  const { subjects, ready, error, reload, rememberSubject } = useCareSession()
  if (!babyKinds.includes(kind)) return <CareScope kind={kind} />
  const selected = subjects.find(item => item.subject_id === value.subject_id)
  const context = <CareScope compact={compact} subjectId={value.subject_id} shared={value.family_shared}
    onUseLast={id => { rememberSubject(id); onChange(privateSubject(id)) }} />
  return <div className={`care-subject-fields${compact ? ' care-subject-fields--compact' : ''}`}>
    {!compact && context}
    <FormField as="select" label={t('continuity.subject.recordFor')} value={value.subject_id || ''} disabled={!ready}
      onChange={event => { rememberSubject(event.target.value); onChange(privateSubject(event.target.value)) }}>
      <option value="">{t('continuity.subject.unknown')}</option>
      {value.subject_id && !selected && <option value={value.subject_id}>{t('continuity.subject.unavailable')}</option>}
      {subjects.map(item => <option key={item.subject_id} value={item.subject_id}>{item.nickname}{item.family_id ? ` · ${item.family_name}` : ` · ${t('continuity.subject.personal')}`}</option>)}
    </FormField>
    {compact && context}
    {error && <ErrorMessage title={t('continuity.subject.loadError')} onRetry={reload} />}
    {selected?.family_id && <>
      <label className="checkbox-label"><input type="checkbox" checked={value.family_shared === true} disabled={!selected.may_share && !value.family_shared} onChange={event => onChange({
        subject_id: selected.subject_id, family_shared: event.target.checked,
        sharing_revision: event.target.checked ? selected.sharing_revision : null,
      })} />{t('continuity.subject.shareRecord', { name: selected.family_name })}</label>
      <p className="field-hint">{t(selected.may_share ? 'continuity.subject.shareNotice' : 'continuity.subject.sharingOff')}</p>
      {value.family_shared && value.sharing_revision !== selected.sharing_revision && <ErrorMessage title={t('continuity.subject.permissionChanged')} />}
    </>}
    {!compact && !value.subject_id && <p className="field-hint">{t('continuity.subject.unassignedNotice')}</p>}
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

export default function CareSubjectManager({ visible = true }) {
  const { t } = useTranslation()
  const care = useCareSession()
  const [families, setFamilies] = useState([])
  const [scope, setScope] = useState('')
  const [nickname, setNickname] = useState('')
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(false)
  const writing = useRef(false)
  useEffect(() => {
    if (!visible || !expanded) return
    let active = true
    api.get('/api/families/').then(result => {
      if (active) { setFamilies(result); setError(previous => previous === 'loadError' ? '' : previous) }
    }).catch(() => { if (active) setError('loadError') })
    return () => { active = false }
  }, [care.subjects, visible, expanded])
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
  return <details className="pilot-panel subject-manager ui-disclosure" onToggle={event => {
    if (event.target === event.currentTarget) setExpanded(event.currentTarget.open)
  }}><summary id="care-subject-heading">{t('continuity.subject.manage')}
    {nickname.trim() ? ` · ${t('flows.overview.unsaved')}` : ''}</summary>
    <p>{t('continuity.subject.notice')}</p>
    {care.ready && !care.subjects.length && <EmptyState compact icon={false} suggestions={[]}
      title={t('foundation.home.noBaby')} description={t('foundation.home.noBabyHint')} />}
    <ul>{care.subjects.map(item => <li key={item.subject_id}>{item.nickname} · {item.family_name || t('continuity.subject.personal')}
      {item.may_edit && <button type="button" className="text-action" disabled={busy} onClick={() => {
        setEditing(item); setNickname(item.nickname); setScope(item.family_id || '')
      }}>{t('continuity.subject.rename')}</button>}
    </li>)}</ul>
    <form onSubmit={save}><fieldset disabled={busy || !care.ready}><legend>{t(editing ? 'continuity.subject.rename' : 'continuity.subject.create')}</legend>
      {!editing && <FormField as="select" label={t('continuity.subject.scope')} value={scope} onChange={event => setScope(event.target.value)}>
        <option value="">{t('continuity.subject.personal')}</option>
        {scope && !families.some(family => family.family_id === scope) && <option value={scope}>{t('continuity.subject.unavailable')}</option>}
        {families.map(family => <option key={family.family_id} value={family.family_id}>{family.name}</option>)}
      </FormField>}
      <FormField label={t('continuity.subject.nickname')} required maxLength={40} value={nickname} onChange={event => setNickname(event.target.value)} />
      <p>{t(scope ? 'continuity.subject.familyNotice' : 'continuity.subject.personalNotice')}</p>
      <Button type="submit" busy={busy} busyLabel={t('settings.saving')} disabled={!nickname.trim()}>{t(editing ? 'work.saveChanges' : 'continuity.subject.createAndSelect')}</Button>
      {editing && <Button variant="secondary" onClick={() => { setEditing(null); setNickname(''); setScope('') }}>{t('tracking.cancel')}</Button>}
    </fieldset></form>
    {error && <ErrorMessage title={t(`continuity.subject.${error}`)} onRetry={error === 'loadError' ? care.reload : undefined} />}
  </details>
}
