/**
 * Minimal Server-Sent Events reader for a `fetch()` response body.
 *
 * The browser's native `EventSource` can't do POST-with-body, so both the
 * streaming chat and the transcription endpoints are consumed by manually
 * reading `response.body` and splitting it into `event:`/`data:` frames.
 */
export async function streamSse(
  response: Response,
  onEvent: (event: string, data: string) => void,
): Promise<void> {
  if (!response.body) {
    throw new Error('Resposta sem corpo — streaming não suportado neste navegador.')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sepIndex = buffer.indexOf('\n\n')
    while (sepIndex !== -1) {
      parseFrame(buffer.slice(0, sepIndex), onEvent)
      buffer = buffer.slice(sepIndex + 2)
      sepIndex = buffer.indexOf('\n\n')
    }
  }

  if (buffer.trim()) parseFrame(buffer, onEvent)
}

function parseFrame(frame: string, onEvent: (event: string, data: string) => void) {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice('event:'.length).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).trim())
  }
  if (dataLines.length) onEvent(event, dataLines.join('\n'))
}
