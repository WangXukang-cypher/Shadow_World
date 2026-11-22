import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, LoaderCircle, Pencil, RotateCcw, Sparkles, Square } from 'lucide-react'
import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'

import { api, ApiError } from '../../api/client'
import { MarkdownMessage } from '../../components/MarkdownMessage'
import { type PersonaConfig, PersonaModal, getAllPersonas, loadCustomPersonas, saveCustomPersonas } from '../../components/PersonaModal'
import { useChatStore } from '../../stores/chatStore'
import { useRunStream } from '../chat/useRunStream'
import { CompanionSidebar } from './CompanionSidebar'

export function CompanionChatPage() {
  const { conversationId } = useParams()
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [error, setError] = useState<string>()
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

  const persona: PersonaConfig | undefined = useMemo(() => {
    const ids = (detail.data as any)?.persona_ids as Array<any> | undefined
    if (ids && ids.length > 0) {
      const p = ids[0]
      return personas.find((x) => x.name === p.name) ?? { id: 'conv', name: p.name, style: p.style, traits: p.traits, addressUser: p.addressUser, avatar: p.avatar, model: p.model }
    }
    return personas[0]
  }, [detail.data, personas])

  const sendMessage = useMutation({
    mutationFn: ({ text }: { text: string }) =>
      api.sendMessage(conversationId!, text, persona ? { name: persona.name, style: persona.style, traits: persona.traits, addressUser: persona.addressUser, model: persona.model } : undefined),
  })
  const cancelRun = useMutation({ mutationFn: (runId: string) => api.cancelRun(runId) })

  useEffect(() => {
    if (detail.data && detail.data.id !== chat.conversationId) {
      setConversation(detail.data.id, detail.data.messages)
    }
  }, [detail.data, chat.conversationId, setConversation])
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [chat.messages, chat.draftAssistant])

  const orderedMessages = useMemo(() => [...chat.messages].sort((a, b) => a.seq - b.seq), [chat.messages])
  const isRunning = ['connecting', 'streaming', 'reconnecting'].includes(chat.runStage)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const text = content.trim()
    if (!text || isRunning || !conversationId) return
    setError(undefined)
    try {
      chat.addUserMessage({
        id: `local-${Date.now()}`, user_id: 'local', conversation_id: conversationId,
        role: 'user', seq: Math.max(0, ...chat.messages.map((m) => m.seq)) + 1,
        content: text, status: 'pending', created_at: new Date().toISOString(),
      })
      setContent('')
      const run = await sendMessage.mutateAsync({ text })
      chat.beginRun(run.id)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '发送失败')
    }
  }

  return (
    <div className="chat-layout">
      <CompanionSidebar activeId={conversationId} />
      <section className="chat-main">
        <header className="chat-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              className="companion-chat-avatar"
              style={{ width: '36px', height: '36px', cursor: 'pointer', position: 'relative' }}
              title={`${persona?.name ?? '人格'}（点击编辑人格）`}
              onClick={() => persona && setEditingPersona(persona)}
            >
              {persona?.avatar ? <img src={persona.avatar} className="persona-avatar-img" /> : <Sparkles size={18} />}
              <span className="avatar-edit-badge"><Pencil size={9} /></span>
            </div>
            <div>
              <span className="eyebrow">影界 · 私聊</span>
              <h1 style={{ fontSize: '18px' }}>{persona?.name ?? '对话'}</h1>
            </div>
          </div>
          <div className={`run-pill ${chat.runStage}`}><span />{chat.runStage === 'idle' || chat.runStage === 'completed' ? '在线' : '输入中...'}</div>
        </header>

        <div className="message-scroll" ref={scrollRef}>
          {orderedMessages.map((msg) => (
            <article key={msg.id} className={`message-card ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? '你' : persona?.avatar ? <img src={persona.avatar} className="persona-avatar-img" /> : <Sparkles size={17} />}
              </div>
              <div className="message-content">
                <span className="message-author">{msg.role === 'user' ? '你' : persona?.name ?? '助理'}</span>
                <MarkdownMessage content={msg.content} />
              </div>
            </article>
          ))}
          {chat.draftAssistant ? (
            <article className="message-card assistant streaming">
              <div className="message-avatar">{persona?.avatar ? <img src={persona.avatar} className="persona-avatar-img" /> : <Sparkles size={17} />}</div>
              <div className="message-content"><span className="message-author">{persona?.name} · 输入中</span><MarkdownMessage content={chat.draftAssistant} /></div>
            </article>
          ) : isRunning ? (
            <article className="message-card assistant">
              <div className="message-avatar">{persona?.avatar ? <img src={persona.avatar} className="persona-avatar-img" /> : <Sparkles size={17} />}</div>
              <div className="message-content"><div className="thinking-indicator"><LoaderCircle size={14} className="spin" /><span>{persona?.name}正在想...</span></div></div>
            </article>
          ) : null}
          {error && <div className="inline-error"><span>{error}</span><button onClick={() => setError(undefined)}><RotateCcw size={14} />关闭</button></div>}
        </div>

        <div className="composer-area">
          <form className="composer" onSubmit={submit}>
            <textarea value={content} onChange={(e) => setContent(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} placeholder={`和${persona?.name ?? ''}聊点什么...`} rows={1} disabled={isRunning} />
            {isRunning && chat.runId ? <button type="button" className="send-button stop" onClick={() => cancelRun.mutate(chat.runId!)}><Square size={15} /></button> : <button className="send-button" disabled={!content.trim()}><ArrowUp size={18} /></button>}
          </form>
        </div>
      </section>

      <PersonaModal
        open={editingPersona !== null}
        editingPersona={editingPersona}
        onClose={() => setEditingPersona(null)}
        onSave={(p) => {
          // 1. 同步本地人格库
          const customs = loadCustomPersonas()
          const idx = customs.findIndex((c) => c.id === p.id)
          if (idx >= 0) customs[idx] = p; else customs.push(p)
          saveCustomPersonas(customs)
          // 2. 同步会话里的人格快照
          if (editingPersona && conversationId) {
            void fetch(`/api/v1/conversations/${conversationId}/personas/${encodeURIComponent(editingPersona.name)}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                name: p.name, style: p.style, traits: p.traits,
                addressUser: p.addressUser, avatar: p.avatar, model: p.model,
              }),
            }).then(() => queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] }))
          }
        }}
      />
    </div>
  )
}
