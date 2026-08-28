import { useEffect, useRef, useState } from 'react'
import type { Dispatch, RefObject, SetStateAction } from 'react'
import { api } from '../api/carouselApi'
import type { CarouselState } from '../types'

/** Generating, regenerating, animating and exporting/downloading slides. */
export function useGeneration({
  state,
  idRef,
  setState,
  setError,
}: {
  state: CarouselState | null
  idRef: RefObject<string | null>
  setState: Dispatch<SetStateAction<CarouselState | null>>
  setError: Dispatch<SetStateAction<string | null>>
}) {
  const [genBusy, setGenBusy] = useState(false)

  const handleGenerate = async () => {
    if (!state?.plan || !idRef.current) return
    setError(null)
    setGenBusy(true)
    try {
      const next = await api.generate(idRef.current, state.plan, state.quality)
      setState({ ...next, status: 'generating' })
    } catch (e) {
      setError(String(e))
    } finally {
      setGenBusy(false)
    }
  }

  const handleRegenerate = async (indices: number[], instruction: string) => {
    if (!idRef.current) return
    setError(null)
    setGenBusy(true)
    try {
      const next = await api.regenerate(idRef.current, indices, instruction)
      setState({ ...next, status: 'generating' })
    } catch (e) {
      setError(String(e))
    } finally {
      setGenBusy(false)
    }
  }

  const handleAnimate = async (indices: number[]) => {
    if (!idRef.current) return
    setError(null)
    setGenBusy(true)
    try {
      const next = await api.animate(idRef.current, indices)
      setState({ ...next, status: 'rendering' })
    } catch (e) {
      setError(String(e))
    } finally {
      setGenBusy(false)
    }
  }

  // Download = export job (composited PNGs + MP4s) followed by the zip.
  // The polling hook tracks the job; when it finishes we fetch the zip.
  const downloadPendingRef = useRef(false)

  const handleDownload = async () => {
    if (!idRef.current) return
    setError(null)
    setGenBusy(true)
    try {
      const next = await api.exportCarousel(idRef.current)
      downloadPendingRef.current = true
      setState({ ...next, status: 'rendering' })
    } catch (e) {
      setError(String(e))
    } finally {
      setGenBusy(false)
    }
  }

  useEffect(() => {
    if (!downloadPendingRef.current || !idRef.current) return
    if (state?.status === 'rendering') return
    downloadPendingRef.current = false
    if (state?.status === 'error') {
      setError(state.error ?? 'Falha ao exportar o carrossel.')
      return
    }
    window.location.assign(api.downloadUrl(idRef.current))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.status])

  return { genBusy, handleGenerate, handleRegenerate, handleAnimate, handleDownload }
}
