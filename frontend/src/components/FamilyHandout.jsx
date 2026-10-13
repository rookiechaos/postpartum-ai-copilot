import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import QRCode from 'qrcode'
import { printView } from '../utils/printView'

export default function FamilyHandout({ familyLink, organizationName }) {
  const { t } = useTranslation()
  const [qr, setQr] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    setQr(''); setError('')
    QRCode.toDataURL(familyLink, { width: 256, margin: 4, errorCorrectionLevel: 'M' })
      .then(value => { if (active) setQr(value) }).catch(() => { if (active) setError(t('work.qrFailed')) })
    return () => { active = false }
  }, [familyLink])
  return <div className="family-handout">
    <p>{t('work.familyLinkNotice')}</p>
    {qr && <><img className="family-qr" src={qr} width={256} height={256} alt={t('work.qrAlt')} />
      <div className="pilot-actions"><a className="pilot-button secondary" href={qr} download="family-entry-qr.png">{t('work.downloadQr')}</a>
        <button className="pilot-button secondary" onClick={() => {
          try { printView('family-handout-print') } catch { setError(t('work.printFailed')) }
        }}>{t('work.printHandout')}</button></div></>}
    {error && <p role="alert">{error}</p>}
    <article id="family-handout-print" className="print-sheet">
      <h1>{t('app.title')}</h1><h2>{organizationName || t('pilot.familyTitle')}</h2>
      {qr && <img className="family-qr" src={qr} width={256} height={256} alt={t('work.qrAlt')} />}
      <p className="handout-link">{familyLink}</p>
      <ol>{['handoutStep1', 'handoutStep2', 'handoutStep3'].map(key => <li key={key}>{t(`work.${key}`)}</li>)}</ol>
      <p>{t('pilot.entryPrivacy')}</p><p>{t('work.installNetwork')}</p><p>{t('pilot.noMonitoring')}</p>
    </article>
  </div>
}
