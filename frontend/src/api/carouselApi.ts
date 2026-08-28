import type { CarouselPlan, CarouselState, ElementRect, SlideElement } from '../types'
import { streamSse } from './sse'

async function assertOk(res: Response): Promise<void> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
}

async function asJson<T>(res: Response): Promise<T> {
  await assertOk(res)
  return res.json() as Promise<T>
}

export interface StreamHandlers<TDone> {
  onDelta: (text: string) => void
  onDone: (payload: TDone) => void
  onError: (message: string) => void
}

export const api = {
  async createCarousel(): Promise<CarouselState> {
    return asJson(await fetch('/api/carousels', { method: 'POST' }))
  },

  async getCarousel(id: string): Promise<CarouselState> {
    return asJson(await fetch(`/api/carousels/${id}`))
  },

  async uploadReferences(id: string, files: FileList | File[]): Promise<CarouselState> {
    const fd = new FormData()
    Array.from(files).forEach((f) => fd.append('files', f))
    return asJson(
      await fetch(`/api/carousels/${id}/references`, { method: 'POST', body: fd }),
    )
  },

  async chatStream(
    id: string,
    message: string,
    handlers: StreamHandlers<CarouselState>,
  ): Promise<void> {
    const res = await fetch(`/api/carousels/${id}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    await assertOk(res)
    await streamSse(res, (event, data) => {
      if (event === 'delta') handlers.onDelta(JSON.parse(data) as string)
      else if (event === 'done') handlers.onDone(JSON.parse(data) as CarouselState)
      else if (event === 'error') handlers.onError(JSON.parse(data) as string)
    })
  },

  async transcribeStream(
    blob: Blob,
    filename: string,
    handlers: StreamHandlers<string>,
  ): Promise<void> {
    const fd = new FormData()
    fd.append('file', blob, filename)
    const res = await fetch('/api/transcriptions', { method: 'POST', body: fd })
    await assertOk(res)
    await streamSse(res, (event, data) => {
      if (event === 'delta') handlers.onDelta(JSON.parse(data) as string)
      else if (event === 'done') handlers.onDone(JSON.parse(data) as string)
      else if (event === 'error') handlers.onError(JSON.parse(data) as string)
    })
  },

  async generate(id: string, plan: CarouselPlan, quality: string): Promise<CarouselState> {
    return asJson(
      await fetch(`/api/carousels/${id}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan, quality }),
      }),
    )
  },

  async regenerate(
    id: string,
    indices: number[],
    instruction: string,
  ): Promise<CarouselState> {
    return asJson(
      await fetch(`/api/carousels/${id}/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ indices, instruction }),
      }),
    )
  },

  async animate(id: string, indices: number[]): Promise<CarouselState> {
    return asJson(
      await fetch(`/api/carousels/${id}/animate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ indices }),
      }),
    )
  },

  async updateSlideLayout(
    id: string,
    index: number,
    patch: { background_rect?: ElementRect; elements?: SlideElement[] },
  ): Promise<CarouselState> {
    return asJson(
      await fetch(`/api/carousels/${id}/slides/${index}/layout`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      }),
    )
  },

  async replaceSlideImage(id: string, index: number, file: File): Promise<CarouselState> {
    const fd = new FormData()
    fd.append('file', file)
    return asJson(
      await fetch(`/api/carousels/${id}/slides/${index}/image`, {
        method: 'POST',
        body: fd,
      }),
    )
  },

  /** Upload a user image/video to be used as a slide block. */
  async uploadMedia(id: string, file: File): Promise<{ url: string; kind: 'image' | 'video' }> {
    const fd = new FormData()
    fd.append('file', file)
    return asJson(await fetch(`/api/carousels/${id}/media`, { method: 'POST', body: fd }))
  },

  /** "Criar imagem": generate an isolated, transparent-background block
   * asset (icon/illustration) from a short free-text idea. */
  async generateBlockImage(
    id: string,
    slideIndex: number,
    prompt: string,
  ): Promise<{ url: string; kind: 'image' | 'video' }> {
    return asJson(
      await fetch(`/api/carousels/${id}/generate-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slide_index: slideIndex, prompt }),
      }),
    )
  },

  /** Kick off the final export job (composited PNGs + MP4s for the zip). */
  async exportCarousel(id: string): Promise<CarouselState> {
    return asJson(await fetch(`/api/carousels/${id}/export`, { method: 'POST' }))
  },

  downloadUrl(id: string): string {
    return `/api/carousels/${id}/download`
  },
}
