import {
  AbsoluteFill,
  Img,
  Video,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  type CalculateMetadataFunction,
} from 'remotion'
import {
  colorFor,
  entrance,
  firstNumber,
  intensityFactor,
  pingPong,
  rectToPx,
  type ElementRect,
  type SlideElementProps,
  type SlideMotionProps,
} from './anim'
import { ensureFont } from './fonts'
import { BlockIcon } from './icons'

export const defaultSlideProps: SlideMotionProps = {
  index: 1,
  total: 1,
  role: 'hook',
  handle: '',
  palette: [
    { hex: '#0a0a0a', role: 'background' },
    { hex: '#ff6b1a', role: 'accent' },
    { hex: '#ffffff', role: 'text' },
  ],
  typography: 'bold condensed grotesque',
  iconStyle: 'monochrome line icons',
  motionLanguage: 'subtle, smooth ease-in-out, loopable',
  motion: {
    animate: true,
    mode: 'image',
    preset: 'kenburns',
    intensity: 'subtle',
    duration_seconds: 4,
    note: '',
  },
  imageUrl: null,
  backgroundRect: { x: 0, y: 0, w: 100, h: 100 },
  elements: [
    {
      id: 'demo-headline',
      type: 'text',
      role: 'h1',
      rect: { x: 8.9, y: 8, w: 82.2, h: 42 },
      z_index: 10,
      content: 'Headline',
      style: { font_size: 76, color: '#ffffff', weight: 800, align: 'left' },
    },
  ],
  fps: 30,
}

export const calculateSlideMetadata: CalculateMetadataFunction<SlideMotionProps> = ({
  props,
}) => {
  const fps = props.fps || 30
  // The clip must be at least as long as the longest user video block on
  // the slide, otherwise the exported MP4 would cut the clip short.
  const videoSeconds = Math.max(
    0,
    ...(props.elements || [])
      .filter((el) => el.type === 'video' && el.media_url)
      .map((el) => el.media_duration_seconds || 0),
  )
  const wanted = Math.max(props.motion?.duration_seconds || 4, videoSeconds)
  const seconds = Math.min(Math.max(wanted, 2), 30)
  return {
    durationInFrames: Math.round(seconds * fps),
    fps,
    width: 1080,
    height: 1350,
  }
}

/**
 * The single render engine for a layered slide: a positioned/sized
 * background image (``backgroundRect``) plus independently positioned
 * text/icon overlays (``elements``), ordered by ``z_index``. Used verbatim
 * by the in-browser editor (Player, frozen on a settled frame), the live
 * preview (Player, looping), and the server-side export (Remotion render).
 */
export const SlideMotion: React.FC<SlideMotionProps> = (props) => {
  const bg = colorFor(props.palette, 'background', '#0a0a0a')
  const elements = [...(props.elements || [])].sort((a, b) => a.z_index - b.z_index)

  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <BackgroundLayer {...props} />
      {elements.map((el) => (
        <ElementLayer key={el.id} element={el} slideIndex={props.index} motion={props.motion} fps={props.fps} />
      ))}
    </AbsoluteFill>
  )
}

/* -------------------------------------------------------------------------- */
/* Background: the AI-generated image, positioned/sized via backgroundRect     */
/* -------------------------------------------------------------------------- */

