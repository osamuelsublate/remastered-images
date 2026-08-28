import { useEffect, useRef, useState } from 'react'
import type { ChatMessage } from '../types'
import { useVoiceInput } from '../hooks/useVoiceInput'
import { IconButton, Spinner, TextArea } from './ui'
import { ArrowUp, Mic, Plus, Square } from './icons'

export function ChatPanel({
  messages,
  references,
  busy,
  onSend,
  onUpload,
  onError,
}: {
  messages: ChatMessage[]
  references: string[]
  busy: boolean
  onSend: (message: string) => void
  onUpload: (files: File[]) => void
  onError?: (message: string) => void
}) {
  const [draft, setDraft] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const { isRecording, isTranscribing, start, stop } = useVoiceInput({
    onTranscriptDelta: (text) => setDraft((d) => d + text),
    onError: (message) => onError?.(message),
  })

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages.length, busy])

  const send = () => {
    const text = draft.trim()
    if (!text || busy) return
    onSend(text)
    setDraft('')
  }

  const lastMessage = messages[messages.length - 1]
  // The placeholder only makes sense before the first token of the reply
  // arrives — once it does, the assistant bubble itself grows in its place.
  const awaitingFirstToken = busy && (!lastMessage || lastMessage.role === 'user')
  const isStreamingReply = busy && lastMessage?.role === 'assistant'

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-line bg-surface">
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span className="size-2 rounded-full bg-primary" />
        <span className="text-sm font-semibold text-fg">Direção de criação</span>
        <span className="ml-auto text-xs text-fg-subtle">converse para montar o carrossel</span>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.map((m, i) => {
          const streaming = isStreamingReply && i === messages.length - 1
          return (
            <div
              key={i}
              className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
            >
              <div
                className={
                  'max-w-[85%] whitespace-pre-wrap rounded-xl px-3.5 py-2.5 text-sm leading-relaxed [overflow-wrap:anywhere] ' +
                  (m.role === 'user'
                    ? 'bg-surface-3 text-fg'
                    : 'border border-line bg-surface-2 text-fg-muted')
                }
              >
                {m.content}
                {streaming && (
                  <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-current align-middle" />
                )}
              </div>
            </div>
          )
        })}
        {awaitingFirstToken && (
          <div className="flex justify-start">
            <div className="inline-flex items-center gap-2 rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-sm text-fg-muted">
              <Spinner /> pensando…
            </div>
          </div>
        )}
      </div>

      {references.length > 0 && (
        <div className="border-t border-line px-4 py-2 text-xs text-fg-subtle">
          {references.length} referência(s): {references.join(', ')}
        </div>
      )}

      <div className="border-t border-line p-3">
        <div className="flex items-end gap-2">
          <IconButton label="Anexar referências" onClick={() => fileRef.current?.click()}>
            <Plus />
          </IconButton>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => {
              // Snapshot into a stable array: the live FileList is emptied the
              // moment we reset the input value below, which would otherwise
              // race the async upload and send zero files (422).
              if (e.target.files?.length) onUpload(Array.from(e.target.files))
              e.target.value = ''
            }}
          />
          <TextArea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            rows={1}
            aria-label="Mensagem"
            placeholder="Descreva o carrossel ou peça ajustes…"
            className="max-h-32 flex-1"
          />
          <IconButton
            label={isRecording ? 'Parar gravação' : 'Gravar mensagem por voz'}
            onClick={isRecording ? stop : start}
            disabled={busy || isTranscribing}
            className={isRecording ? 'relative border-error/40 text-error' : ''}
          >
            {isTranscribing ? (
              <Spinner />
            ) : isRecording ? (
              <Square size={16} />
            ) : (
              <Mic />
            )}
            {isRecording && (
              <span className="absolute -right-0.5 -top-0.5 size-2.5 animate-pulse rounded-full bg-error" />
            )}
          </IconButton>
          <IconButton
            label="Enviar mensagem"
            variant="primary"
            onClick={send}
            disabled={busy || !draft.trim()}
          >
            <ArrowUp />
          </IconButton>
        </div>
      </div>
    </div>
  )
}
