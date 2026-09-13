export interface ChatRequest {
  sessionId: string
  message: string
}

export interface ChatStreamHandlers {
  onDelta: (delta: string) => void
  onDone: () => void
  onError: (message: string) => void
}

type FrameResult = 'continue' | 'done' | 'error'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function processFrame(frame: string, handlers: ChatStreamHandlers): FrameResult {
  for (const line of frame.split(/\r?\n/)) {
    if (!line.startsWith('data:')) {
      continue
    }

    const data = line.slice('data:'.length).trimStart()
    if (data === '[DONE]') {
      handlers.onDone()
      return 'done'
    }

    let payload: unknown
    try {
      payload = JSON.parse(data)
    } catch {
      handlers.onError('Invalid SSE data received from chat service.')
      return 'error'
    }

    if (!isRecord(payload)) {
      continue
    }

    if (typeof payload.delta === 'string') {
      handlers.onDelta(payload.delta)
      continue
    }

    if (isRecord(payload.error)) {
      handlers.onError(
        typeof payload.error.message === 'string'
          ? payload.error.message
          : 'Chat service returned an error.',
      )
      return 'error'
    }
  }

  return 'continue'
}

export async function streamChat(
  request: ChatRequest,
  handlers: ChatStreamHandlers,
): Promise<void> {
  let response: Response
  try {
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id: request.sessionId, message: request.message }),
    })
  } catch {
    handlers.onError('Unable to reach the chat service.')
    return
  }

  if (!response.ok) {
    handlers.onError(`Chat request failed (${response.status}).`)
    return
  }

  if (!response.body) {
    handlers.onError('Chat service returned an empty stream.')
    return
  }

  const decoder = new TextDecoder()
  const reader = response.body.getReader()
  let buffered = ''

  const processBufferedFrames = (): FrameResult => {
    const boundary = /\r?\n\r?\n/
    let match = boundary.exec(buffered)

    while (match) {
      const frame = buffered.slice(0, match.index)
      buffered = buffered.slice(match.index + match[0].length)
      const result = processFrame(frame, handlers)
      if (result !== 'continue') {
        return result
      }
      match = boundary.exec(buffered)
    }

    return 'continue'
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      buffered += decoder.decode(value, { stream: true })
      const result = processBufferedFrames()
      if (result !== 'continue') {
        return
      }
    }

    buffered += decoder.decode()
    const result = processBufferedFrames()
    if (result !== 'continue') {
      return
    }
  } catch {
    handlers.onError('Chat stream was interrupted.')
    return
  }

  handlers.onError('Chat stream ended before completion.')
}
