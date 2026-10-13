import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime, japanDay, utcDate } from '../utils/japanTime'
import { useToast } from './Toast'
import './ExportData.css'

// Backups preserve every supported record field; consultation formatting is intentionally compact.
const backupFields = ['id', 'record_key', 'revision', 'user_id', 'entry_type', 'timestamp',
  'feeding_type', 'duration_minutes', 'amount_ml', 'side', 'diaper_type', 'sleep_duration_minutes',
  'sleep_quality', 'mood_level', 'mood_notes', 'pumped_amount_ml', 'weight_kg', 'breast_condition', 'recovery_notes', 'notes']

// Quote all cells and neutralize spreadsheet formula prefixes in user-authored text.
const csvCell = value => {
  let cell = String(value ?? '')
  if (/^[\s\uFEFF]*[=+\-@]/u.test(cell) || /^[\t\r\n]/u.test(cell)) cell = `'${cell}`
  return `"${cell.replaceAll('"', '""')}"`
}

export default function ExportData({ userId }) {
  const { t, i18n } = useTranslation()
  const [exporting, setExporting] = useState(false)
  const toast = useToast()
  const download = async format => {
    if (exporting) return
    setExporting(true)
    try {
      const entries = await api.getTracking(userId, 365)
      const language = i18n.resolvedLanguage || 'ja'
      let content
      if (format === 'json') {
        content = JSON.stringify({ exportDate: new Date().toISOString(), userId, entries }, null, 2)
      } else {
        const headers = [t('work.exportDate'), ...backupFields.map(key => `${t(`work.backupFields.${key}`)} (${key})`)]
        const rows = entries.map(entry => [entry.timestamp ? japanDateTime(entry.timestamp, language) : '',
          ...backupFields.map(key => key === 'timestamp' && entry.timestamp ? utcDate(entry.timestamp).toISOString() : entry[key])])
        content = '\uFEFF' + [headers, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n')
      }
      const url = URL.createObjectURL(new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv;charset=utf-8' }))
      const link = document.createElement('a')
      link.href = url; link.download = `postpartum-backup-${japanDay(new Date())}.${format}`
      document.body.appendChild(link); link.click(); link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      toast.success(t('work.exportSuccess'))
    } catch { toast.error(t('work.exportFailed')) }
    finally { setExporting(false) }
  }
  return <section className="export-data">
    <div className="export-header"><h3>{t('work.exportTitle')}</h3><p>{t('work.exportNotice')}</p></div>
    <div className="export-options">{['csv', 'json'].map(format => <button key={format} className="export-button" disabled={exporting} onClick={() => download(format)}>
      {exporting ? t('common.loading') : t(`work.exportFormats.${format}`)}
    </button>)}</div>
  </section>
}
