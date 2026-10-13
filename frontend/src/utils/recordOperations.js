export function requestKey() {
  if (globalThis.crypto.randomUUID) return globalThis.crypto.randomUUID()
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function recordOperation(data) {
  return { ...data, timestamp: data.timestamp || new Date().toISOString(), request_key: requestKey() }
}

export function isRecordOperation(value) {
  return Boolean(value && typeof value === 'object' && typeof value.request_key === 'string'
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value.request_key)
    && ['feeding', 'diaper', 'sleep', 'mood', 'pumping', 'recovery'].includes(value.entry_type)
    && typeof value.timestamp === 'string' && Number.isFinite(new Date(value.timestamp).getTime()))
}
