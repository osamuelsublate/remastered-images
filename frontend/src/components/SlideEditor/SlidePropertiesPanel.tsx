import { useState, type ChangeEvent } from 'react'
import { FONT_FAMILIES, ensureFont } from '@motion/fonts'
import type {
  ElementRect,
  PaletteColor,
  ShapeKind,
  Slide,
  SlideElement,
  TextStyle,
} from '../../types'
import { Button, Field, TextArea, TextInput } from '../ui'
import { Images, Refresh, Trash } from '../icons'

const ROLE_LABEL: Record<string, string> = {
  h1: 'Título (H1)',
  text: 'Texto',
  swipe_cue: 'Swipe cue',
  handle: '@handle',
  progress: 'Progresso',
  visual: 'Bloco visual',
}

const TYPE_LABEL: Record<string, string> = {
  shape: 'Forma',
  icon: 'Ícone',
  image: 'Imagem',
  video: 'Vídeo',
}

const WEIGHTS = [400, 500, 600, 700, 800, 900]

const SHAPES: { value: ShapeKind; label: string }[] = [
  { value: 'rect', label: 'Retângulo' },
  { value: 'ellipse', label: 'Elipse' },
  { value: 'line', label: 'Linha' },
  { value: 'arrow', label: 'Seta' },
]

const ICON_OPTIONS = [
  'arrow_right',
  'arrow_up_right',
  'arrow_down',
  'check',
  'x',
  'star',
  'bolt',
  'circle',
  'quote',
  'sparkles',
  'plus',
  'play',
]

/**
 * Contextual property form for whatever block is selected on the canvas:
 * text (content/font/size/color/weight/align), shape (kind/fill/opacity),
 * icon, image/video (fit/opacity) or the background box (regenerate via AI /
 * replace via upload). Every block can be removed.
 */
export function SlidePropertiesPanel({
  slide,
  selected,
  isBackgroundSelected,
  palette,
  saving,
  onContentChange,
  onStyleChange,
  onPropsChange,
  onRectChange,
  onRemove,
  onRegenerateBackground,
  onReplaceBackgroundImage,
}: {
  slide: Slide
  selected: SlideElement | null
  isBackgroundSelected: boolean
  palette: PaletteColor[]
  saving: boolean
  onContentChange: (content: string) => void
  onStyleChange: (patch: Partial<TextStyle>) => void
  onPropsChange: (patch: Partial<SlideElement>) => void
  onRectChange: (rect: ElementRect) => void
  onRemove: () => void
  onRegenerateBackground: (instruction: string) => Promise<void> | void
  onReplaceBackgroundImage: (file: File) => Promise<void> | void
}) {
  if (isBackgroundSelected) {
    return (
      <BackgroundPanel
        rect={slide.background_rect}
        saving={saving}
        onRectChange={onRectChange}
        onRegenerateBackground={onRegenerateBackground}
        onReplaceBackgroundImage={onReplaceBackgroundImage}
      />
    )
  }

  if (!selected) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-fg-subtle">
        Clique em um bloco ou no fundo do slide para editar, ou adicione um novo bloco.
      </div>
    )
  }

  const title =
    selected.type === 'text'
      ? ROLE_LABEL[selected.role] ?? selected.role
      : TYPE_LABEL[selected.type] ?? selected.type

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-fg">{title}</h4>
        <button
          type="button"
          title="Remover bloco"
          aria-label="Remover bloco"
          onClick={onRemove}
          className="grid size-8 place-items-center rounded-lg text-fg-muted transition-colors hover:bg-error/15 hover:text-error"
        >
          <Trash size={15} />
        </button>
      </div>

      {selected.type === 'text' && (
        <TextBlockFields selected={selected} palette={palette} onContentChange={onContentChange} onStyleChange={onStyleChange} />
      )}

      {selected.type === 'shape' && (
        <ShapeBlockFields selected={selected} palette={palette} onPropsChange={onPropsChange} />
      )}

      {selected.type === 'icon' && (
        <IconBlockFields selected={selected} palette={palette} onPropsChange={onPropsChange} />
      )}

      {(selected.type === 'image' || selected.type === 'video') && (
        <MediaBlockFields selected={selected} onPropsChange={onPropsChange} />
      )}

      <RectFields
        rect={selected.rect}
        onChange={onRectChange}
        lockHeight={selected.type === 'text'}
      />

      {saving && <p className="text-xs text-fg-subtle">salvando…</p>}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Text                                                                        */
/* -------------------------------------------------------------------------- */

