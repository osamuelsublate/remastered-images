import { useEffect, useRef, useState } from 'react'
import { Player } from '@remotion/player'
import Moveable from 'react-moveable'
import { SlideMotion } from '@motion/SlideMotion'
import type { SlideMotionProps } from '@motion/anim'
import type { CarouselPlan, ElementRect, Slide, SlideElement } from '../../types'
import { BACKGROUND_SELECTION } from '../../hooks/useSlideEditor'

const CANVAS_W = 1080
const CANVAS_H = 1350
const FPS = 30

function boxToRect(box: DOMRect, container: DOMRect): ElementRect {
  return {
    x: ((box.left - container.left) / container.width) * 100,
    y: ((box.top - container.top) / container.height) * 100,
    w: (box.width / container.width) * 100,
    h: (box.height / container.height) * 100,
  }
}

/**
 * The editor's live view: `SlideMotion` frozen on a settled frame (entrance
 * animations finished) rendered via `@remotion/player`, with `react-moveable`
 * overlaid on the selected DOM node (background box or one block) for
 * drag/resize. Clicking any block (or the background) selects it — the
 * same `SlideMotion` DOM is what gets exported, so what you see here is
 * exactly what renders.
 *
 * Text blocks shrink-wrap: their rect height is auto-fitted to the rendered
 * content, so the selection border hugs the block's exact bounds.
 */
export function SlideEditorCanvas({
  plan,
  slide,
  total,
  elements,
  backgroundRect,
  selectedId,
  onSelect,
  onCommitElementRect,
  onCommitBackgroundRect,
}: {
  plan: CarouselPlan
  slide: Slide
  total: number
  elements: SlideElement[]
  backgroundRect: ElementRect
  selectedId: string | null
  onSelect: (id: string | null) => void
  onCommitElementRect: (id: string, rect: ElementRect) => void
  onCommitBackgroundRect: (rect: ElementRect) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const moveableRef = useRef<Moveable>(null)
  const [targetEl, setTargetEl] = useState<HTMLElement | null>(null)

  const durationInFrames = Math.max(1, Math.round((slide.motion?.duration_seconds ?? 4) * FPS))

  const selectedElement =
    selectedId && selectedId !== BACKGROUND_SELECTION
      ? elements.find((e) => e.id === selectedId) ?? null
      : null
  const isTextSelected = selectedElement?.type === 'text'

  const inputProps: SlideMotionProps = {
    index: slide.index,
    total,
    role: slide.role,
    handle: plan.handle,
    palette: plan.art_direction.palette,
    typography: plan.art_direction.typography,
    iconStyle: plan.art_direction.icon_style,
    motionLanguage: plan.art_direction.motion,
    // Frozen preview: no entrance/preset animation while editing, so
    // elements sit exactly where their rect says.
    motion: { animate: false, mode: 'image', preset: 'none', intensity: 'subtle', duration_seconds: 4, note: '' },
    imageUrl: slide.image_url,
    backgroundRect,
    elements,
    fps: FPS,
  }

  useEffect(() => {
    const root = containerRef.current
    if (!root || !selectedId) {
      setTargetEl(null)
      return
    }
    const selector =
      selectedId === BACKGROUND_SELECTION
        ? '[data-background-layer="1"]'
        : `[data-element-id="${selectedId}"]`
    setTargetEl(root.querySelector<HTMLElement>(selector))
  }, [selectedId, elements, backgroundRect])

  // Keep the selection frame glued to the block after external rect changes
  // (properties panel edits, auto-fit) — Moveable doesn't watch DOM layout.
  useEffect(() => {
    moveableRef.current?.updateRect()
  }, [elements, backgroundRect, targetEl])

  // Shrink-wrap text blocks: fit rect.h to the actual rendered content so the
  // selection border sits exactly on the block's domain — no more, no less.
  // Measured on the next frame because the Player renders the composition in
  // its own React root, which may commit after ours.
  useEffect(() => {
    if (!targetEl || !selectedElement || selectedElement.type !== 'text') return
    const raf = requestAnimationFrame(() => {
      const container = containerRef.current?.getBoundingClientRect()
      const content = targetEl.querySelector<HTMLElement>('[data-element-content]')
      if (!container || !content) return
      const h = (content.getBoundingClientRect().height / container.height) * 100
      if (h > 0.5 && Math.abs(h - selectedElement.rect.h) > 0.4) {
        onCommitElementRect(selectedElement.id, { ...selectedElement.rect, h })
      }
      moveableRef.current?.updateRect()
    })
    return () => cancelAnimationFrame(raf)
  }, [targetEl, selectedElement, onCommitElementRect])

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement
    const elHit = target.closest<HTMLElement>('[data-element-id]')
    if (elHit) {
      onSelect(elHit.dataset.elementId ?? null)
      return
    }
    if (target.closest('[data-background-layer]')) {
      onSelect(BACKGROUND_SELECTION)
      return
    }
    onSelect(null)
  }

  const commit = (target: HTMLElement | SVGElement) => {
    const container = containerRef.current?.getBoundingClientRect()
    if (!container) return
    const rect = boxToRect(target.getBoundingClientRect(), container)
    if (isTextSelected) {
      // Height follows the content, not the drag handles.
      const content = target.querySelector<HTMLElement>('[data-element-content]')
      if (content) {
        rect.h = (content.getBoundingClientRect().height / container.height) * 100
      }
    }
    target.style.transform = ''
    if (selectedId === BACKGROUND_SELECTION) onCommitBackgroundRect(rect)
    else if (selectedId) onCommitElementRect(selectedId, rect)
  }

  return (
    <div className="mx-auto w-full max-w-md">
      <div
        ref={containerRef}
        onClick={handleClick}
        className="relative aspect-[4/5] w-full select-none overflow-hidden rounded-lg bg-black"
      >
        <Player
          component={SlideMotion}
          inputProps={inputProps}
          durationInFrames={durationInFrames}
          initialFrame={Math.max(0, durationInFrames - 1)}
          fps={FPS}
          compositionWidth={CANVAS_W}
          compositionHeight={CANVAS_H}
          style={{ width: '100%', height: '100%' }}
          controls={false}
          clickToPlay={false}
          doubleClickToFullscreen={false}
          allowFullscreen={false}
        />
        {targetEl && (
          <Moveable
            ref={moveableRef}
            target={targetEl}
            container={containerRef.current}
            draggable
            resizable
            keepRatio={false}
            // Text height is content-driven (shrink-wrap), so only expose
            // horizontal handles for text blocks.
            renderDirections={
              isTextSelected ? ['w', 'e'] : ['nw', 'n', 'ne', 'w', 'e', 'sw', 's', 'se']
            }
            throttleDrag={0}
            throttleResize={0}
            onDrag={({ target, transform }) => {
              target.style.transform = transform
            }}
            onDragEnd={({ target }) => commit(target)}
            onResize={({ target, width, height, drag }) => {
              target.style.width = `${width}px`
              if (!isTextSelected) target.style.height = `${height}px`
              target.style.transform = drag.transform
            }}
            onResizeEnd={({ target }) => commit(target)}
          />
        )}
      </div>
      <p className="mt-2 text-center text-xs text-fg-subtle">
        Clique em um bloco ou no fundo para selecionar; arraste as bordas para redimensionar.
      </p>
    </div>
  )
}
