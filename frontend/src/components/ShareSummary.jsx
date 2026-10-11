import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { buildCareSummary } from '../utils/careSummary'
import { japanDay } from '../utils/japanTime'

export default function ShareSummary({ userId }) {
  const { t, i18n } = useTranslation()
  const [includeParent, setIncludeParent] = useState(false)
  const [includeNotes, setIncludeNotes] = useState(false)
  const [preview, setPreview] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const prepare = async () => {
    setLoading(true)
    setError('')
    setPreview('')
    try {
      const entries = await api.getTracking(userId, 7)
      const summary = buildCareSummary(entries, { includeParent, includeNotes, language: i18n.language, t })
      setPreview(summary ? `${t('pilot.summaryHeader')}\n${summary}` : '')
      if (!summary) setError(t('pilot.noSummaryEntries'))
    } catch { setError(t('pilot.loadFailed')) }
    finally { setLoading(false) }
  }
  const download = () => {
    const url = URL.createObjectURL(new Blob([preview], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `care-summary-${japanDay()}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }
  return <section className="pilot-panel share-summary">
    <h2>{t('pilot.summaryTitle')}</h2>
    <p>{t('pilot.summaryDescription')}</p>
    <fieldset disabled={loading}>
      <label className="checkbox-label"><input type="checkbox" checked={includeParent} onChange={event => {
        setIncludeParent(event.target.checked); setPreview('')
      }} />{t('pilot.includeParent')}</label>
      <label className="checkbox-label"><input type="checkbox" checked={includeNotes} onChange={event => {
        setIncludeNotes(event.target.checked); setPreview('')
      }} />{t('pilot.includeNotes')}</label>
    </fieldset>
    <button className="pilot-button secondary" disabled={loading} onClick={prepare}>{loading ? t('common.loading') : t('pilot.prepareSummary')}</button>
    {error && <p role="status">{error}</p>}
    {preview && <>
      <label>{t('pilot.summaryPreview')}<textarea rows={10} value={preview} onChange={event => setPreview(event.target.value)} /></label>
      <p>{t('pilot.summarySharingNote')}</p>
      <button className="pilot-button" onClick={download}>{t('pilot.downloadSummary')}</button>
    </>}
  </section>
}
