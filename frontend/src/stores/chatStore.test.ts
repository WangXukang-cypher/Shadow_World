import { beforeEach, describe, expect, it } from 'vitest'

import { useChatStore } from './chatStore'

describe('chatStore streaming state', () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      draftAssistant: '',
      runStage: 'idle',
      tools: [],
      runId: undefined,
      lastEventId: undefined,
    })
  })

  it('rewinds speculative text before a tool call', () => {
    useChatStore.getState().appendAssistantDelta('准备调用工具')
    useChatStore.getState().rewindAssistant(2)
    expect(useChatStore.getState().draftAssistant).toBe('准备调用')
  })

  it('supports cancelled terminal state', () => {
    useChatStore.getState().beginRun('run-1')
    useChatStore.getState().setRunStage('cancelled')
    expect(useChatStore.getState().runStage).toBe('cancelled')
  })
})
