import { useState } from 'react'
import { ChatPanel } from './components/ChatPanel'
import { PreviewPanel } from './components/PreviewPanel'
import { Alert, Button } from './components/ui'
import { useCarouselPolling } from './hooks/useCarouselPolling'
import { useCarouselSession } from './hooks/useCarouselSession'
import { useChat } from './hooks/useChat'
import { useGeneration } from './hooks/useGeneration'

export default function App() {
  const [error, setError] = useState<string | null>(null)

  const { state, setState, idRef, ensureSession, reset } = useCarouselSession(setError)
  useCarouselPolling(state, setState, idRef)
  const { chatBusy, handleUpload, handleSend } = useChat({ ensureSession, setState, setError })
  const { genBusy, handleGenerate, handleRegenerate, handleAnimate, handleDownload } =
    useGeneration({
      state,
      idRef,
      setState,
      setError,
    })

  const plan = state?.plan ?? null

  return (
    <div className="mx-auto flex h-screen max-w-[1400px] flex-col px-4 py-4 sm:px-6">
      <header className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-lg bg-primary text-lg font-black text-black">
            C
          </span>
          <div>
            <h1 className="text-lg font-bold leading-none text-fg">Carousel Studio</h1>
            <p className="text-xs text-fg-subtle">converse → estrutura → carrossel pronto</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-right text-xs text-fg-subtle sm:block">
            gpt-5.5 (plano) · gpt-5.4-mini (chat) · gemini-3-pro-image · via OpenRouter
          </span>
          <Button variant="ghost" size="sm" onClick={reset}>
            novo
          </Button>
        </div>
      </header>

      {error && (
        <div className="mb-3">
          <Alert onDismiss={() => setError(null)}>{error}</Alert>
        </div>
      )}

      <div
        className={
          plan
            ? 'grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]'
            : 'grid min-h-0 flex-1 grid-cols-1'
        }
      >
        <div className="min-h-0">
          <ChatPanel
            messages={state?.messages ?? []}
            references={state?.references ?? []}
            busy={chatBusy}
            onSend={handleSend}
            onUpload={handleUpload}
            onError={setError}
          />
        </div>
        {plan && (
          <div className="min-h-0">
            <PreviewPanel
              plan={plan}
              status={state?.status ?? 'draft'}
              busy={genBusy}
              quality={state?.quality ?? 'medium'}
              carouselId={state?.id ?? ''}
              onGenerate={handleGenerate}
              onRegenerate={handleRegenerate}
              onAnimate={handleAnimate}
              onDownload={handleDownload}
              onQualityChange={(quality) =>
                setState((s) => (s ? { ...s, quality } : s))
              }
              onCarouselUpdate={setState}
            />
          </div>
        )}
      </div>
    </div>
  )
}
