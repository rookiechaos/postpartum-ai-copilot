import React from 'react'
import { useTranslation } from 'react-i18next'
import { useCareSession } from '../utils/CareSession'

export default function CareScope({ subjectId, shared = false, mode = 'record', kind = 'feeding', onUseLast, disabled = false, familyName = '', compact = false }) {
  const { t } = useTranslation()
  const care = useCareSession()
  const subject = care.subjects.find(item => item.subject_id === subjectId)
  const recent = care.subjects.find(item => item.subject_id === care.recentSubjectId)
  const adult = ['mood', 'recovery'].includes(kind)
  const label = item => `${item.nickname} · ${item.family_name || t('continuity.subject.personal')}`
  const name = adult ? t('continuity.subject.adult') : subjectId === '*' ? t('workflow.context.allOwn')
    : subject ? label(subject) : t(subjectId ? 'continuity.subject.unavailable' : 'continuity.subject.unknown')
  return <aside className={`care-scope${compact ? ' care-scope--compact' : ''}`} aria-label={t('workflow.context.title')}>
    {!compact && <strong>{familyName ? t('workflow.context.familyView', { name: familyName }) : t('workflow.context.subject', { name })}</strong>}
    {adult && mode === 'record' ? <>
      <span>{t(care.adultSharing === null ? 'workflow.context.visibilityUnknown' : care.adultSharing.length ? 'workflow.context.adultShared' : 'workflow.context.adultPrivate')}</span>
      {care.adultSharing?.map((family, index) => <span key={index}>{family.name} · {t(family.includes_notes ? 'workflow.context.withNotes' : 'workflow.context.withoutNotes')}</span>)}
      {care.adultSharing === null && <button type="button" className="text-action" onClick={care.reload}>{t('pilot.retry')}</button>}
    </> : <span>{t(familyName ? 'workflow.context.viewShared' : mode === 'record' && shared ? 'workflow.context.shareRecord'
      : mode === 'record' ? 'workflow.context.privateRecord' : mode === 'analysis' ? 'workflow.context.analysis'
        : mode === 'sheet' ? 'workflow.context.sheet' : 'workflow.context.ownView')}</span>}
    {!adult && !familyName && onUseLast && recent && recent.subject_id !== subjectId && <button type="button" className="text-action"
      disabled={disabled || !care.ready} onClick={() => {
        if (window.confirm(t('workflow.context.confirmUse', { name: label(recent) }))) onUseLast(recent.subject_id)
      }}>{t('workflow.context.useLast', { name: label(recent) })}</button>}
  </aside>
}
