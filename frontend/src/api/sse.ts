export type ServerSentEvent<T = Record<string, unknown>> = {
  id?: string
  event: string
  data: T
}

type ConnectOptions = {
  signal?: AbortSignal
  lastEventId?: string
  onEvent: (event: ServerSentEvent) => void | Promise<void>
  onStateChange?: (state: 'connecting' | 'streaming' | 'reconnecting' | 'closed') => void
  reconnect?: boolean
  maxReconnects?: number
}

function parseBlock(block: string): ServerSentEvent | null {
  let id: string | undefined
  let event = 'message'
  const data: string[] = []
  for (const rawLine of block.split('\n')) {
    const line = rawLine.replace(/\r$/, '')
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator >= 0 ? line.slice(0, separator) : line
    const value = separator >= 0 ? line.slice(separator + 1).replace(/^ /, '') : ''
    if (field === 'id') id = value
    if (field === 'event') event = value
    if (field === 'data') data.push(value)
  }
  if (data.length === 0) return null
  const rawData = data.join('\n')
  let parsed: unknown = rawData
  try {
    parsed = JSON.parse(rawData)
  } catch {
    // Plain text SSE data is valid and remains a string.
  }
  return { id, event, data: parsed as Record<string, unknown> }
}

export async function consumeEventStream(
  response: Response,
  onEvent: ConnectOptions['onEvent'],
): Promise<string | undefined> {
  if (!response.body) throw new Error('当前浏览器不支持流式响应')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lastEventId: string | undefined
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n')
    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const event = parseBlock(block)
      if (event) {
        if (event.id) lastEventId = event.id
        await onEvent(event)
      }
      boundary = buffer.indexOf('\n\n')
    }
    if (done) break
  }
  return lastEventId
}

export async function connectSSE(url: string, options: ConnectOptions): Promise<void> {
  const reconnect = options.reconnect ?? true
  const maxReconnects = options.maxReconnects ?? 5
  let attempts = 0
  let lastEventId = options.lastEventId
  while (!options.signal?.aborted) {
    options.onStateChange?.(attempts === 0 ? 'connecting' : 'reconnecting')
    try {
      const response = await fetch(url, {
        headers: lastEventId ? { 'Last-Event-ID': lastEventId } : undefined,
        signal: options.signal,
      })
      if (!response.ok) throw new Error(`SSE 连接失败（${response.status}）`)
      options.onStateChange?.('streaming')
      const receivedId = await consumeEventStream(response, options.onEvent)
      lastEventId = receivedId ?? lastEventId
      if (!reconnect || options.signal?.aborted) break
    } catch (error) {
      if (options.signal?.aborted) break
      attempts += 1
      if (!reconnect || attempts > maxReconnects) throw error
      await new Promise((resolve) => setTimeout(resolve, Math.min(1000 * 2 ** attempts, 8000)))
      continue
    }
    attempts += 1
    if (attempts > maxReconnects) break
    await new Promise((resolve) => setTimeout(resolve, Math.min(1000 * 2 ** attempts, 8000)))
  }
  options.onStateChange?.('closed')
}
