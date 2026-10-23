import api from './api'
import { utcDate } from './japanTime'
import { recordFields } from './recordOperations'

// A POST receipt proves creation happened, not that its original content remains.
// Read by the owner's immutable request key before discarding a pending creation.
export async function readCreationResult(operation) {
  const result = await api.get(`/api/tracking/operations/${encodeURIComponent(operation.request_key)}`)
  if (result?.state === 'not_found' || result?.state === 'deleted') return { state: result.state, record: null }
  const record = result?.record
  if (result?.state !== 'saved' || !record || !Number.isInteger(record.id) || !record.record_key
    || !Number.isInteger(record.revision) || record.revision < 1) throw new Error('Save result unavailable')
  const matches = recordFields.every(key => {
    const fallback = key === 'family_shared' ? false : null
    const expected = operation[key] ?? fallback
    const actual = record[key] ?? fallback
    if (['timestamp', 'end_timestamp'].includes(key)) {
      return expected === null || actual === null ? expected === actual
        : utcDate(expected).getTime() === utcDate(actual).getTime()
    }
    return actual === expected
  })
  return { state: record.revision === 1 && matches ? 'matched' : 'changed', record }
}
