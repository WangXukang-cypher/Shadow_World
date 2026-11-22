export type Conversation = {
  id: string
  user_id: string
  title: string
  next_message_seq: number
  is_group?: boolean
  persona_ids?: Array<{
    name: string
    style: string
    traits: string
    addressUser: string
    avatar?: string
    model?: string
    max_replies?: number
  }>
  archived_at: string | null
  created_at: string
  updated_at: string
}

export type Message = {
  id: string
  user_id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'tool' | 'system'
  seq: number
  content: string
  status: string
  persona_name?: string | null
  persona_avatar?: string | null
  reply_to_id?: string | null
  created_at: string
}

export type ConversationDetail = Conversation & { messages: Message[] }
export type RunAccepted = { id: string; status: string; conversation_id: string }
export type ToolCallRecord = {
  id: string
  call_id: string
  tool_name: string
  status: string
  side_effect: string
  latency_ms: number | null
  error_code: string | null
  result_preview: Record<string, unknown> | null
  created_at: string
  completed_at: string | null
}

export type Run = {
  id: string
  conversation_id: string
  status: string
  route: string
  model_name: string
  iteration_count: number
  prompt_tokens: number
  completion_tokens: number
  error_code: string | null
  cancel_requested_at: string | null
  created_at: string
  completed_at: string | null
  tool_calls: ToolCallRecord[]
}

export type Memory = {
  id: string
  user_id: string
  type: string
  subject: string
  content: string
  normalized_key: string
  status: string
  source_message_id: string | null
  created_at: string
  updated_at: string
}

export type Task = {
  id: string
  user_id: string
  title: string
  status: string
  due_at: string | null
  remind_at: string | null
  notified_at: string | null
  source_message_id: string | null
  created_at: string
  updated_at: string
}

export type Notification = {
  id: number
  user_id: string
  type: string
  payload: Record<string, unknown>
  created_at: string
  read_at: string | null
}

export type Health = {
  status: 'ok'
  provider: string
  mode: string
  database: string
  timestamp: string
}

export type Me = {
  user_id: string
  display_name: string
  onboarded: boolean
}

export type ApiErrorBody = {
  error: {
    code: string
    message: string
    request_id: string
    details: unknown
  }
}
