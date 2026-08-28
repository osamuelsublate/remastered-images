import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/carouselApi'
import type {
  CarouselState,
  ElementRect,
  ElementRole,
  Slide,
  SlideElement,
  TextStyle,
} from '../types'

const SAVE_DEBOUNCE_MS = 500

/** Read a video file's duration (seconds) from its metadata, client-side. */
function probeVideoDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url)
      resolve(Number.isFinite(video.duration) ? video.duration : null)
    }
    video.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(null)
    }
    video.src = url
  })
}

const TEXT_DEFAULTS: Record<string, { font_size: number; weight: number }> = {
  h1: { font_size: 64, weight: 800 },
  text: { font_size: 30, weight: 500 },
}

/** Sentinel `selectedId` value meaning "the background image box is selected"
 * (as opposed to one of the text/icon overlay elements). */
export const BACKGROUND_SELECTION = 'background'

/**
 * Optimistic editing state for one slide's layout: local copies of
 * `elements`/`background_rect` that update instantly on drag/resize/style
 * edits, with the actual persistence (`PATCH .../layout`) debounced so we
 * don't spam the API on every mousemove.
 */
export function useSlideEditor(
  carouselId: string,
  slide: Slide,
  onSaved: (state: CarouselState) => void,
  options: { textColor?: string; fontFamily?: string; bodyFontFamily?: string } = {},
) {
  const [elements, setElements] = useState<SlideElement[]>(slide.elements)
  const [backgroundRect, setBackgroundRect] = useState<ElementRect>(slide.background_rect)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Reset local optimistic state only when switching to a different slide —
  // not on every parent re-render, so our own optimistic edits don't get
  // clobbered by the (slightly stale) prop while a save is in flight.
  useEffect(() => {
    setElements(slide.elements)
    setBackgroundRect(slide.background_rect)
    setSelectedId(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slide.index])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const scheduleSave = useCallback(
    (patch: { background_rect?: ElementRect; elements?: SlideElement[] }) => {
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(async () => {
        setSaving(true)
        try {
          const state = await api.updateSlideLayout(carouselId, slide.index, patch)
          onSaved(state)
        } catch {
          /* keep the optimistic local state; user can retry the edit */
        } finally {
          setSaving(false)
        }
      }, SAVE_DEBOUNCE_MS)
    },
    [carouselId, slide.index, onSaved],
  )

  const updateElementRect = useCallback(
    (id: string, rect: ElementRect) => {
      setElements((prev) => {
        const next = prev.map((el) => (el.id === id ? { ...el, rect } : el))
        scheduleSave({ elements: next })
        return next
      })
    },
    [scheduleSave],
  )

  const updateElementStyle = useCallback(
    (id: string, patch: Partial<TextStyle>) => {
      setElements((prev) => {
        const next = prev.map((el) =>
          el.id === id ? { ...el, style: { ...el.style, ...patch } } : el,
        )
        scheduleSave({ elements: next })
        return next
      })
    },
    [scheduleSave],
  )

  const updateElementContent = useCallback(
    (id: string, content: string) => {
      setElements((prev) => {
        const next = prev.map((el) => (el.id === id ? { ...el, content } : el))
        scheduleSave({ elements: next })
        return next
      })
    },
    [scheduleSave],
  )

  /** Generic patch for non-style block fields (shape, fill, fit, opacity...). */
  const updateElementProps = useCallback(
    (id: string, patch: Partial<SlideElement>) => {
      setElements((prev) => {
        const next = prev.map((el) => (el.id === id ? { ...el, ...patch } : el))
        scheduleSave({ elements: next })
        return next
      })
    },
    [scheduleSave],
  )

  const addElement = useCallback(
    (partial: Partial<SlideElement> & { type: SlideElement['type']; role: ElementRole }) => {
      const id = `u${Date.now().toString(36)}`
      const textDefaults = TEXT_DEFAULTS[partial.role] ?? TEXT_DEFAULTS.text
      const element: SlideElement = {
        id,
        z_index: 12,
        content: '',
        rect: { x: 20, y: 40, w: 60, h: 10 },
        style: {
          font_size: textDefaults.font_size,
          color: options.textColor ?? '#ffffff',
          weight: textDefaults.weight,
          align: 'left',
          font_family:
            (partial.role === 'h1' ? options.fontFamily : options.bodyFontFamily) ??
            options.fontFamily ??
            'Inter',
        },
        opacity: 1,
        ...partial,
      }
      setElements((prev) => {
        const next = [...prev, element]
        scheduleSave({ elements: next })
        return next
      })
      setSelectedId(id)
      return element
    },
    [scheduleSave, options.textColor, options.fontFamily, options.bodyFontFamily],
  )

  const removeElement = useCallback(
    (id: string) => {
      setElements((prev) => {
        const next = prev.filter((el) => el.id !== id)
        scheduleSave({ elements: next })
        return next
      })
      setSelectedId((cur) => (cur === id ? null : cur))
    },
    [scheduleSave],
  )

  /** Upload a user image/video and insert it as a new block. */
  const addMediaElement = useCallback(
    async (file: File) => {
      setSaving(true)
      try {
        const { url, kind } = await api.uploadMedia(carouselId, file)
        const duration = kind === 'video' ? await probeVideoDuration(file) : null
        addElement({
          type: kind,
          role: 'visual',
          media_url: url,
          fit: 'cover',
          media_duration_seconds: duration,
          rect: { x: 25, y: 30, w: 50, h: 40 },
        })
      } finally {
        setSaving(false)
      }
    },
    [carouselId, addElement],
  )

  /** "Criar imagem": generate an isolated transparent asset via the AI asset
   * agent and insert it as an image block. `fit: 'contain'` (unlike the
   * `cover` used for user uploads) so a generated icon/illustration is never
   * cropped. */
  const generateImageElement = useCallback(
    async (prompt: string) => {
      setSaving(true)
      try {
        const { url } = await api.generateBlockImage(carouselId, slide.index, prompt)
        addElement({
          type: 'image',
          role: 'visual',
          media_url: url,
          fit: 'contain',
          rect: { x: 30, y: 30, w: 40, h: 40 },
        })
      } finally {
        setSaving(false)
      }
    },
    [carouselId, slide.index, addElement],
  )

  const updateBackgroundRect = useCallback(
    (rect: ElementRect) => {
      setBackgroundRect(rect)
      scheduleSave({ background_rect: rect })
    },
    [scheduleSave],
  )

  const replaceBackgroundImage = useCallback(
    async (file: File) => {
      setSaving(true)
      try {
        const state = await api.replaceSlideImage(carouselId, slide.index, file)
        onSaved(state)
      } finally {
        setSaving(false)
      }
    },
    [carouselId, slide.index, onSaved],
  )

  const regenerateBackground = useCallback(
    async (instruction: string) => {
      setSaving(true)
      try {
        const state = await api.regenerate(carouselId, [slide.index], instruction)
        onSaved(state)
      } finally {
        setSaving(false)
      }
    },
    [carouselId, slide.index, onSaved],
  )

  return {
    elements,
    backgroundRect,
    selectedId,
    select: setSelectedId,
    saving,
    updateElementRect,
    updateElementStyle,
    updateElementContent,
    updateElementProps,
    addElement,
    removeElement,
    addMediaElement,
    generateImageElement,
    updateBackgroundRect,
    replaceBackgroundImage,
    regenerateBackground,
  }
}
