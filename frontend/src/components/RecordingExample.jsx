import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'

export default function RecordingExample() {
  const { t } = useTranslation()
  const [step, setStep] = useState(0)
  const [kind, setKind] = useState('wet')
  return <details className="pilot-panel recording-example"><summary>{t('polish.exampleTitle')}</summary>
    <p>{t('polish.exampleNotice')}</p>
    <ol className="recording-walkthrough">{['record', 'find', 'correct'].map((key, index) => <li key={key} aria-current={Math.min(step, 2) === index ? 'step' : undefined}>{t(`flows.walkthrough.${key}`)}</li>)}</ol>
    {step === 0 && <button type="button" className="pilot-button secondary" onClick={() => setStep(1)}>{t('polish.exampleAction')}</button>}
    {step > 0 && <article className="support-card"><h4>{t('flows.walkthrough.sampleRecent')}</h4>
      <p>{t('flows.walkthrough.sampleTime')} · {t(`tracking.${kind}`)}</p>
      <p role="status">{t(step === 3 ? 'flows.walkthrough.corrected' : 'flows.walkthrough.saved')}</p>
    </article>}
    {step === 1 && <><p>{t('flows.walkthrough.where')}</p><button type="button" className="pilot-button secondary" onClick={() => setStep(2)}>{t('flows.walkthrough.tryCorrection')}</button></>}
    {step === 2 && <fieldset><legend>{t('flows.walkthrough.chooseCorrection')}</legend><div className="record-choices">
      {['wet', 'dirty', 'both'].map(value => <button type="button" key={value} className="pilot-button secondary" aria-pressed={kind === value} onClick={() => setKind(value)}>{t(`tracking.${value}`)}</button>)}
    </div><button type="button" className="pilot-button secondary" onClick={() => setStep(3)}>{t('flows.walkthrough.saveCorrection')}</button></fieldset>}
    {step > 0 && <button type="button" className="pilot-button secondary" onClick={() => { setStep(0); setKind('wet') }}>{t('flows.walkthrough.reset')}</button>}
  </details>
}