function TextBlockFields({
  selected,
  palette,
  onContentChange,
  onStyleChange,
}: {
  selected: SlideElement
  palette: PaletteColor[]
  onContentChange: (content: string) => void
  onStyleChange: (patch: Partial<TextStyle>) => void
}) {
  return (
    <>
      <Field label="Texto" htmlFor="el-content">
        <TextArea
          id="el-content"
          value={selected.content}
          onChange={(e) => onContentChange(e.target.value)}
          rows={selected.role === 'h1' ? 1 : 3}
        />
      </Field>

      <Field label="Fonte" htmlFor="el-font">
        <select
          id="el-font"
          value={selected.style.font_family || 'Inter'}
          onChange={(e) => onStyleChange({ font_family: e.target.value })}
          className="min-h-11 w-full rounded-lg border border-line bg-surface-2 px-3.5 text-sm text-fg outline-none focus:border-primary"
        >
          {FONT_FAMILIES.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <p
          className="mt-1.5 truncate rounded-lg border border-line bg-surface-2 px-3 py-1.5 text-lg text-fg"
          style={{ fontFamily: ensureFont(selected.style.font_family) }}
        >
          {selected.content.trim().slice(0, 24) || 'Aa Bb Cc 123'}
        </p>
      </Field>

      <Field label="Tamanho" htmlFor="el-size">
        <TextInput
          id="el-size"
          type="number"
          min={8}
          value={Math.round(selected.style.font_size)}
          onChange={(e) => onStyleChange({ font_size: Number(e.target.value) || 0 })}
        />
      </Field>

      <ColorField
        label="Cor"
        value={selected.style.color}
        palette={palette}
        onChange={(color) => onStyleChange({ color })}
      />

      <Field label="Peso" htmlFor="el-weight">
        <select
          id="el-weight"
          value={selected.style.weight}
          onChange={(e) => onStyleChange({ weight: Number(e.target.value) })}
          className="min-h-11 w-full rounded-lg border border-line bg-surface-2 px-3.5 text-sm text-fg outline-none focus:border-primary"
        >
          {WEIGHTS.map((w) => (
            <option key={w} value={w}>
              {w}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Alinhamento">
        <div className="inline-flex rounded-lg border border-line bg-surface-2 p-0.5">
          {(['left', 'center', 'right'] as const).map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => onStyleChange({ align: a })}
              className={
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors ' +
                (selected.style.align === a
                  ? 'bg-primary text-black'
                  : 'text-fg-muted hover:text-fg')
              }
            >
              {a}
            </button>
          ))}
        </div>
      </Field>
    </>
  )
}

/* -------------------------------------------------------------------------- */
/* Shape / icon / media                                                        */
/* -------------------------------------------------------------------------- */

function ShapeBlockFields({
  selected,
  palette,
  onPropsChange,
}: {
  selected: SlideElement
  palette: PaletteColor[]
  onPropsChange: (patch: Partial<SlideElement>) => void
}) {
  return (
    <>
      <Field label="Forma" htmlFor="el-shape">
        <select
          id="el-shape"
          value={selected.shape ?? 'rect'}
          onChange={(e) => onPropsChange({ shape: e.target.value as ShapeKind })}
          className="min-h-11 w-full rounded-lg border border-line bg-surface-2 px-3.5 text-sm text-fg outline-none focus:border-primary"
        >
          {SHAPES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </Field>

      <ColorField
        label="Cor"
        value={selected.fill ?? '#ffffff'}
        palette={palette}
        onChange={(fill) => onPropsChange({ fill })}
      />

      {selected.shape === 'rect' && (
        <Field label="Raio dos cantos" htmlFor="el-radius">
          <TextInput
            id="el-radius"
            type="number"
            min={0}
            value={Math.round(selected.corner_radius ?? 0)}
            onChange={(e) => onPropsChange({ corner_radius: Number(e.target.value) || 0 })}
          />
        </Field>
      )}

      <OpacityField selected={selected} onPropsChange={onPropsChange} />
    </>
  )
}

function IconBlockFields({
  selected,
  palette,
  onPropsChange,
}: {
  selected: SlideElement
  palette: PaletteColor[]
  onPropsChange: (patch: Partial<SlideElement>) => void
}) {
  return (
    <>
      <Field label="Ícone" htmlFor="el-icon">
        <select
          id="el-icon"
          value={selected.icon_name ?? 'sparkles'}
          onChange={(e) => onPropsChange({ icon_name: e.target.value })}
          className="min-h-11 w-full rounded-lg border border-line bg-surface-2 px-3.5 text-sm text-fg outline-none focus:border-primary"
        >
          {ICON_OPTIONS.map((name) => (
            <option key={name} value={name}>
              {name.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </Field>

      <ColorField
        label="Cor"
        value={selected.fill ?? selected.style.color}
        palette={palette}
        onChange={(fill) => onPropsChange({ fill })}
      />

      <OpacityField selected={selected} onPropsChange={onPropsChange} />
    </>
  )
}

function MediaBlockFields({
  selected,
  onPropsChange,
}: {
  selected: SlideElement
  onPropsChange: (patch: Partial<SlideElement>) => void
}) {
  return (
    <>
      <Field label="Ajuste" htmlFor="el-fit">
        <select
          id="el-fit"
          value={selected.fit ?? 'cover'}
          onChange={(e) => onPropsChange({ fit: e.target.value as 'cover' | 'contain' })}
          className="min-h-11 w-full rounded-lg border border-line bg-surface-2 px-3.5 text-sm text-fg outline-none focus:border-primary"
        >
          <option value="cover">Preencher (cover)</option>
          <option value="contain">Conter (contain)</option>
        </select>
      </Field>

      <OpacityField selected={selected} onPropsChange={onPropsChange} />

      {selected.type === 'video' && (
        <p className="text-xs text-fg-subtle">
          {selected.media_duration_seconds
            ? `Vídeo de ${selected.media_duration_seconds.toFixed(1)}s — o slide será exportado como MP4.`
            : 'O slide será exportado como MP4.'}
        </p>
      )}
    </>
  )
}

function OpacityField({
  selected,
  onPropsChange,
}: {
  selected: SlideElement
  onPropsChange: (patch: Partial<SlideElement>) => void
}) {
  return (
    <Field label={`Opacidade (${Math.round((selected.opacity ?? 1) * 100)}%)`} htmlFor="el-opacity">
      <input
        id="el-opacity"
        type="range"
        min={0}
        max={100}
        value={Math.round((selected.opacity ?? 1) * 100)}
        onChange={(e) => onPropsChange({ opacity: Number(e.target.value) / 100 })}
        className="w-full accent-primary"
      />
    </Field>
  )
}

function ColorField({
  label,
  value,
  palette,
  onChange,
}: {
  label: string
  value: string
  palette: PaletteColor[]
  onChange: (hex: string) => void
}) {
  return (
    <Field label={label}>
      <div className="flex flex-wrap items-center gap-2">
        {palette.map((c) => (
          <button
            key={c.hex}
            type="button"
            title={`${c.hex} · ${c.role}`}
            onClick={() => onChange(c.hex)}
            className={
              'size-8 rounded-full ring-2 transition-transform ' +
              (value.toLowerCase() === c.hex.toLowerCase()
                ? 'scale-110 ring-primary'
                : 'ring-white/15')
            }
            style={{ backgroundColor: c.hex }}
          />
        ))}
        <TextInput
          aria-label="Cor em hex"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-24"
        />
      </div>
    </Field>
  )
}

/* -------------------------------------------------------------------------- */
/* Background                                                                  */
/* -------------------------------------------------------------------------- */

function BackgroundPanel({
  rect,
  saving,
  onRectChange,
  onRegenerateBackground,
  onReplaceBackgroundImage,
}: {
  rect: ElementRect
  saving: boolean
  onRectChange: (rect: ElementRect) => void
  onRegenerateBackground: (instruction: string) => Promise<void> | void
  onReplaceBackgroundImage: (file: File) => Promise<void> | void
}) {
  const [instruction, setInstruction] = useState('')
  const [regenBusy, setRegenBusy] = useState(false)

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div>
        <h4 className="text-sm font-semibold text-fg">Fundo</h4>
        <p className="mt-1 text-xs text-fg-subtle">
          Arraste/redimensione na tela ou ajuste os valores abaixo.
        </p>
      </div>

      <RectFields rect={rect} onChange={onRectChange} />

      <div className="flex flex-col gap-2">
        <TextArea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={2}
          placeholder="Instrução para regenerar o fundo (opcional)"
        />
        <Button
          variant="secondary"
          iconLeft={<Refresh size={16} />}
          loading={regenBusy}
          onClick={async () => {
            setRegenBusy(true)
            try {
              await onRegenerateBackground(instruction.trim())
              setInstruction('')
            } finally {
              setRegenBusy(false)
            }
          }}
        >
          Regenerar com IA
        </Button>
        <label className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border border-line bg-surface-3 px-4 text-sm font-semibold text-fg transition-colors hover:bg-[#26262b]">
          <Images size={16} />
          Substituir imagem
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              const f = e.target.files?.[0]
              if (f) onReplaceBackgroundImage(f)
              e.target.value = ''
            }}
          />
        </label>
      </div>

      {saving && <p className="text-xs text-fg-subtle">salvando…</p>}
    </div>
  )
}

function RectFields({
  rect,
  onChange,
  lockHeight = false,
}: {
  rect: ElementRect
  onChange: (rect: ElementRect) => void
  lockHeight?: boolean
}) {
  const set = (key: keyof ElementRect) => (e: ChangeEvent<HTMLInputElement>) => {
    onChange({ ...rect, [key]: Number(e.target.value) || 0 })
  }
  return (
    <div className="grid grid-cols-4 gap-2">
      {(['x', 'y', 'w', 'h'] as const).map((k) => (
        <Field key={k} label={k.toUpperCase()}>
          <TextInput
            type="number"
            value={Math.round(rect[k] * 10) / 10}
            onChange={set(k)}
            disabled={lockHeight && k === 'h'}
            title={lockHeight && k === 'h' ? 'Altura automática (segue o texto)' : undefined}
          />
        </Field>
      ))}
    </div>
  )
}
