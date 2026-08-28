import { Easing, interpolate } from 'remotion'

export type Intensity = 'subtle' | 'medium' | 'strong'

export interface PaletteColor {
  hex: string
  role: string
}

export interface SlideMotionSpec {
  animate: boolean
  mode: 'image' | 'vector'
  preset:
    | 'none'
    | 'kenburns'
    | 'fade_up'
    | 'typewriter'
    | 'pop'
    | 'parallax'
    | 'draw_in'
    | 'loop_pulse'
    | 'count_up'
  intensity: Intensity
  duration_seconds: number
  note: string
}

/** Position/size as percentages (0-100) of the 1080x1350 canvas. */
export interface ElementRect {
  x: number
  y: number
  w: number
  h: number
}

export interface TextStyle {
  font_size: number
  color: string
  weight: number
  align: 'left' | 'center' | 'right'
  font_family?: string
  line_height?: number | null
  letter_spacing?: number | null
}

export type ElementRole = 'h1' | 'text' | 'swipe_cue' | 'handle' | 'progress' | 'visual'

export type ElementType = 'text' | 'shape' | 'icon' | 'image' | 'video'
export type ShapeKind = 'rect' | 'ellipse' | 'line' | 'arrow'

export interface SlideElementProps {
  id: string
  type: ElementType
  role: ElementRole
  rect: ElementRect
  z_index: number
  content: string
  style: TextStyle
  // shape/icon blocks
  shape?: ShapeKind | null
  fill?: string | null
  stroke?: string | null
  stroke_width?: number
  corner_radius?: number
  icon_name?: string | null
  // image/video blocks
  media_url?: string | null
  fit?: 'cover' | 'contain'
  media_duration_seconds?: number | null
  // generic
  opacity?: number
  rotation?: number
}

export interface SlideMotionProps {
  index: number
  total: number
  role: string
  handle: string
  palette: PaletteColor[]
  typography: string
  iconStyle: string
  motionLanguage: string
  motion: SlideMotionSpec
  imageUrl: string | null
  /** Where the AI background image sits within the canvas; outside it shows
   * the palette's background color. */
  backgroundRect: ElementRect
  /** Independently positioned text/icon overlays, ordered by z_index. */
  elements: SlideElementProps[]
  fps: number
  // Remotion requires composition props to be index-signature compatible.
  [key: string]: unknown
}

/** Convert a percent-based ``ElementRect`` into absolute pixels for a canvas
 * of the given size. */
export function rectToPx(
  rect: ElementRect,
  canvasWidth: number,
  canvasHeight: number,
): { left: number; top: number; width: number; height: number } {
  return {
    left: (rect.x / 100) * canvasWidth,
    top: (rect.y / 100) * canvasHeight,
    width: (rect.w / 100) * canvasWidth,
    height: (rect.h / 100) * canvasHeight,
  }
}

/** Amplitude multiplier so the same preset can be subtle..strong. */
export function intensityFactor(intensity: Intensity): number {
  switch (intensity) {
    case 'strong':
      return 2.2
    case 'medium':
      return 1.5
    default:
      return 1
  }
}

export const EASE = Easing.bezier(0.22, 1, 0.36, 1)

/** Pick a palette color by (fuzzy) role, with a fallback. */
export function colorFor(
  palette: PaletteColor[],
  role: 'background' | 'accent' | 'text' | 'secondary',
  fallback: string,
): string {
  const want = role.toLowerCase()
  const hit = palette.find((c) => c.role.toLowerCase().includes(want))
  if (hit) return hit.hex
  // Reasonable fallbacks derived from common roles.
  if (role === 'text') {
    const t = palette.find((c) => c.role.toLowerCase().includes('text'))
    if (t) return t.hex
  }
  return fallback
}

/** Entrance progress 0..1 over the first `durationInFrames` frames. */
export function entrance(frame: number, fps: number, delaySec = 0, durSec = 0.6): number {
  return interpolate(frame, [delaySec * fps, (delaySec + durSec) * fps], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE,
  })
}

/** Loop-friendly 0..1..0 oscillation. */
export function pingPong(frame: number, durationInFrames: number): number {
  const t = (frame % durationInFrames) / durationInFrames
  return 0.5 - 0.5 * Math.cos(t * Math.PI * 2)
}

/** Extract the first integer found in a string (for count_up). */
export function firstNumber(text: string): { value: number; prefix: string; suffix: string } | null {
  const m = text.match(/(\d[\d.,]*)/)
  if (!m) return null
  const raw = m[1].replace(/[.,]/g, '')
  const value = parseInt(raw, 10)
  if (Number.isNaN(value)) return null
  return {
    value,
    prefix: text.slice(0, m.index ?? 0),
    suffix: text.slice((m.index ?? 0) + m[1].length),
  }
}
