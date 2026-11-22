import { create } from 'zustand'

import type { Message } from '../types/api'

export type RunStage = 'idle' | 'connecting' | 'streaming' | 'reconnecting' | 'completed' | 'cancelled' | 'failed'

export type ToolActivity = {
  id: string
  tool: string
  status: 'running' | 'completed' | 'failed'
  detail?: string
}

type ChatState = {
  conversationId?: string
  messages: Message[]
  draftAssistant: string
  runId?: string
  runStage: RunStage
  runRoute?: string
  tools: ToolActivity[]
  lastEventId?: string
  setConversation: (id: string, messages: Message[]) => void
  addUserMessage: (message: Message) => void
  beginRun: (runId: string) => void
  appendAssistantDelta: (text: string) => void
  rewindAssistant: (characters: number) => void
  setRunStage: (stage: RunStage) => void
  setRunRoute: (route?: string) => void
  setLastEventId: (id?: string) => void
  startTool: (tool: string) => void
  finishTool: (tool: string) => void
  completeRun: (message: Message) => void
  failRun: () => void
  resetRun: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  draftAssistant: '',
  runStage: 'idle',
  tools: [],
  setConversation: (conversationId, messages) =>
    set({ conversationId, messages, draftAssistant: '', runId: undefined, runStage: 'idle', tools: [] }),
  addUserMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  beginRun: (runId) =>
    set({ runId, runStage: 'connecting', draftAssistant: '', tools: [], lastEventId: undefined }),
  appendAssistantDelta: (text) =>
    set((state) => ({ draftAssistant: `${state.draftAssistant}${text}` })),
  rewindAssistant: (characters) =>
    set((state) => ({
      draftAssistant: state.draftAssistant.slice(0, Math.max(0, state.draftAssistant.length - characters)),
    })),
  setRunStage: (runStage) => set({ runStage }),
  setRunRoute: (runRoute) => set({ runRoute }),
  setLastEventId: (lastEventId) => set({ lastEventId }),
  startTool: (tool) =>
    set((state) => ({
      tools: [...state.tools, { id: `${tool}-${state.tools.length}`, tool, status: 'running' }],
    })),
  finishTool: (tool) =>
    set((state) => ({
      tools: state.tools.map((item) =>
        item.tool === tool && item.status === 'running' ? { ...item, status: 'completed' } : item,
      ),
    })),
  completeRun: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      draftAssistant: '',
      runStage: 'completed',
    })),
  failRun: () => set({ runStage: 'failed' }),
  resetRun: () =>
    set({ runId: undefined, runStage: 'idle', draftAssistant: '', tools: [], lastEventId: undefined }),
}))
