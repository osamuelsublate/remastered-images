import { useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { api } from '../api/carouselApi'
import type { CarouselState } from '../types'

/** Sending chat messages and uploading reference images. */
export function useChat({
  ensureSession,
  setState,
  setError,
}: {
  ensureSession: () => Promise<string>
  setState: Dispatch<SetStateAction<CarouselState | null>>
  setError: Dispatch<SetStateAction<string | null>>
}) {
  const [chatBusy, setChatBusy] = useState(false)

  const handleUpload = async (files: File[]) => {
    setError(null)
    try {
      const id = await ensureSession()
      setState(await api.uploadReferences(id, files))
    } catch (e) {
      setError(String(e))
    }
  }

  const handleSend = async (message: string) => {
    setError(null)
    setChatBusy(true)
    // Optimistically show the user's message.
    setState((s) =>
      s ? { ...s, messages: [...s.messages, { role: 'user', content: message }] } : s,
    )
    try {
      const id = await ensureSession()
      await api.chatStream(id, message, {
        // Grow (or start) the assistant bubble as text streams in, like the
        // AI is typing. `onDone` below swaps this for the persisted final
        // state, so any tiny drift between accumulated deltas and the
        // server's final text self-corrects.
        onDelta: (text) => {
          setState((s) => {
            if (!s) return s
            const messages = [...s.messages]
            const last = messages[messages.length - 1]
            if (last?.role === 'assistant') {
              messages[messages.length - 1] = { ...last, content: last.content + text }
            } else {
              messages.push({ role: 'assistant', content: text })
            }
            return { ...s, messages }
          })
        },
        onDone: (finalState) => setState(finalState),
        onError: (message) => setError(message),
      })
    } catch (e) {
      setError(String(e))
    } finally {
      setChatBusy(false)
    }
  }

  return { chatBusy, handleUpload, handleSend }
}
