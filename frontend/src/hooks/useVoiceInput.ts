import { useCallback, useRef, useState } from 'react'
import { api } from '../api/carouselApi'

// Ordered by preference; the first one the browser's MediaRecorder supports
// wins. OpenAI's transcription endpoint accepts all of these directly, so
// there's no client-side re-encoding needed.
const MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
  'audio/ogg;codecs=opus',
]

function pickMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return ''
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported?.(type)) ?? ''
}

function extensionFor(mimeType: string): string {
  if (mimeType.includes('mp4')) return 'mp4'
  if (mimeType.includes('ogg')) return 'ogg'
  return 'webm'
}

/**
 * Records a voice note (manual start/stop) and, once stopped, streams the
 * transcription so the caller can grow a text draft as it arrives — the
 * user still gets to review/edit before sending.
 */
export function useVoiceInput({
  onTranscriptDelta,
  onError,
}: {
  onTranscriptDelta: (text: string) => void
  onError: (message: string) => void
}) {
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)

  const releaseMic = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  const start = useCallback(async () => {
    if (recorderRef.current) return
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      onError('Não foi possível acessar o microfone (permissão negada?).')
      return
    }
    streamRef.current = stream

    const mimeType = pickMimeType()
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
    chunksRef.current = []

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onstop = async () => {
      releaseMic()
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
      chunksRef.current = []
      recorderRef.current = null
      if (blob.size === 0) return

      setIsTranscribing(true)
      try {
        await api.transcribeStream(blob, `gravacao.${extensionFor(recorder.mimeType)}`, {
          onDelta: onTranscriptDelta,
          onDone: () => {},
          onError,
        })
      } catch (e) {
        onError(String(e))
      } finally {
        setIsTranscribing(false)
      }
    }

    recorderRef.current = recorder
    recorder.start()
    setIsRecording(true)
  }, [onTranscriptDelta, onError])

  const stop = useCallback(() => {
    recorderRef.current?.stop()
    setIsRecording(false)
  }, [])

  return { isRecording, isTranscribing, start, stop }
}
