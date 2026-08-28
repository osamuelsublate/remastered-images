export type SlideRole = 'hook' | 'context' | 'value' | 'proof' | 'cta'
export type SlideStatus = 'pending' | 'running' | 'done' | 'error'
export type MotionStatus = 'idle' | 'pending' | 'running' | 'done' | 'error'
export type CarouselStatus =
  | 'draft'
  | 'planned'
  | 'generating'
  | 'rendering'
  | 'done'
  | 'error'

export type MotionPreset =
  | 'none'
  | 'kenburns'
  | 'fade_up'
  | 'typewriter'
  | 'pop'
  | 'parallax'
  | 'draw_in'
  | 'loop_pulse'
  | 'count_up'

export interface SlideMotion {
  animate: boolean
  mode: 'image' | 'vector'
  preset: MotionPreset
  intensity: 'subtle' | 'medium' | 'strong'
  duration_seconds: number
  note: string
}

export type ElementRole = 'h1' | 'text' | 'swipe_cue' | 'handle' | 'progress' | 'visual'
export type ElementType = 'text' | 'shape' | 'icon' | 'image' | 'video'
export type ShapeKind = 'rect' | 'ellipse' | 'line' | 'arrow'

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
  font_family: string
  line_height?: number | null
  letter_spacing?: number | null
}

export interface SlideElement {
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

export interface PaletteColor {
  hex: string
  role: string
}

export interface ArtDirection {
  palette: PaletteColor[]
  typography: string
  font_family: string
  font_family_secondary: string
  icon_style: string
  layout: string
  logo_policy: string
  mood: string
  motion: string
}

export interface Slide {
  index: number
  role: SlideRole
  headline: string
  body: string
  visual_prompt: string
  swipe_cue: string
  motion: SlideMotion | null
  elements: SlideElement[]
  status: SlideStatus
  image_url: string | null
  background_rect: ElementRect
  error: string | null
  motion_status: MotionStatus
  video_url: string | null
  motion_error: string | null
  export_status: MotionStatus
  export_error: string | null
}

export interface CarouselPlan {
  title: string
  handle: string
  art_direction: ArtDirection
  caption: string
  hashtags: string[]
  slides: Slide[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface CarouselState {
  id: string
  brief: unknown | null
  plan: CarouselPlan | null
  references: string[]
  messages: ChatMessage[]
  status: CarouselStatus
  quality: string
  error: string | null
}
