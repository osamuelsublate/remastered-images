import { useEffect } from 'react'
import type { Dispatch, RefObject, SetStateAction } from 'react'
import { api } from '../api/carouselApi'
import type { CarouselState } from '../types'

/** Polls the carousel state every 2.5s while an image/video job is running. */
export function useCarouselPolling(
  state: CarouselState | null,
  setState: Dispatch<SetStateAction<CarouselState | null>>,
  idRef: RefObject<string | null>,
) {
  useEffect(() => {
    if (!idRef.current) return
    if (state?.status !== 'generating' && state?.status !== 'rendering') return
    const id = idRef.current
    const t = setInterval(async () => {
      try {
        setState(await api.getCarousel(id))
      } catch {
        /* keep polling */
      }
    }, 2500)
    return () => clearInterval(t)
  }, [state?.status])
}
