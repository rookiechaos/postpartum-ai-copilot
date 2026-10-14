import { japanDay } from './japanTime'
import { publicHttps } from './publicDirectory'

export const businessLimits = { name: 100, municipality: 100, contact: 200, hours: 200, phone: 40, email: 255,
  retention_notice: 1000, ai_data_notice: 1500, account_support_notice: 1000 }
export const resourceLimits = { name: 100, url: 500, description: 500, hours: 200, area: 100, audience: 200,
  phone: 40, booking_url: 500, cost_note: 300, maintainer: 100, pause_notice: 500,
  application_steps: 800, preparation: 500, fallback_contact: 500 }
export const directoryFieldId = (scope, field, resourceKey = '') => `directory-${scope}-${resourceKey || 'business'}-${field}`

const normalizePhone = value => String(value || '').normalize('NFKC').replace(/[‐‑‒–—−ー]/g, '-').trim()
export function normalizeDirectory(profile) {
  const normalize = item => ({ ...item, name: (item.name || '').trim(), phone: normalizePhone(item.phone) })
  return { ...normalize(profile), email: (profile.email || '').trim(), resources: profile.resources.map(item => ({
    ...normalize(item), url: (item.url || '').trim(), booking_url: item.booking_url?.trim() || null,
  })) }
}
function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number(value.slice(0, 4)) < 1) return false
  const parsed = new Date(`${value}T00:00:00Z`)
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value
}
// Drafts allow empty publication fields, but both paths use the API's format limits.
export function validateDirectory(profile, { publication = false, today = japanDay() } = {}) {
  const issues = []
  const check = (item, scope, resourceKey, limits) => {
    const add = (field, messageKey, values = {}) => {
      if (!issues.some(issue => issue.scope === scope && issue.resourceKey === resourceKey && issue.field === field)) {
        issues.push({ scope, resourceKey, field, messageKey, values })
      }
    }
    Object.entries(limits).forEach(([field, max]) => {
      if ([...String(item[field] || '')].length > max) add(field, 'tooLong', { max })
    })
    if (publication && !item.name?.trim()) add('name', 'required')
    if (item.phone && !/^[0-9+() #.-]*$/.test(item.phone)) add('phone', 'phone')
    if (scope === 'business' && item.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(item.email)) add('email', 'email')
    if (scope === 'resource') {
      if (publication && !item.url?.trim()) add('url', 'required')
      for (const field of ['url', 'booking_url']) {
        if (item[field] && (!/^https:\/\//i.test(item[field]) || !publicHttps(item[field]))) add(field, 'https')
      }
      if (!['parenting', 'postpartum', 'feeding'].includes(item.category || 'parenting')) add('category', 'invalid')
      if (!['active', 'paused'].includes(item.service_status || 'active')) add('service_status', 'invalid')
      for (const field of ['checked_on', 'review_due_on']) {
        if (item[field] && !validDate(item[field])) add(field, 'date')
      }
      if (item.checked_on && validDate(item.checked_on) && item.checked_on > today) add('checked_on', 'futureDate')
    }
  }
  check(profile, 'business', '', businessLimits)
  profile.resources.forEach(item => check(item, 'resource', item.resource_key, resourceLimits))
  if (profile.resources.length > 10) issues.push({ scope: 'business', resourceKey: '', field: 'resources', messageKey: 'contactLimit' })
  return issues
}

// API error metadata contains field paths and codes only, never submitted values.
export function directoryServerIssues(validation, profile) {
  return (validation || []).flatMap(item => {
    const path = item.loc || []
    const profileIndex = path.indexOf('profile')
    if (profileIndex < 0) return []
    const fields = path.slice(profileIndex + 1)
    const resource = fields[0] === 'resources' && Number.isInteger(fields[1]) ? profile.resources[fields[1]] : null
    const field = resource ? fields[2] : fields[0]
    const allowed = resource ? { ...resourceLimits, category: 1, service_status: 1, checked_on: 1, review_due_on: 1 } : { ...businessLimits, resources: 1 }
    if (!Object.hasOwn(allowed, field)) return []
    return [{ scope: resource ? 'resource' : 'business', resourceKey: resource?.resource_key || '', field, messageKey: 'invalid' }]
  })
}

export function publicationChanges(published, draft) {
  const changes = []
  const value = (item, field) => item?.[field] ?? (field === 'service_status' ? 'active' : '')
  const compare = (before, after, scope, name = '') => {
    const fields = scope === 'business' ? Object.keys(businessLimits)
      : [...Object.keys(resourceLimits), 'category', 'service_status', 'checked_on', 'review_due_on']
    fields.forEach(field => {
      if (value(before, field) !== value(after, field)) changes.push({ scope, name, field,
        before: String(value(before, field)), after: String(value(after, field)), kind: 'updated' })
    })
  }
  compare(published || {}, draft, 'business')
  const old = new Map((published?.resources || []).map(item => [item.resource_key, item]))
  const next = new Map(draft.resources.map(item => [item.resource_key, item]))
  next.forEach((item, key) => {
    if (!old.has(key)) changes.push({ name: item.name, kind: 'added' })
    else compare(old.get(key), item, 'resource', item.name)
  })
  old.forEach((item, key) => { if (!next.has(key)) changes.push({ name: item.name, kind: 'removed' }) })
  return changes
}
