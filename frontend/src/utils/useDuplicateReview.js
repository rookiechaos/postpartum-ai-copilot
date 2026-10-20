import { useRef, useState } from 'react'
import api from './api'

export default function useDuplicateReview() {
  const [review, setReview] = useState(null)
  const checking = useRef(false)
  const check = async operation => {
    if (!operation.subject_id) return true
    if (checking.current) return false
    checking.current = true
    try {
      // Only structured care fields enter this local comparison, never free text.
      const fields = ['entry_type', 'timestamp', 'subject_id', 'feeding_type', 'diaper_type', 'amount_ml', 'duration_minutes', 'sleep_duration_minutes']
      const result = await api.post('/api/tracking/duplicate-check', Object.fromEntries(fields.map(key => [key, operation[key]])))
      if (!result.matches.length) return true
      setReview({ operation, matches: result.matches, failed: false }); return false
    } catch { setReview({ operation, matches: [], failed: true }); return false }
    finally { checking.current = false }
  }
  return { review, check, clear: () => setReview(null) }
}
