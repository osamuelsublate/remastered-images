import { useRef, useState } from 'react'
import { BACKGROUND_SELECTION, useSlideEditor } from '../../hooks/useSlideEditor'
import type { CarouselPlan, CarouselState, ElementRole, Slide } from '../../types'
import { Button, IconButton, TextArea } from '../ui'
import { Images, Shapes, Sparkles, Type, Video, X } from '../icons'
import { SlideEditorCanvas } from './SlideEditorCanvas'
import { SlidePropertiesPanel } from './SlidePropertiesPanel'

/**
 * Full-screen "editar slide" experience: canvas (Player + react-moveable) on
 * the left, contextual property panel on the right. Every slide is a
 * composition of N editable blocks (text h1/text, shapes, icons, user
 * image/video) layered over the AI background — the toolbar adds new blocks,
 * the canvas moves/resizes them, the panel edits their props.
 */
export function SlideEditorModal({
  carouselId,
  plan,
  slide,
  total,
  onClose,
  onCarouselUpdate,
}: {
  carouselId: string
  plan: CarouselPlan
  slide: Slide
  total: number
  onClose: () => void
  onCarouselUpdate: (state: CarouselState) => void
}) {
  const textColor =
    plan.art_direction.palette.find((c) => c.role.toLowerCase().includes('text'))?.hex ??
    '#ffffff'
  const editor = useSlideEditor(carouselId, slide, onCarouselUpdate, {
    textColor,
    fontFamily: plan.art_direction.font_family,
    bodyFontFamily: plan.art_direction.font_family_secondary,
  })
  const mediaInputRef = useRef<HTMLInputElement>(null)
  const [assetPopoverOpen, setAssetPopoverOpen] = useState(false)
  const [assetPrompt, setAssetPrompt] = useState('')
  const [assetBusy, setAssetBusy] = useState(false)

  const isBackgroundSelected = editor.selectedId === BACKGROUND_SELECTION
  const selectedElement =
    !isBackgroundSelected && editor.selectedId
      ? editor.elements.find((e) => e.id === editor.selectedId) ?? null
      : null

  const addText = (role: ElementRole, content: string) =>
    editor.addElement({ type: 'text', role, content })

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Editor do slide ${slide.index}`}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose()
      }}
    >
      <div className="flex h-full max-h-[900px] w-full max-w-5xl overflow-hidden rounded-xl border border-line bg-surface">
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold text-fg">
                Editar slide {slide.index}/{total}
              </h3>
              <p className="text-xs text-fg-subtle">
                {editor.saving ? 'salvando…' : 'alterações salvas automaticamente'}
              </p>
            </div>
            <IconButton label="Fechar editor" onClick={onClose}>
              <X size={18} />
            </IconButton>
          </div>

          {/* Add-block toolbar */}
          <div className="flex flex-wrap items-center gap-1.5 border-b border-line px-4 py-2">
            <span className="mr-1 text-xs font-medium text-fg-subtle">Adicionar bloco:</span>
            <ToolbarButton icon={<Type size={14} />} label="H1" onClick={() => addText('h1', 'Título')} />
            <ToolbarButton icon={<Type size={12} />} label="Texto" onClick={() => addText('text', 'Seu texto aqui')} />
            <ToolbarButton
              icon={<Shapes size={14} />}
              label="Forma"
              onClick={() =>
                editor.addElement({
                  type: 'shape',
                  role: 'visual',
                  shape: 'rect',
                  fill: textColor,
                  opacity: 0.25,
                  z_index: 4,
                  rect: { x: 30, y: 40, w: 40, h: 12 },
                })
              }
            />
            <ToolbarButton
              icon={<Sparkles size={14} />}
              label="Ícone"
              onClick={() =>
                editor.addElement({
                  type: 'icon',
                  role: 'visual',
                  icon_name: 'sparkles',
                  fill: textColor,
                  rect: { x: 44, y: 42, w: 12, h: 9.6 },
                })
              }
            />
            <ToolbarButton
              icon={<Images size={14} />}
              label="Imagem"
              onClick={() => {
                if (mediaInputRef.current) {
                  mediaInputRef.current.accept = 'image/*'
                  mediaInputRef.current.click()
                }
              }}
            />
            <ToolbarButton
              icon={<Video size={14} />}
              label="Vídeo"
              onClick={() => {
                if (mediaInputRef.current) {
                  mediaInputRef.current.accept = 'video/mp4,video/quicktime,video/webm'
                  mediaInputRef.current.click()
                }
              }}
            />
            <input
              ref={mediaInputRef}
              type="file"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) editor.addMediaElement(f)
                e.target.value = ''
              }}
            />

            <div className="relative">
              <ToolbarButton
                icon={<Sparkles size={14} />}
                label="Criar imagem"
                onClick={() => setAssetPopoverOpen((v) => !v)}
              />
              {assetPopoverOpen && (
                <div className="absolute left-0 top-full z-10 mt-2 w-72 rounded-lg border border-line bg-surface-2 p-3 shadow-[var(--shadow-sm)]">
                  <p className="mb-2 text-xs text-fg-subtle">
                    Descreva um ícone ou ilustração isolada (fundo transparente) para inserir
                    neste slide.
                  </p>
                  <TextArea
                    autoFocus
                    rows={3}
                    value={assetPrompt}
                    onChange={(e) => setAssetPrompt(e.target.value)}
                    placeholder="ex: um foguete decolando, estilo line icon"
                  />
                  <Button
                    className="mt-2 w-full"
                    size="sm"
                    iconLeft={<Sparkles size={14} />}
                    loading={assetBusy}
                    disabled={!assetPrompt.trim()}
                    onClick={async () => {
                      setAssetBusy(true)
                      try {
                        await editor.generateImageElement(assetPrompt.trim())
                        setAssetPrompt('')
                        setAssetPopoverOpen(false)
                      } finally {
                        setAssetBusy(false)
                      }
                    }}
                  >
                    Gerar
                  </Button>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            <SlideEditorCanvas
              plan={plan}
              slide={slide}
              total={total}
              elements={editor.elements}
              backgroundRect={editor.backgroundRect}
              selectedId={editor.selectedId}
              onSelect={editor.select}
              onCommitElementRect={editor.updateElementRect}
              onCommitBackgroundRect={editor.updateBackgroundRect}
            />
          </div>
        </div>
        <div className="w-72 shrink-0 border-l border-line">
          <SlidePropertiesPanel
            slide={{ ...slide, elements: editor.elements, background_rect: editor.backgroundRect }}
            selected={selectedElement}
            isBackgroundSelected={isBackgroundSelected}
            palette={plan.art_direction.palette}
            saving={editor.saving}
            onContentChange={(content) =>
              selectedElement && editor.updateElementContent(selectedElement.id, content)
            }
            onStyleChange={(patch) =>
              selectedElement && editor.updateElementStyle(selectedElement.id, patch)
            }
            onPropsChange={(patch) =>
              selectedElement && editor.updateElementProps(selectedElement.id, patch)
            }
            onRectChange={(rect) =>
              isBackgroundSelected
                ? editor.updateBackgroundRect(rect)
                : selectedElement && editor.updateElementRect(selectedElement.id, rect)
            }
            onRemove={() => selectedElement && editor.removeElement(selectedElement.id)}
            onRegenerateBackground={editor.regenerateBackground}
            onReplaceBackgroundImage={editor.replaceBackgroundImage}
          />
        </div>
      </div>
    </div>
  )
}

function ToolbarButton({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface-2 px-2.5 py-1.5 text-xs font-medium text-fg-muted transition-colors hover:border-fg-subtle hover:text-fg"
    >
      {icon}
      {label}
    </button>
  )
}
