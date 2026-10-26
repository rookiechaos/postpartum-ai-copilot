import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from './api'
import useConnection from './useConnection'

export const subjectsChanged = 'postpartum-care-subjects-changed'
export const journeysChanged = 'postpartum-support-journeys-changed'
const CareContext = createContext(null)

export function CareSessionProvider({ userId, children }) {
  const { reconnections } = useConnection()
  const [subjects, setSubjects] = useState([])
  const [adultSharing, setAdultSharing] = useState(null)
  const [activeId, setActiveId] = useState('')
  const [recentSubjectId, setRecentSubjectId] = useState('')
  const rememberSubject = useCallback(id => setRecentSubjectId(id || ''), [])
  const [ready, setReady] = useState(false)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [work, setWorkState] = useState({})
  const reload = useCallback(() => setAttempt(value => value + 1), [])
  useEffect(() => {
    let active = true
    setError(false); setReady(false); setAdultSharing(null)
    Promise.allSettled([api.get('/api/care-subjects'), api.get('/api/care-subjects/visibility')]).then(([result, visibility]) => {
      if (!active) return
      if (visibility.status === 'fulfilled') setAdultSharing(visibility.value.adult_shared_with)
      if (result.status === 'fulfilled') {
        setSubjects(result.value); setReady(true)
        setActiveId(previous => result.value.some(item => item.subject_id === previous) ? previous : '')
      } else { setError(true); setReady(false); setSubjects([]) }
    })
    return () => { active = false }
  }, [userId, reconnections, attempt])
  useEffect(() => {
    window.addEventListener('focus', reload); window.addEventListener(subjectsChanged, reload)
    return () => { window.removeEventListener('focus', reload); window.removeEventListener(subjectsChanged, reload) }
  }, [reload])
  const setWork = useCallback((key, value) => setWorkState(previous => {
    if (JSON.stringify(previous[key] ?? null) === JSON.stringify(value)) return previous
    const next = { ...previous }
    if (value) next[key] = value
    else delete next[key]
    return next
  }), [])
  return <CareContext.Provider value={{ userId, subjects, adultSharing, activeId, setActiveId, recentSubjectId, rememberSubject, ready, error, reload, work, setWork }}>
    {children}
  </CareContext.Provider>
}

export function useCareSession() { return useContext(CareContext) }

export function useCareWork(key, value) {
  // Public previews and institution contact cards share some family components.
  // They have no care session and must never register private family work.
  const setWork = useCareSession()?.setWork
  const serialized = value ? JSON.stringify(value) : null
  useEffect(() => { setWork?.(key, serialized ? JSON.parse(serialized) : null) }, [key, serialized, setWork])
  useEffect(() => () => setWork?.(key, null), [key, setWork])
}
