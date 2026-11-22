import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { connectSSE } from '../../api/sse'
import { useChatStore } from '../../stores/chatStore'
import type { Message } from '../../types/api'

export function useRunStream(runId?: string) {
  const queryClient = useQueryClient()
  const conversationId = useChatStore((state) => state.conversationId)
  const setRunStage = useChatStore((state) => state.setRunStage)
  const setRunRoute = useChatStore((state) => state.setRunRoute)
  const setLastEventId = useChatStore((state) => state.setLastEventId)
  const startTool = useChatStore((state) => state.startTool)
  const finishTool = useChatStore((state) => state.finishTool)
  const appendAssistantDelta = useChatStore((state) => state.appendAssistantDelta)
  const rewindAssistant = useChatStore((state) => state.rewindAssistant)
  const completeRun = useChatStore((state) => state.completeRun)
  const failRun = useChatStore((state) => state.failRun)

  useEffect(() => {
    if (!runId) return
    const controller = new AbortController()
    const seen = new Set<string>()
    void connectSSE(`/api/v1/runs/${runId}/events`, {
      signal: controller.signal,
      lastEventId: useChatStore.getState().lastEventId,
      reconnect: true,
      onStateChange: (state) => {
        if (state === 'streaming') setRunStage('streaming')
        if (state === 'reconnecting') setRunStage('reconnecting')
      },
      onEvent: (event) => {
        if (event.id && seen.has(event.id)) return
        if (event.id) {
          seen.add(event.id)
          setLastEventId(event.id)
        }
        const data = event.data as Record<string, any>
        if (event.event === 'agent.status') setRunRoute(data.route as string)
        if (event.event === 'tool.started') startTool(data.tool as string)
        if (event.event === 'memory.saved') void queryClient.invalidateQueries({ queryKey: ['memories'] })
        if (event.event === 'tool.finished') finishTool(data.tool as string)
        if (event.event === 'assistant.delta') appendAssistantDelta(data.text as string)
        if (event.event === 'assistant.rewind') rewindAssistant(data.characters as number)
        if (event.event === 'run.completed') {
          completeRun(data.message as Message)
          void queryClient.invalidateQueries({ queryKey: ['conversations'] })
          void queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] })
          void queryClient.invalidateQueries({ queryKey: ['memories'] })
          void queryClient.invalidateQueries({ queryKey: ['tasks'] })
          controller.abort()
        }
        if (event.event === 'run.cancelled') {
          setRunStage('cancelled')
          controller.abort()
        }
        if (event.event === 'run.failed') {
          failRun()
          controller.abort()
        }
      },
    }).catch(() => {
      if (!controller.signal.aborted) failRun()
    })
    return () => controller.abort()
  }, [
    appendAssistantDelta,
    completeRun,
    conversationId,
    failRun,
    finishTool,
    queryClient,
    rewindAssistant,
    runId,
    setLastEventId,
    setRunRoute,
    setRunStage,
    startTool,
  ])
}
