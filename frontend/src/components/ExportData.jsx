import React, { useState } from 'react'
import api from '../utils/api'
import { Download, FileText, FileSpreadsheet, Loader } from 'lucide-react'
import { useToast } from './Toast'
import './ExportData.css'

function ExportData({ userId }) {
  const [exporting, setExporting] = useState(false)
  const toast = useToast()

  const exportToCSV = async () => {
    setExporting(true)
    try {
      const entries = await api.getTracking(userId, 365)
      // Convert to CSV
      const headers = ['Date', 'Type', 'Details', 'Notes']
      const rows = entries.map(entry => {
        const date = new Date(entry.timestamp).toLocaleString()
        const type = entry.entry_type
        let details = ''
        
        switch(entry.entry_type) {
          case 'feeding':
            details = `Type: ${entry.feeding_type || 'N/A'}, Duration: ${entry.duration_minutes || 0}min, Amount: ${entry.amount_ml || 0}ml`
            break
          case 'diaper':
            details = `Type: ${entry.diaper_type || 'N/A'}`
            break
          case 'sleep':
            details = `Duration: ${entry.sleep_duration_minutes || 0}min, Quality: ${entry.sleep_quality || 'N/A'}`
            break
          case 'mood':
            details = `Level: ${entry.mood_level || 'N/A'}, Notes: ${entry.mood_notes || 'N/A'}`
            break
          default:
            details = 'N/A'
        }
        
        return [date, type, details, entry.notes || '']
      })

      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n')

      // Download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `postpartum-data-${new Date().toISOString().split('T')[0]}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      toast.success('Data exported successfully!')
    } catch (error) {
      console.error('Export error:', error)
      toast.error('Failed to export data. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const exportToJSON = async () => {
    setExporting(true)
    try {
      const entries = await api.getTracking(userId, 365)
      const data = {
        exportDate: new Date().toISOString(),
        userId: userId,
        entries
      }

      const jsonContent = JSON.stringify(data, null, 2)
      const blob = new Blob([jsonContent], { type: 'application/json' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `postpartum-data-${new Date().toISOString().split('T')[0]}.json`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      toast.success('Data exported successfully!')
    } catch (error) {
      console.error('Export error:', error)
      toast.error(error?.message || 'Failed to export data. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="export-data">
      <div className="export-header">
        <h3>Export Your Data</h3>
        <p>Download your tracking data for backup or sharing with healthcare providers</p>
      </div>

      <div className="export-options">
        <button
          className="export-button"
          onClick={exportToCSV}
          disabled={exporting}
        >
          {exporting ? (
            <Loader className="spinner" size={20} />
          ) : (
            <FileSpreadsheet size={20} />
          )}
          <span>Export as CSV</span>
          <small>Excel compatible</small>
        </button>

        <button
          className="export-button"
          onClick={exportToJSON}
          disabled={exporting}
        >
          {exporting ? (
            <Loader className="spinner" size={20} />
          ) : (
            <FileText size={20} />
          )}
          <span>Export as JSON</span>
          <small>Raw data format</small>
        </button>
      </div>

      <div className="export-info">
        <p>💡 <strong>Tip:</strong> Exported data includes all your tracking entries. You can share this with your healthcare provider.</p>
      </div>
    </div>
  )
}

export default ExportData
