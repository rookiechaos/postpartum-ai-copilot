import { useEffect, useState } from 'react'

export default function useConnection() {
  const [online, setOnline] = useState(() => navigator.onLine !== false)
  const [reconnections, setReconnections] = useState(0)
  useEffect(() => {
    const restored = () => { setOnline(true); setReconnections(value => value + 1) }
    const lost = () => setOnline(false)
    window.addEventListener('online', restored)
    window.addEventListener('offline', lost)
    return () => { window.removeEventListener('online', restored); window.removeEventListener('offline', lost) }
  }, [])
  return { online, reconnections }
}
