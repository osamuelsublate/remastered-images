import { useState } from 'react'
import { Player, Thumbnail } from '@remotion/player'
import { SlideMotion } from '@motion/SlideMotion'
import type { SlideMotionProps } from '@motion/anim'
import type { CarouselPlan, CarouselState, CarouselStatus, Slide, SlideRole } from '../types'
import { Badge, Button, ProgressBar, Spinner, TextArea } from './ui'
import { SlideEditorModal } from './SlideEditor/SlideEditorModal'
import {
  AlertTriangle,
  Check,
  Download,
  Pause,
  Pencil,
  Play,
  Refresh,
  Sparkles,
  Video,
} from './icons'

const ROLE_TONE: Record<SlideRole, 'default' | 'accent' | 'ok' | 'err' | 'run'> = {
  hook: 'accent',
  context: 'default',
  value: 'default',
  proof: 'default',
  cta: 'accent',
}

const FPS = 30
// Frozen thumbnails only need enough frames for entrance animations to
// settle; 4s at 30fps matches the frozen `motion.duration_seconds`.
const THUMB_DURATION = 4 * FPS

const QUALITY_OPTIONS = [
  { value: 'low', label: 'Baixa' },
  { value: 'medium', label: 'Média' },
  { value: 'high', label: 'Alta' },
] as const

function motionProps(
  plan: CarouselPlan,
  slide: Slide,
  total: number,
  { frozen = false }: { frozen?: boolean } = {},
): SlideMotionProps {
  return {
    index: slide.index,
    total,
    role: slide.role,
    handle: plan.handle,
    palette: plan.art_direction.palette,
    typography: plan.art_direction.typography,
    iconStyle: plan.art_direction.icon_style,
    motionLanguage: plan.art_direction.motion,
    motion:
      !frozen && slide.motion
        ? slide.motion
        : {
            animate: false,
            mode: 'image',
            preset: 'none',
            intensity: 'subtle',
            duration_seconds: 4,
            note: '',
          },
    imageUrl: slide.image_url,
    backgroundRect: slide.background_rect,
    elements: slide.elements,
    fps: FPS,
  }
}

