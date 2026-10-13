import { useCallback, useEffect, useRef, useState } from 'react'
import api from './api'

export const draftPreferenceEvent = 'postpartum-draft-preference'

// Health text stays in account-bound server drafts; it is never written to localStorage.
export default function useAccountDraft(kind, userId, content, onRestore) {
  const [candidate, setCandidate] = useState(null)
  const [status, setStatus] = useState('loading')
  const [attempt, setAttempt] = useState(0)
  const [savedContent, setSavedContent] = useState(null)
  const metadata = useRef({ loaded: false, enabled: false, preferenceRevision: 0, revision: 0, approved: false })
  const generation = useRef(0)
  const queue = useRef(Promise.resolve())
  const lastSaved = useRef(null)
  const restore = useRef(onRestore)
  restore.current = onRestore
  const serialized = content ? JSON.stringify(content) : null

  useEffect(() => {
    let active = true
    const token = ++generation.current
    metadata.current.approved = false
    metadata.current.loaded = false
    setStatus('loading')
    api.get(`/api/drafts/${kind}`).then(result => {
      if (!active || token !== generation.current) return
      metadata.current = { loaded: true, enabled: result.enabled, preferenceRevision: result.revision,
        revision: result.draft_revision || 0, approved: !result.draft }
      setCandidate(result.draft)
      lastSaved.current = result.draft ? JSON.stringify(result.draft.content) : null
      setSavedContent(lastSaved.current)
      setStatus(result.enabled ? 'ready' : 'off')
    }).catch(() => { if (active && token === generation.current) setStatus('error') })
    return () => { active = false; generation.current++ }
  }, [kind, userId, attempt])
  useEffect(() => {
    const reload = () => setAttempt(value => value + 1)
    window.addEventListener(draftPreferenceEvent, reload)
    return () => window.removeEventListener(draftPreferenceEvent, reload)
  }, [])

  useEffect(() => {
    const current = metadata.current
    if (!serialized || candidate || !current.enabled || !current.approved || status === 'loading' || status === 'conflict'
      || serialized === lastSaved.current) return
    const token = generation.current
    const preferenceRevision = current.preferenceRevision
    const timer = setTimeout(() => {
      setStatus('saving')
      queue.current = queue.current.catch(() => {}).then(async () => {
        if (token !== generation.current || !metadata.current.approved) return
        try {
          const result = await api.post(`/api/drafts/${kind}`, { content: JSON.parse(serialized),
            revision: metadata.current.revision, preference_revision: preferenceRevision })
          if (metadata.current.preferenceRevision === preferenceRevision) metadata.current.revision = result.revision
          if (token === generation.current) { lastSaved.current = serialized; setSavedContent(serialized); setStatus('saved') }
        } catch (error) {
          if (token === generation.current) {
            if (error.status === 409) metadata.current.approved = false
            setStatus(error.status === 409 ? 'conflict' : 'error')
          }
        }
      })
    }, 600)
    return () => clearTimeout(timer)
  }, [serialized, candidate, status === 'loading', status === 'conflict', attempt, kind])

  const clear = useCallback(async () => {
    if (!metadata.current.loaded) { setStatus('error'); return false }
    if (!metadata.current.enabled) return true
    if (!metadata.current.approved) return false
    const token = ++generation.current
    const preferenceRevision = metadata.current.preferenceRevision
    lastSaved.current = null
    setSavedContent(null)
    setStatus('deleting')
    let cleared = false
    const remove = queue.current.catch(() => {}).then(async () => {
      if (token !== generation.current || preferenceRevision !== metadata.current.preferenceRevision) return
      const result = await api.delete(`/api/drafts/${kind}?revision=${metadata.current.revision}&preference_revision=${preferenceRevision}`)
      cleared = true
      if (token === generation.current) { metadata.current.revision = result.revision; setStatus('ready') }
    })
    queue.current = remove.catch(() => { if (token === generation.current) setStatus('error') })
    await queue.current
    return cleared
  }, [kind])

  const recover = () => {
    if (!candidate) return
    if (restore.current(candidate.content) === false) { setStatus('error'); return }
    metadata.current.approved = true
    setCandidate(null); setStatus('ready')
  }
  const discard = async () => {
    const previousCandidate = candidate
    const expectedGeneration = generation.current + 1
    metadata.current.approved = true
    const cleared = await clear()
    if (generation.current !== expectedGeneration) return
    if (cleared) setCandidate(current => current === previousCandidate ? null : current)
    else metadata.current.approved = false
  }
  const visibleStatus = metadata.current.enabled && metadata.current.approved && !candidate
    && serialized !== savedContent && ['ready', 'saved'].includes(status) ? 'unsaved' : status
  return { candidate, status: visibleStatus, hasSavedDraft: savedContent !== null,
    recover, discard, clear, reload: () => setAttempt(value => value + 1) }
}
