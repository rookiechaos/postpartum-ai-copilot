import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from './api'
import useConnection from './useConnection'

export const subjectsChanged = 'postpartum-care-subjects-changed'
export const journeysChanged = 'postpartum-support-journeys-changed'
const CareContext = createContext(null)

export function CareSessionProvider({ userId, children }) {
  const { reconnections } = useConnection()
  const [subjects, setSubjects] = useState([])
  const [activeId, setActiveId] = useState('')
  const [ready, setReady] = useState(false)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [work, setWorkState] = useState({})
  const reload = useCallback(() => setAttempt(value => value + 1), [])
  useEffect(() => {
    let active = true
    setError(false); setReady(false)
    api.get('/api/care-subjects').then(result => {
      if (!active) return
      setSubjects(result); setReady(true)
      setActiveId(previous => result.some(item => item.subject_id === previous) ? previous : '')
    }).catch(() => { if (active) { setError(true); setReady(false); setSubjects([]) } })
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
  return <CareContext.Provider value={{ userId, subjects, activeId, setActiveId, ready, error, reload, work, setWork }}>
    {children}
  </CareContext.Provider>
}

export function useCareSession() { return useContext(CareContext) }

export function useCareWork(key, value) {
  const { setWork } = useCareSession()
  const serialized = value ? JSON.stringify(value) : null
  useEffect(() => { setWork(key, serialized ? JSON.parse(serialized) : null) }, [key, serialized, setWork])
  useEffect(() => () => setWork(key, null), [key, setWork])
}
