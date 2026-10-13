import { useCallback, useEffect, useRef, useState } from 'react'

const stateKey = 'postpartumNavigation'
const entrance = pathname => ({ '/family': 'family', '/organization': 'organization', '/operator': 'operator' })[pathname] || null
const currentUrl = () => window.location.pathname + window.location.search + window.location.hash
const newSession = () => `${Date.now()}:${Math.random()}`
const marker = state => {
  const value = state?.[stateKey]
  return value && typeof value.session === 'string' && Number.isSafeInteger(value.index) ? value : null
}

export default function useEntranceNavigation() {
  const [entry, setEntry] = useState(() => entrance(window.location.pathname))
  const position = useRef(null)
  const leaveGuard = useRef(null)
  const restoring = useRef(false)

  const commitPosition = useCallback(() => {
    let saved = marker(window.history.state)
    if (!saved) {
      saved = { session: newSession(), index: 0 }
      window.history.replaceState({ ...window.history.state, [stateKey]: saved }, '', currentUrl())
    }
    position.current = { ...saved, url: currentUrl(), state: window.history.state }
    setEntry(entrance(window.location.pathname))
  }, [])

  useEffect(() => {
    commitPosition()
    const restorePosition = () => {
      const previous = position.current
      const target = marker(window.history.state)
      if (target?.session === previous.session && target.index !== previous.index) {
        restoring.current = true
        window.history.go(previous.index - target.index)
      } else {
        // Older/untracked history has no distance to traverse. Re-anchor without losing the draft.
        const saved = { session: newSession(), index: 0 }
        const state = { ...previous.state, [stateKey]: saved }
        window.history.pushState(state, '', previous.url)
        position.current = { ...saved, state, url: previous.url }
        restoring.current = false
      }
    }
    const onPopState = () => {
      const previous = position.current
      const target = marker(window.history.state)
      if (restoring.current) {
        if (target?.session === previous.session && target.index === previous.index && currentUrl() === previous.url) {
          restoring.current = false
        } else restorePosition()
        return
      }
      // A pop has already changed the URL. Keep the current component until the guard accepts it.
      if (entrance(window.location.pathname) !== entrance(new URL(previous.url, window.location.origin).pathname)
        && leaveGuard.current && !leaveGuard.current()) {
        restorePosition()
        return
      }
      commitPosition()
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [commitPosition])

  const navigate = useCallback(value => {
    if (restoring.current) return
    const url = value ? `/${value}` : '/'
    if (url === window.location.pathname) return
    if (leaveGuard.current && !leaveGuard.current()) return
    const previous = position.current
    const saved = { session: previous.session, index: previous.index + 1 }
    window.history.pushState({ [stateKey]: saved }, '', url)
    commitPosition()
  }, [commitPosition])

  const registerLeaveGuard = useCallback(guard => {
    leaveGuard.current = guard
    return () => { if (leaveGuard.current === guard) leaveGuard.current = null }
  }, [])
  const clearLeaveGuard = useCallback(() => { leaveGuard.current = null }, [])
  return { entry, navigate, registerLeaveGuard, clearLeaveGuard }
}
