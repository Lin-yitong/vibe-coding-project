import { afterEach, describe, expect, it, vi } from 'vitest'
import { streamChat } from './chatClient'

function mockFetchSse(chunks: string[]): void {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  })

  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('streamChat', () => {
  it('parses a delta frame split across chunks before completion', async () => {
    mockFetchSse(['data: {"delta":"您', '好"}\n\ndata: [DONE]\n\n'])
    const deltas: string[] = []
    const onDone = vi.fn()
    const onError = vi.fn()

    await streamChat(
      { sessionId: 's', message: 'hi' },
      { onDelta: (delta) => deltas.push(delta), onDone, onError },
    )

    expect(deltas).toEqual(['您好'])
    expect(onDone).toHaveBeenCalledOnce()
    expect(onError).not.toHaveBeenCalled()
  })

  it('reports a server error frame and ignores unrelated event fields', async () => {
    mockFetchSse([
      'event: update\ndata: {"trace":"hidden"}\n\ndata: {"error":{"message":"服务暂时不可用"}}\n\n',
    ])
    const onDelta = vi.fn()
    const onDone = vi.fn()
    const errors: string[] = []

    await streamChat(
      { sessionId: 's', message: 'hi' },
      { onDelta, onDone, onError: (message) => errors.push(message) },
    )

    expect(onDelta).not.toHaveBeenCalled()
    expect(onDone).not.toHaveBeenCalled()
    expect(errors).toEqual(['服务暂时不可用'])
  })

  it('reports malformed data as a protocol error', async () => {
    mockFetchSse(['data: not-json\n\n'])
    const onError = vi.fn()

    await streamChat(
      { sessionId: 's', message: 'hi' },
      { onDelta: vi.fn(), onDone: vi.fn(), onError },
    )

    expect(onError).toHaveBeenCalledWith('Invalid SSE data received from chat service.')
  })

  it('reports HTTP and network failures through the error handler', async () => {
    const onError = vi.fn()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('bad gateway', { status: 502 })))

    await streamChat(
      { sessionId: 's', message: 'hi' },
      { onDelta: vi.fn(), onDone: vi.fn(), onError },
    )

    expect(onError).toHaveBeenCalledWith('Chat request failed (502).')

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await streamChat(
      { sessionId: 's', message: 'hi' },
      { onDelta: vi.fn(), onDone: vi.fn(), onError },
    )

    expect(onError).toHaveBeenLastCalledWith('Unable to reach the chat service.')
  })
})
