import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, LoaderCircle, Plus, RotateCcw, Sparkles, Square, Users } from 'lucide-react'
import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'

import { api, ApiError } from '../../api/client'
import { EmptyState } from '../../components/EmptyState'
import { MarkdownMessage } from '../../components/MarkdownMessage'
import { type PersonaConfig, PersonaModal, getAllPersonas, loadCustomPersonas, saveCustomPersonas } from '../../components/PersonaModal'
import { useChatStore } from '../../stores/chatStore'
import type { Message } from '../../types/api'
import { useRunStream } from './useRunStream'
import { CompanionSidebar } from '../companion/CompanionSidebar'

export function GroupChatPage() {
  const { conversationId } = useParams()
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [error, setError] = useState<string>()
  const [replyTo, setReplyTo] = useState<Message | null>(null)
  const [editingPersona, setEditingPersona] = useState<PersonaConfig | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const chat = useChatStore()
  const setConversation = useChatStore((state) => state.setConversation)
  useRunStream(chat.runId)

  const personas = getAllPersonas()
  const detail = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => api.getConversation(conversationId!),
    enabled: Boolean(conversationId),
  })
  const groupPersonas: PersonaConfig[] = useMemo(() => {
    const ids = detail.data?.persona_ids
    if (!ids) return []
    return ids.map((p) => {
      const found = personas.find((x) => x.name === p.name)
      // 合并人格库与会话快照：快照里的 max_replies 等字段生效，id 保留人格库的
      return found
        ? { ...found, ...p, id: found.id, avatar: p.avatar ?? found.avatar, maxReplies: p.max_replies ?? found.maxReplies }
        : { id: `group_${p.name}`, ...p, maxReplies: p.max_replies }
    })
  }, [detail.data, personas])

  const [showAddPersona, setShowAddPersona] = useState(false)
  const allPersonas = getAllPersonas()
  const cancelRun = useMutation({ mutationFn: (runId: string) => api.cancelRun(runId) })

  useEffect(() => {
    if (detail.data && detail.data.id !== chat.conversationId) {
      setConversation(detail.data.id, detail.data.messages)
    }
  }, [detail.data, chat.conversationId, setConversation])
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [chat.messages, chat.draftAssistant])

  const orderedMessages = useMemo(() => [...chat.messages].sort((a, b) => a.seq - b.seq), [chat.messages])
  const isRunning = ['connecting', 'streaming', 'reconnecting'].includes(chat.runStage)

  function detectTargetPersona(text: string): PersonaConfig | undefined {
    const match = text.match(/@(\S+)/)
    if (match) {
      return groupPersonas.find((p) => p.name === match[1])
    }
    return groupPersonas[0]
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const text = content.trim()
    if (!text || isRunning || !conversationId) return
    setError(undefined)
    const target = detectTargetPersona(text)
    try {
      chat.addUserMessage({
        id: `local-${Date.now()}`, user_id: 'local', conversation_id: conversationId,
        role: 'user', seq: Math.max(0, ...chat.messages.map((m) => m.seq)) + 1,
        content: text, status: 'pending', created_at: new Date().toISOString(),
      })
      setContent('')
      setReplyTo(null)
      const persona = target ? { name: target.name, style: target.style, traits: target.traits, addressUser: target.addressUser } : undefined
      const run = await api.sendMessage(conversationId, text, persona)
      chat.beginRun(run.id)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '发送失败')
    }
  }

  function getPersonaForMessage(msg: any): PersonaConfig | undefined {
    const pname = msg.persona_name
    if (!pname) return undefined
    return groupPersonas.find((p) => p.name === pname) ?? { id: 'unknown', name: pname, style: '', traits: '', addressUser: '' }
  }

  return (
    <div className="chat-layout">
      <CompanionSidebar activeId={conversationId} />
      <section className="chat-main">
        <header className="chat-header">
          <div>
            <span className="eyebrow">群聊</span>
            <h1>{detail.data?.title || '群聊'}</h1>
          </div>
          <div className="chat-header-actions">
            <div className="group-avatars">
              {groupPersonas.map((p) => (
                <span key={p.id} className="group-avatar-chip editable" title={`${p.name}（点击编辑人格）`} onClick={() => {
                  setEditingPersona({ ...p, maxReplies: p.maxReplies ?? 5 })
                }} style={{ cursor: 'pointer' }}>
                  {p.avatar ? <img src={p.avatar} className="persona-avatar-img" /> : p.name[0]}
                </span>
              ))}
              <button className="group-avatar-chip add-btn" onClick={() => setShowAddPersona(!showAddPersona)} title="添加人格">
                <Plus size={14} />
              </button>
            </div>
            {showAddPersona && (
              <div className="persona-dropdown" style={{ display: 'flex', position: 'absolute', top: '60px', right: '20px' }}>
                {allPersonas.filter((p) => !groupPersonas.find((g) => g.name === p.name)).map((p) => (
                  <button key={p.id} type="button" onClick={async () => {
                    await fetch(`/api/v1/conversations/${conversationId}/personas`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ name: p.name, style: p.style, traits: p.traits, addressUser: p.addressUser, avatar: p.avatar }),
                    })
                    await queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] })
                    setShowAddPersona(false)
                  }}>{p.name}</button>
                ))}
                {allPersonas.filter((p) => !groupPersonas.find((g) => g.name === p.name)).length === 0 && <span style={{ padding: '8px', fontSize: '11px', color: 'var(--muted)' }}>没有更多人格了</span>}
              </div>
            )}
            <div className={`run-pill ${chat.runStage}`}><span />{chat.runStage === 'idle' || chat.runStage === 'completed' ? '就绪' : '处理中'}</div>
          </div>
        </header>

        <div className="message-scroll" ref={scrollRef}>
          {orderedMessages.length === 0 ? (
            <EmptyState icon={Users} title="群聊已创建" description="在下方输入框中 @人格名 发送消息" />
          ) : null}
          {orderedMessages.map((msg) => {
            const persona = getPersonaForMessage(msg)
            const isUser = msg.role === 'user'
            const isSystem = msg.role === 'system'
            if (isSystem) {
              return <div key={msg.id} className="group-system-msg">{msg.content}</div>
            }
            return (
              <article key={msg.id} className={`message-card ${msg.role}`}>
                <div className="message-avatar">
                  {isUser ? '你' : persona?.avatar ? <img src={persona.avatar} className="persona-avatar-img" /> : <Sparkles size={17} />}
                </div>
                <div className="message-content">
                  <span className="message-author">{isUser ? '你' : persona?.name ?? '助理'}</span>
                  {(msg as any).reply_to_id && <div className="reply-quote">↩ 回复消息</div>}
                  <MarkdownMessage content={msg.content} />
                  {!isUser && <button className="reply-btn" onClick={() => setReplyTo(msg)}>回复</button>}
                </div>
              </article>
            )
          })}
          {chat.draftAssistant ? (
            <article className="message-card assistant streaming">
              <div className="message-avatar"><Sparkles size={17} /></div>
              <div className="message-content">
                <span className="message-author">正在输入</span>
                <MarkdownMessage content={chat.draftAssistant} />
              </div>
            </article>
          ) : isRunning ? (
            <article className="message-card assistant">
              <div className="message-avatar"><Sparkles size={17} /></div>
              <div className="message-content">
                <div className="thinking-indicator"><LoaderCircle size={14} className="spin" /><span>{detectTargetPersona(content)?.name ?? '人格'}正在组织语言...</span></div>
              </div>
            </article>
          ) : null}
          {error && <div className="inline-error"><span>{error}</span><button onClick={() => setError(undefined)}><RotateCcw size={14} />关闭</button></div>}
        </div>

        <div className="composer-area">
          {replyTo && (
            <div className="reply-bar">
              <span>回复: {replyTo.content.slice(0, 40)}...</span>
              <button onClick={() => setReplyTo(null)}>✕</button>
            </div>
          )}
          <div className="at-hints">
            {groupPersonas.map((p) => (
              <button key={p.id} className="at-chip" onClick={() => setContent((prev) => `@${p.name} ${prev}`)}>
                @{p.name}
              </button>
            ))}
          </div>
          <form className="composer" onSubmit={submit}>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }}
              placeholder="输入消息，用 @人格名 指定回答者"
              rows={1}
              disabled={isRunning}
            />
            {isRunning && chat.runId
              ? <button type="button" className="send-button stop" onClick={() => cancelRun.mutate(chat.runId!)}><Square size={15} /></button>
              : <button className="send-button" disabled={!content.trim()}><ArrowUp size={18} /></button>
            }
          </form>
        </div>
      </section>

      <PersonaModal
        open={editingPersona !== null}
        editingPersona={editingPersona}
        showMaxReplies
        onClose={() => setEditingPersona(null)}
        onSave={(p) => {
          // 1. 同步本地人格库
          const customs = loadCustomPersonas()
          const idx = customs.findIndex((c) => c.id === p.id)
          if (idx >= 0) customs[idx] = p; else customs.push(p)
          saveCustomPersonas(customs)
          // 2. 同步会话里的人格快照（含轮次）
          if (editingPersona && conversationId) {
            void fetch(`/api/v1/conversations/${conversationId}/personas/${encodeURIComponent(editingPersona.name)}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                name: p.name, style: p.style, traits: p.traits,
                addressUser: p.addressUser, avatar: p.avatar, model: p.model,
                max_replies: p.maxReplies ?? 5,
              }),
            }).then(() => queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] }))
          }
        }}
      />
    </div>
  )
}
