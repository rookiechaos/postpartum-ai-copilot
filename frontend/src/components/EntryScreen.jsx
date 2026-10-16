import React from 'react'
import { useTranslation } from 'react-i18next'
import { Baby, Building2, ArrowRight } from 'lucide-react'
import LanguageSelector from './LanguageSelector'
import SupportDirectory from './SupportDirectory'
import ProductBrand from './ProductBrand'
import OperatorInfo from './OperatorInfo'
import './Pilot.css'

export default function EntryScreen({ onChoose }) {
  const { t } = useTranslation()
  return (
    <main className="pilot-shell entry-screen">
      <div className="pilot-topbar"><ProductBrand /><LanguageSelector /></div>
      <header className="entry-intro">
        <p className="pilot-eyebrow">{t('pilot.eyebrow')}</p>
        <h1>{t('pilot.entryTitle')}</h1>
        <p>{t('pilot.entryDescription')}</p>
      </header>
      <OperatorInfo />
      <div className="entry-grid">
        <article className="entrance-card">
          <Baby size={32} aria-hidden="true" />
          <h2>{t('pilot.familyTitle')}</h2>
          <p>{t('pilot.familyDescription')}</p>
          <ul><li>{t('pilot.familyBenefit1')}</li><li>{t('pilot.familyBenefit2')}</li><li>{t('pilot.familyBenefit3')}</li></ul>
          <a href="/family" className="pilot-button" onClick={event => { event.preventDefault(); onChoose('family') }}>
            {t('pilot.enterFamily')} <ArrowRight size={18} aria-hidden="true" />
          </a>
        </article>
        <article className="entrance-card">
          <Building2 size={32} aria-hidden="true" />
          <h2>{t('pilot.organizationTitle')}</h2>
          <p>{t('pilot.organizationDescription')}</p>
          <ul><li>{t('pilot.organizationBenefit1')}</li><li>{t('pilot.organizationBenefit2')}</li><li>{t('pilot.organizationBenefit3')}</li></ul>
          <a href="/organization" className="pilot-button secondary" onClick={event => { event.preventDefault(); onChoose('organization') }}>
            {t('pilot.enterOrganization')} <ArrowRight size={18} aria-hidden="true" />
          </a>
        </article>
      </div>
      <p className="pilot-note">{t('pilot.entryPrivacy')}</p>
      <SupportDirectory />
    </main>
  )
}