const BackgroundLayer: React.FC<SlideMotionProps> = (props) => {
  const frame = useCurrentFrame()
  const { width, height, durationInFrames } = useVideoConfig()
  const k = intensityFactor(props.motion.intensity)
  const p = frame / Math.max(durationInFrames - 1, 1)
  const box = rectToPx(props.backgroundRect, width, height)

  let transform = 'scale(1.02)'
  if (props.motion.preset === 'kenburns') {
    const scale = interpolate(p, [0, 1], [1.04, 1.04 + 0.08 * k])
    const ty = interpolate(p, [0, 1], [0, -2 * k])
    transform = `scale(${scale}) translateY(${ty}%)`
  } else if (props.motion.preset === 'parallax') {
    const ty = interpolate(p, [0, 1], [2 * k, -2 * k])
    transform = `scale(1.08) translateY(${ty}%)`
  } else if (props.motion.preset === 'pop') {
    const s = spring({ frame, fps: props.fps, config: { damping: 12 } })
    transform = `scale(${interpolate(s, [0, 1], [1.12, 1.0 + 0.02 * k])})`
  } else if (props.motion.preset === 'loop_pulse') {
    const pulse = 1 + 0.05 * k * pingPong(frame, durationInFrames)
    transform = `scale(${pulse})`
  } else if (props.motion.preset === 'draw_in') {
    const e = entrance(frame, props.fps, 0.05, 0.9)
    transform = `scale(${interpolate(e, [0, 1], [1.06, 1.0])})`
  }

  return (
    <div
      data-background-layer="1"
      style={{
        position: 'absolute',
        left: box.left,
        top: box.top,
        width: box.width,
        height: box.height,
        overflow: 'hidden',
      }}
    >
      {props.imageUrl ? (
        <Img
          src={props.imageUrl}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform,
            transformOrigin: 'center',
          }}
        />
      ) : (
        <AbsoluteFill
          style={{
            border: '2px dashed rgba(255,255,255,0.18)',
          }}
        />
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Overlay elements: text/icon layers positioned independently of the bg      */
/* -------------------------------------------------------------------------- */

// Only "h1" remains as a heading-styled role now that h2/h3/body/caption
// collapsed into the generic "text" role.
const isH1 = (role: string) => role === 'h1'

const ElementLayer: React.FC<{
  element: SlideElementProps
  slideIndex: number
  motion: SlideMotionProps['motion']
  fps: number
}> = ({ element, motion, fps }) => {
  const frame = useCurrentFrame()
  const { width, height } = useVideoConfig()
  const box = rectToPx(element.rect, width, height)

  // Baseline entrance so every layout feels intentional even without a
  // dedicated preset; staggered a touch by z_index so text doesn't all pop
  // in at once.
  const delay = 0.1 + Math.min(element.z_index, 10) * 0.01
  const baseline = entrance(frame, fps, delay, 0.6)

  let opacity = baseline
  let translateY = (1 - baseline) * 24
  let content = element.content

  if (motion.preset === 'fade_up') {
    const e = entrance(frame, fps, delay + 0.05, 0.7)
    opacity = e
    translateY = (1 - e) * 28
  } else if (motion.preset === 'typewriter' && isH1(element.role)) {
    const e = entrance(frame, fps, 0.1, 1.2)
    content = element.content.slice(0, Math.floor(element.content.length * e))
    opacity = 1
    translateY = 0
  } else if (motion.preset === 'count_up' && isH1(element.role)) {
    const num = firstNumber(element.content)
    if (num) {
      const e = entrance(frame, fps, 0.2, 1.1)
      content = `${num.prefix}${Math.round(num.value * e)}${num.suffix}`
    }
    opacity = baseline
  }

  if (!content && element.type === 'text') return null

  opacity *= element.opacity ?? 1

  const rotation = element.rotation || 0
  const wrapperStyle: React.CSSProperties = {
    position: 'absolute',
    left: box.left,
    top: box.top,
    width: box.width,
    height: box.height,
    opacity,
    transform:
      `translateY(${translateY}px)` + (rotation ? ` rotate(${rotation}deg)` : ''),
  }

  if (element.type === 'shape') {
    return (
      <div data-element-id={element.id} data-element-role={element.role} style={wrapperStyle}>
        <ShapeBlock element={element} boxWidth={box.width} boxHeight={box.height} />
      </div>
    )
  }

  if (element.type === 'icon') {
    return (
      <div data-element-id={element.id} data-element-role={element.role} style={wrapperStyle}>
        <BlockIcon
          name={element.icon_name || 'sparkles'}
          color={element.fill || element.style.color}
        />
      </div>
    )
  }

  if (element.type === 'image' || element.type === 'video') {
    if (!element.media_url) return null
    const mediaStyle: React.CSSProperties = {
      width: '100%',
      height: '100%',
      objectFit: element.fit || 'cover',
    }
    return (
      <div
        data-element-id={element.id}
        data-element-role={element.role}
        style={{ ...wrapperStyle, overflow: 'hidden' }}
      >
        {element.type === 'image' ? (
          <Img src={element.media_url} style={mediaStyle} />
        ) : (
          // <Video> plays inline in the Player and is frame-synced during
          // the server-side render — same WYSIWYG contract as the rest of
          // the composition. Loops if the slide outlasts the clip.
          <Video src={element.media_url} muted loop style={mediaStyle} />
        )}
      </div>
    )
  }

  return (
    <div
      data-element-id={element.id}
      data-element-role={element.role}
      style={{
        ...wrapperStyle,
        display: 'flex',
        // Top-aligned so the rect can shrink-wrap the text: the editor
        // auto-fits rect.h to the rendered content height, making the
        // selection border hug the block exactly.
        alignItems: 'flex-start',
        justifyContent:
          element.style.align === 'center'
            ? 'center'
            : element.style.align === 'right'
              ? 'flex-end'
              : 'flex-start',
      }}
    >
      <div
        data-element-content="1"
        style={{
          color: element.style.color,
          fontSize: element.style.font_size,
          fontWeight: element.style.weight,
          fontFamily: ensureFont(element.style.font_family),
          textAlign: element.style.align,
          lineHeight: element.style.line_height ?? (isH1(element.role) ? 1.04 : 1.3),
          letterSpacing:
            element.style.letter_spacing ?? (isH1(element.role) ? -1 : undefined),
          whiteSpace: 'pre-wrap',
          width: '100%',
        }}
      >
        {content}
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Shape blocks: rect / ellipse / line / arrow                                 */
/* -------------------------------------------------------------------------- */

const ShapeBlock: React.FC<{
  element: SlideElementProps
  boxWidth: number
  boxHeight: number
}> = ({ element, boxWidth, boxHeight }) => {
  const fill = element.fill || element.style.color
  const stroke = element.stroke || undefined
  const strokeWidth = element.stroke_width || 0

  if (element.shape === 'line' || element.shape === 'arrow') {
    const thickness = Math.max(strokeWidth || 4, 2)
    const midY = boxHeight / 2
    return (
      <svg width="100%" height="100%" viewBox={`0 0 ${boxWidth} ${boxHeight}`}>
        <line
          x1={0}
          y1={midY}
          x2={element.shape === 'arrow' ? boxWidth - thickness * 3 : boxWidth}
          y2={midY}
          stroke={fill}
          strokeWidth={thickness}
          strokeLinecap="round"
        />
        {element.shape === 'arrow' && (
          <path
            d={`M ${boxWidth - thickness * 4} ${midY - thickness * 2.2} L ${boxWidth} ${midY} L ${boxWidth - thickness * 4} ${midY + thickness * 2.2}`}
            fill="none"
            stroke={fill}
            strokeWidth={thickness}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
      </svg>
    )
  }

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: fill,
        borderRadius:
          element.shape === 'ellipse' ? '50%' : (element.corner_radius ?? 0),
        border: stroke && strokeWidth ? `${strokeWidth}px solid ${stroke}` : undefined,
      }}
    />
  )
}

/** Exported so the editor canvas can compute selection handles from the same
 * rect math the renderer itself uses. */
export function elementBoxPx(rect: ElementRect, canvasWidth: number, canvasHeight: number) {
  return rectToPx(rect, canvasWidth, canvasHeight)
}
