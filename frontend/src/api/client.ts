import type {
  ApiErrorBody,
  Conversation,
  ConversationDetail,
  Health,
  Me,
  Memory,
  Notification,
  Run,
  RunAccepted,
  Task,
} from '../types/api'

const API_BASE = '/api/v1'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
    readonly requestId?: string,
    readonly details?: unknown,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let body: ApiErrorBody | undefined
    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      body = undefined
    }
    throw new ApiError(
      body?.error.message ?? `请求失败（${response.status}）`,
      body?.error.code ?? 'HTTP_ERROR',
      response.status,
      body?.error.request_id,
      body?.error.details,
    )
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  health: () => request<Health>('/health'),
  listConversations: () => request<Conversation[]>('/conversations'),
  createConversation: (title = '') =>
    request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
  getConversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (id: string) =>
    request<void>(`/conversations/${id}`, { method: 'DELETE' }),
  deleteMemory: (id: string) =>
    request<void>(`/memories/${id}`, { method: 'DELETE' }),
  sendMessage: (conversationId: string, content: string, persona?: { name: string; style: string; traits: string; addressUser: string; model?: string }) =>
    request<RunAccepted>(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, persona }),
    }),
  getRun: (id: string) => request<Run>(`/runs/${id}`),
  cancelRun: (id: string) =>
    request<{ id: string; status: string; cancel_requested: boolean }>(`/runs/${id}/cancel`, {
      method: 'POST',
    }),
  listMemories: () => request<Memory[]>('/memories'),
  createMemory: (content: string, type = 'fact', subject = '我') =>
    request<Memory>('/memories', {
      method: 'POST',
      body: JSON.stringify({ content, type, subject }),
    }),
  listTasks: () => request<Task[]>('/tasks'),
  createTask: (title: string, remindAt?: string) =>
    request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify({ title, remind_at: remindAt || null }),
    }),
  completeTask: (id: string) =>
    request<void>(`/tasks/${id}/complete`, { method: 'POST' }),
  deleteTask: (id: string) =>
    request<void>(`/tasks/${id}`, { method: 'DELETE' }),
  listNotifications: (afterId = 0) =>
    request<Notification[]>(`/notifications?after_id=${afterId}`),
  deleteNotification: (id: number) =>
    request<void>(`/notifications/${id}`, { method: 'DELETE' }),
  clearNotifications: () =>
    request<void>('/notifications', { method: 'DELETE' }),
  fetchMe: () =>
    request<Me>('/me'),
  fetch: <T = unknown>(path: string) => request<T>(path),
}
