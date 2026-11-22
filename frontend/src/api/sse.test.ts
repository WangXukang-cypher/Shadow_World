import { describe, expect, it } from 'vitest'

import { consumeEventStream } from './sse'

function responseFromChunks(chunks: string[]) {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  })
  return new Response(stream, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

describe('consumeEventStream', () => {
  it('parses events split across network chunks', async () => {
    const events: Array<{ id?: string; event: string; data: unknown }> = []
    const response = responseFromChunks([
      'id: 1\nevent: assistant.delta\ndata: {"te',
      'xt":"你好"}\n\nid: 2\nevent: run.completed\ndata: {"route":"chat"}\n\n',
    ])
    const lastId = await consumeEventStream(response, (event) => { events.push(event) })
    expect(lastId).toBe('2')
    expect(events).toEqual([
      { id: '1', event: 'assistant.delta', data: { text: '你好' } },
      { id: '2', event: 'run.completed', data: { route: 'chat' } },
    ])
  })

  it('ignores heartbeat comments', async () => {
    const events: unknown[] = []
    const response = responseFromChunks([': heartbeat\n\nid: 3\ndata: plain text\n\n'])
    await consumeEventStream(response, (event) => { events.push(event) })
    expect(events).toEqual([{ id: '3', event: 'message', data: 'plain text' }])
  })
})
