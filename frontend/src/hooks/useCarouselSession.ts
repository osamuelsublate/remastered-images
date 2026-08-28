import { useCallback, useEffect, useRef, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { api } from '../api/carouselApi'
import type { CarouselState } from '../types'

/**
 * Owns the current carousel id/state: creates a session on first load (or
 * reopens one from the URL hash), keeps the URL in sync, and exposes
 * `ensureSession`/`reset` for the other hooks to call into.
 */
export function useCarouselSession(setError: Dispatch<SetStateAction<string | null>>) {
  const [state, setState] = useState<CarouselState | null>(null)
  const idRef = useRef<string | null>(null)

  const ensureSession = useCallback(async (): Promise<string> => {
    if (idRef.current) return idRef.current
    const s = await api.createCarousel()
    idRef.current = s.id
    setState(s)
    return s.id
  }, [])

  // On load: open an existing carousel from the URL (#/c/<id>) if present,
  // otherwise start a fresh session.
  useEffect(() => {
    const m = window.location.hash.match(/#\/c\/([A-Za-z0-9]+)/)
    if (m) {
      const id = m[1]
      idRef.current = id
      api
        .getCarousel(id)
        .then(setState)
        .catch(() => {
          idRef.current = null
          setError('Carrossel da URL não encontrado; iniciei um novo.')
          ensureSession().catch((e) => setError(String(e)))
        })
    } else {
      ensureSession().catch((e) => setError(String(e)))
    }
  }, [ensureSession, setError])

  // Keep the URL in sync so the carousel can be reopened/shared.
  useEffect(() => {
    if (state?.id) {
      const target = `#/c/${state.id}`
      if (window.location.hash !== target) window.location.hash = target
    }
  }, [state?.id])

  const reset = useCallback(async () => {
    idRef.current = null
    setState(null)
    setError(null)
    window.location.hash = ''
    try {
      await ensureSession()
    } catch (e) {
      setError(String(e))
    }
  }, [ensureSession, setError])

  return { state, setState, idRef, ensureSession, reset }
}
