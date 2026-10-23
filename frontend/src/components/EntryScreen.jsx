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
        <div className="entry-intro-copy">
          <p className="pilot-eyebrow">{t('pilot.eyebrow')}</p>
          <h1>{t('pilot.entryTitle')}</h1>
          <p>{t('pilot.entryDescription')}</p>
        </div>
        <svg className="entry-illustration" viewBox="0 0 200 180" fill="none" aria-hidden="true" focusable="false">
          <circle cx="99" cy="91" r="74" fill="var(--color-tint)" />
          <circle cx="148" cy="45" r="23" fill="var(--color-accent-tint)" />
          <path d="M53 104c7 30 25 45 47 45s40-15 47-45" stroke="var(--color-brand)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M65 105c6-21 19-31 35-31s29 10 35 31" stroke="var(--color-brand)" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="100" cy="68" r="19" fill="var(--color-surface)" stroke="var(--color-brand)" strokeWidth="2" />
          <path d="M94 69c3 4 9 4 12 0M100 49c-5-8 2-14 7-10" stroke="var(--color-brand)" strokeWidth="2" strokeLinecap="round" />
          <path d="M78 109c8 9 17 13 27 11M62 143l-9 10m85-10 9 10" stroke="var(--color-brand)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M150 80c4-13 11-20 23-22-1 12-8 20-23 22Z" fill="var(--color-accent-tint)" stroke="var(--color-accent)" strokeWidth="1.5" />
          <path d="m150 81-5 9M39 61l4-9m-10 2 8 3" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </header>
      <OperatorInfo />
      <div className="entry-grid">
        <article className="entrance-card entrance-card--family">
          <span className="entrance-symbol"><Baby size={28} strokeWidth={1.7} aria-hidden="true" /></span>
          <h2>{t('pilot.familyTitle')}</h2>
          <p>{t('pilot.familyDescription')}</p>
          <ul><li>{t('pilot.familyBenefit1')}</li><li>{t('pilot.familyBenefit2')}</li><li>{t('pilot.familyBenefit3')}</li></ul>
          <a href="/family" className="pilot-button" onClick={event => { event.preventDefault(); onChoose('family') }}>
            {t('pilot.enterFamily')} <ArrowRight size={18} aria-hidden="true" />
          </a>
        </article>
        <article className="entrance-card entrance-card--organization">
          <span className="entrance-symbol"><Building2 size={28} strokeWidth={1.7} aria-hidden="true" /></span>
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
