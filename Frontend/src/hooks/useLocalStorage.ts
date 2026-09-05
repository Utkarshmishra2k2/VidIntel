import { useEffect, useState } from 'react'

/**
 * Persists state to localStorage so a user's analyzed resource and chat
 * history survive a page refresh. This is a standalone browser app the
 * user runs themselves (not a sandboxed artifact), so normal localStorage
 * usage is appropriate here — this is what "session handling" means for a
 * tool with no accounts or backend database.
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = window.localStorage.getItem(key)
      return stored ? (JSON.parse(stored) as T) : initialValue
    } catch {
      return initialValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // storage full or unavailable (e.g. private browsing) — fail silently,
      // the app still works without persistence
    }
  }, [key, value])

  return [value, setValue]
}