export function PreviewPanel({
  plan,
  status,
  busy,
  quality,
  carouselId,
  onGenerate,
  onRegenerate,
  onAnimate,
  onDownload,
  onQualityChange,
  onCarouselUpdate,
}: {
  plan: CarouselPlan
  status: CarouselStatus
  busy: boolean
  quality: string
  carouselId: string
  onGenerate: () => void
  onRegenerate: (indices: number[], instruction: string) => void
  onAnimate: (indices: number[]) => void
  onDownload: () => void
  onQualityChange: (quality: string) => void
  onCarouselUpdate: (state: CarouselState) => void
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [instruction, setInstruction] = useState('')
  const [preview, setPreview] = useState<Set<number>>(new Set())
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  const total = plan.slides.length
  const done = plan.slides.filter((s) => s.status === 'done').length
  const generating = status === 'generating'
  const rendering = status === 'rendering'
  const busyState = generating || rendering
  const anyImage = plan.slides.some((s) => s.image_url)
  const animatable = plan.slides.filter((s) => s.motion?.animate)
  const motionTracked = plan.slides.filter((s) => s.motion_status && s.motion_status !== 'idle')
  const motionDone = motionTracked.filter((s) => s.motion_status === 'done').length
  const exportTracked = plan.slides.filter(
    (s) => s.export_status === 'pending' || s.export_status === 'running',
  )
  const exporting = rendering && exportTracked.length > 0
  const exportDone = plan.slides.filter((s) => s.export_status === 'done').length
  const percent = total ? Math.round((done / total) * 100) : 0
  const motionPercent = motionTracked.length
    ? Math.round((motionDone / motionTracked.length) * 100)
    : 0
  const exportPercent = total ? Math.round((exportDone / total) * 100) : 0

  const toggle = (index: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const togglePreview = (index: number) => {
    setPreview((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const runRegen = () => {
    if (!selected.size) return
    onRegenerate([...selected].sort((a, b) => a - b), instruction.trim())
    setInstruction('')
    setSelected(new Set())
  }

  const animateSelected = () => {
    const idx = [...selected].filter(
      (i) => plan.slides[i - 1]?.motion?.animate,
    )
    if (!idx.length) return
    onAnimate(idx.sort((a, b) => a - b))
    setSelected(new Set())
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-line bg-surface">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 border-b border-line px-4 py-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-fg">{plan.title}</h3>
          <div className="mt-1 flex items-center gap-2">
            {plan.art_direction.palette.slice(0, 5).map((c, i) => (
              <span
                key={i}
                title={`${c.hex} · ${c.role}`}
                className="size-3.5 rounded-full ring-1 ring-white/15"
                style={{ backgroundColor: c.hex }}
              />
            ))}
            {plan.handle && <span className="text-xs text-fg-subtle">{plan.handle}</span>}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {anyImage && (
            <Button
              variant="secondary"
              onClick={onDownload}
              disabled={busy || busyState}
              loading={exporting}
              iconLeft={!exporting ? <Download size={16} /> : undefined}
            >
              {exporting ? 'exportando…' : 'Baixar .zip'}
            </Button>
          )}
          {anyImage && animatable.length > 0 && (
            <Button
              variant="secondary"
              onClick={() => onAnimate([])}
              disabled={busy || busyState}
              loading={rendering}
              iconLeft={!rendering ? <Video size={16} /> : undefined}
            >
              {rendering ? 'renderizando…' : `Renderizar vídeos (${animatable.length})`}
            </Button>
          )}
          {!anyImage && (
            <div
              role="radiogroup"
              aria-label="Qualidade da imagem"
              className="inline-flex items-center rounded-lg border border-line bg-surface-2 p-0.5"
            >
              {QUALITY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={quality === opt.value}
                  title={`Qualidade ${opt.label.toLowerCase()}`}
                  onClick={() => onQualityChange(opt.value)}
                  disabled={busy || busyState}
                  className={
                    'rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 disabled:pointer-events-none ' +
                    (quality === opt.value
                      ? 'bg-primary text-black'
                      : 'text-fg-muted hover:text-fg')
                  }
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
          {anyImage ? (
            <Button
              variant="secondary"
              onClick={onGenerate}
              disabled={busy || busyState}
              loading={generating}
              iconLeft={!generating ? <Refresh size={16} /> : undefined}
            >
              {generating ? 'gerando…' : 'Gerar tudo de novo'}
            </Button>
          ) : (
            <Button
              onClick={onGenerate}
              disabled={busy || busyState}
              loading={generating}
              iconLeft={!generating ? <Sparkles size={16} /> : undefined}
            >
              {generating ? 'gerando…' : 'Gerar carrossel'}
            </Button>
          )}
        </div>
      </div>

      {/* Progress bars */}
      {(generating || (anyImage && done < total)) && (
        <ProgressBar label={`${done}/${total} slides`} percent={percent} />
      )}
      {rendering && exporting && (
        <ProgressBar label={`exportando slides ${exportDone}/${total}`} percent={exportPercent} />
      )}
      {rendering && !exporting && (
        <ProgressBar
          label={`renderizando vídeos ${motionDone}/${motionTracked.length}`}
          percent={motionPercent}
        />
      )}

      {/* Slides grid */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {plan.slides.map((s) => (
            <SlideCard
              key={s.index}
              plan={plan}
              slide={s}
              total={total}
              isSel={selected.has(s.index)}
              isPreview={preview.has(s.index)}
              selectable={anyImage && !busyState && !busy}
              generating={generating}
              rendering={rendering}
              onToggleSelect={toggle}
              onTogglePreview={togglePreview}
              onEdit={() => setEditingIndex(s.index)}
            />
          ))}
        </div>
      </div>

      {/* Selective actions */}
      {anyImage && !busyState && (
        <div className="border-t border-line p-3">
          {selected.size > 0 ? (
            <div className="space-y-2">
              <div className="text-xs text-fg-muted">
                {selected.size} slide(s) selecionado(s) — descreva o ajuste (opcional)
              </div>
              <div className="flex items-end gap-2">
                <TextArea
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  rows={1}
                  aria-label="Instrução de ajuste"
                  placeholder="ex: deixa o ícone maior e o fundo mais escuro"
                  className="max-h-28 flex-1"
                />
                <Button onClick={runRegen} disabled={busy} iconLeft={<Refresh size={16} />}>
                  Refazer
                </Button>
                <Button
                  variant="secondary"
                  onClick={animateSelected}
                  disabled={busy}
                  iconLeft={<Video size={16} />}
                >
                  Renderizar vídeo
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-center text-xs text-fg-subtle">
              Clique em slides para refazê-los ou renderizar seus vídeos. Use “▶ prévia”
              para ver a animação na hora.
            </p>
          )}
        </div>
      )}

      {editingIndex != null && plan.slides[editingIndex - 1] && (
        <SlideEditorModal
          carouselId={carouselId}
          plan={plan}
          slide={plan.slides[editingIndex - 1]}
          total={total}
          onClose={() => setEditingIndex(null)}
          onCarouselUpdate={onCarouselUpdate}
        />
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* SlideCard (organism) — a selectable, keyboard-operable slide tile           */
/* -------------------------------------------------------------------------- */

function SlideCard({
  plan,
  slide: s,
  total,
  isSel,
  isPreview,
  selectable,
  generating,
  rendering,
  onToggleSelect,
  onTogglePreview,
  onEdit,
}: {
  plan: CarouselPlan
  slide: Slide
  total: number
  isSel: boolean
  isPreview: boolean
  selectable: boolean
  generating: boolean
  rendering: boolean
  onToggleSelect: (index: number) => void
  onTogglePreview: (index: number) => void
  onEdit: () => void
}) {
  const imgSpin = s.status === 'running' || (generating && s.status === 'pending')
  const motionSpin =
    s.motion_status === 'running' || (rendering && s.motion_status === 'pending')
  const exportSpin =
    s.export_status === 'running' || (rendering && s.export_status === 'pending')
  const canAnimate = !!s.motion?.animate
  const hasError =
    s.status === 'error' || s.motion_status === 'error' || s.export_status === 'error'

  return (
    <div
      role={selectable ? 'button' : undefined}
      tabIndex={selectable ? 0 : undefined}
      aria-pressed={selectable ? isSel : undefined}
      aria-label={`Slide ${s.index} de ${total}: ${s.headline}`}
      onClick={() => selectable && onToggleSelect(s.index)}
      onKeyDown={(e) => {
        if (selectable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onToggleSelect(s.index)
        }
      }}
      className={
        'group relative overflow-hidden rounded-lg border bg-surface-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg ' +
        (isSel
          ? 'border-primary ring-2 ring-primary/40'
          : 'border-line') +
        (selectable ? ' cursor-pointer hover:border-fg-subtle' : '')
      }
    >
      <div className="relative aspect-[4/5] w-full">
        {isPreview && canAnimate ? (
          <Player
            component={SlideMotion}
            inputProps={motionProps(plan, s, total)}
            durationInFrames={Math.round((s.motion?.duration_seconds ?? 4) * FPS)}
            fps={FPS}
            compositionWidth={1080}
            compositionHeight={1350}
            style={{ width: '100%', height: '100%' }}
            autoPlay
            loop
          />
        ) : s.video_url ? (
          <video
            src={s.video_url}
            className="size-full object-cover"
            autoPlay
            loop
            muted
            playsInline
          />
        ) : s.image_url || s.elements.length > 0 ? (
          // Composited thumbnail: the exact same SlideMotion composition the
          // editor and the export use, frozen on the settled final frame —
          // so layout/font/block edits show up here immediately (WYSIWYG).
          <Thumbnail
            component={SlideMotion}
            inputProps={motionProps(plan, s, total, { frozen: true })}
            frameToDisplay={THUMB_DURATION - 1}
            durationInFrames={THUMB_DURATION}
            fps={FPS}
            compositionWidth={1080}
            compositionHeight={1350}
            style={{ width: '100%', height: '100%' }}
          />
        ) : (
          <div className="flex size-full flex-col justify-between p-3">
            <Badge tone={ROLE_TONE[s.role]}>{s.role}</Badge>
            <p className="line-clamp-3 text-sm font-semibold text-fg">{s.headline}</p>
          </div>
        )}

        {(imgSpin || motionSpin || exportSpin) && (
          <div className="absolute inset-0 grid place-items-center bg-black/55 backdrop-blur-sm">
            <Spinner className="text-primary" />
          </div>
        )}
        {hasError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/75 p-2 text-center text-[11px] text-error">
            <AlertTriangle size={18} />
            {s.error || s.motion_error || s.export_error || 'falhou'}
          </div>
        )}

        <span className="absolute left-2 top-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[11px] font-medium text-fg">
          {s.index}
        </span>

        {canAnimate && (
          <span className="absolute left-9 top-2 inline-flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-[11px] font-medium text-fg">
            <Video size={12} /> vídeo
          </span>
        )}

        {isSel && (
          <span className="absolute right-2 top-2 grid size-5 place-items-center rounded-md bg-primary text-black">
            <Check size={14} />
          </span>
        )}

        {/* Live preview toggle (no server render) */}
        {canAnimate && selectable && (
          <button
            type="button"
            aria-label={isPreview ? 'Parar prévia' : 'Tocar prévia da animação'}
            onClick={(e) => {
              e.stopPropagation()
              onTogglePreview(s.index)
            }}
            className="absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-md bg-black/65 px-2 py-1 text-[11px] font-medium text-fg backdrop-blur-sm transition-colors hover:bg-black/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            {isPreview ? <Pause size={12} /> : <Play size={12} />}
            {isPreview ? 'parar' : 'prévia'}
          </button>
        )}

        {/* Layered editor entry point */}
        <button
          type="button"
          aria-label={`Editar slide ${s.index}`}
          onClick={(e) => {
            e.stopPropagation()
            onEdit()
          }}
          className="absolute bottom-2 right-2 inline-flex items-center gap-1 rounded-md bg-black/65 px-2 py-1 text-[11px] font-medium text-fg backdrop-blur-sm transition-colors hover:bg-black/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <Pencil size={12} />
          editar
        </button>
      </div>
    </div>
  )
}
