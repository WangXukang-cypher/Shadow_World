import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, LoaderCircle, MessageCircle, Pencil, Plus, RotateCcw, Square, Trash2, Wrench, Sparkles } from 'lucide-react'
import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { api, ApiError } from '../../api/client'
import { EmptyState } from '../../components/EmptyState'
import { MarkdownMessage } from '../../components/MarkdownMessage'
import { PersonaModal, type PersonaConfig, BUILTIN_PERSONAS, loadCustomPersonas, saveCustomPersonas, getAllPersonas, markPersonaDeleted } from '../../components/PersonaModal'
import { useChatStore } from '../../stores/chatStore'
import type { Message } from '../../types/api'
import { useRunStream } from './useRunStream'

function localUserMessage(conversationId: string, content: string, seq: number): Message {
  return { id: `local-${Date.now()}`, user_id: 'local', conversation_id: conversationId, role: 'user', seq, content, status: 'pending', created_at: new Date().toISOString() }
}

export function ChatPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [error, setError] = useState<string>()
  const [personas, setPersonas] = useState<PersonaConfig[]>(getAllPersonas)
  const [activePersonaId, setActivePersonaId] = useState(() => localStorage.getItem('preferred_persona') ?? 'buddy')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingPersona, setEditingPersona] = useState<PersonaConfig | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const chat = useChatStore()
  const setConversation = useChatStore((state) => state.setConversation)
  useRunStream(chat.runId)

  const activePersona = personas.find((p) => p.id === activePersonaId) ?? BUILTIN_PERSONAS[0]

  // 会话绑定人格：切换会话时恢复该会话上次使用的人格
  useEffect(() => {
    if (conversationId) {
      const stored = localStorage.getItem(`persona_${conversationId}`)
      if (stored) setActivePersonaId(stored)
    }
  }, [conversationId])

  // 发消息时保存人格绑定
  function bindPersonaToConversation(convId: string) {
    localStorage.setItem(`persona_${convId}`, activePersonaId)
  }

  // 获取某条消息应显示的人格（从会话绑定获取，不依赖当前选择）
  function getMessagePersona(): PersonaConfig {
    if (!conversationId) return activePersona
    const storedId = localStorage.getItem(`persona_${conversationId}`)
    if (storedId) {
      const found = personas.find((p) => p.id === storedId)
      if (found) return found
    }
    return activePersona
  }

  const displayPersona = conversationId ? getMessagePersona() : activePersona

  const conversations = useQuery({ queryKey: ['conversations'], queryFn: api.listConversations })
  const detail = useQuery({ queryKey: ['conversation', conversationId], queryFn: () => api.getConversation(conversationId!), enabled: Boolean(conversationId) })
  const createConversation = useMutation({ mutationFn: () => api.createConversation(), onSuccess: async (item) => { await queryClient.invalidateQueries({ queryKey: ['conversations'] }); navigate(`/chat/${item.id}`) } })
  const sendMessage = useMutation({ mutationFn: ({ id, text, p }: { id: string; text: string; p: PersonaConfig }) => api.sendMessage(id, text, { name: p.name, style: p.style, traits: p.traits, addressUser: p.addressUser, model: p.model }) })
  const deleteConversation = useMutation({ mutationFn: (id: string) => api.deleteConversation(id), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['conversations'] }); if (conversationId) navigate('/chat') } })
  const cancelRun = useMutation({ mutationFn: (runId: string) => api.cancelRun(runId) })

  useEffect(() => {
    if (detail.data && detail.data.id !== chat.conversationId) {
      setConversation(detail.data.id, detail.data.messages)
    }
  }, [detail.data, chat.conversationId, setConversation])

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [chat.messages, chat.draftAssistant, chat.tools])

  const orderedMessages = useMemo(() => [...chat.messages].sort((a, b) => a.seq - b.seq), [chat.messages])
  const isRunning = ['connecting', 'streaming', 'reconnecting'].includes(chat.runStage)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const text = content.trim()
    if (!text || isRunning) return
    setError(undefined)
    try {
      let id = conversationId
      if (!id) {
        const created = await createConversation.mutateAsync()
        id = created.id
      }
      chat.addUserMessage(localUserMessage(id, text, Math.max(0, ...chat.messages.map((item) => item.seq)) + 1))
      setContent('')
      const run = await sendMessage.mutateAsync({ id, text, p: activePersona })
      bindPersonaToConversation(id)
      chat.beginRun(run.id)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '发送失败，请稍后重试。')
    }
  }

  return <div className="chat-layout">
    <aside className="conversation-panel">
      <div className="panel-heading"><div><span className="eyebrow">事界</span><h2>工作台</h2></div><button className="icon-button" aria-label="新建会话" onClick={() => createConversation.mutate()}><Plus size={18} /></button></div>
      <div className="conversation-list">
        {conversations.isLoading ? <span className="muted">加载会话中…</span> : null}
        {conversations.data?.filter((item) => !(item as any).is_group && !(item as any).persona_ids?.length).map((item) => <div key={item.id} className={item.id === conversationId ? 'conversation-row active' : 'conversation-row'}><button style={{display:'contents'}} onClick={() => navigate(`/chat/${item.id}`)}><MessageCircle size={16} /><span>{item.title || '新会话'}</span></button><time>{new Date(item.updated_at).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}</time><button className="row-delete" onClick={(e) => { e.stopPropagation(); if(confirm('删除这个会话？')) deleteConversation.mutate(item.id) }}><Trash2 size={13}/></button></div>)}
      </div>
    </aside>
    <section className="chat-main">
      <header className="chat-header"><div><span className="eyebrow">Conversation</span><h1>{detail.data?.title || '开始一段新对话'}</h1></div><div className="chat-header-actions">{chat.runId ? <button className="text-button" onClick={() => navigate(`/runs/${chat.runId}`)}>运行详情</button> : null}<div className={`run-pill ${chat.runStage}`}><span />{chat.runStage === 'idle' || chat.runStage === 'completed' ? '就绪' : chat.runStage === 'cancelled' ? '已停止' : chat.runStage === 'reconnecting' ? '正在恢复连接' : chat.runStage === 'failed' ? '运行失败' : '助理处理中'}</div></div></header>
      <div className="message-scroll" ref={scrollRef}>
        {!conversationId && orderedMessages.length === 0 ? <div className="welcome-block"><div className="welcome-icon"><Sparkles size={28} /></div><span className="eyebrow">你的社交记忆搭子</span><h2>今天有什么想聊的？</h2><p>随便聊聊就好，我会记住你提到的重要的人和事～</p><div className="prompt-grid">{['今天跟同事吃饭了，聊了好多','帮我记住小王下周二生日','我答应朋友周末请他吃饭','最近心情有点烦'].map((prompt) => <button key={prompt} onClick={() => setContent(prompt)}>{prompt}</button>)}</div></div> : null}
        {conversationId && !detail.isLoading && orderedMessages.length === 0 ? <EmptyState icon={MessageCircle} title="这段对话还没有消息" description="发送一句话开始吧。" /> : null}
        {orderedMessages.map((message) => { const msgPersonaName = (message as any).persona_name; const showPersona = msgPersonaName ? (personas.find(p => p.name === msgPersonaName) ?? { name: msgPersonaName, avatar: undefined }) : displayPersona; return <article key={message.id} className={`message-card ${message.role}`}><div className="message-avatar">{message.role === 'user' ? '你' : (showPersona as any).avatar ? <img src={(showPersona as any).avatar} className="persona-avatar-img" /> : <Sparkles size={17} />}</div><div className="message-content"><span className="message-author">{message.role === 'user' ? '你' : showPersona.name}</span><MarkdownMessage content={message.content} /></div></article>})}
        {chat.tools.length ? <div className="tool-stack">{chat.tools.map((tool) => <div key={tool.id} className="tool-card"><Wrench size={15} /><span>{tool.tool === 'create_memory' ? '正在保存记忆' : tool.tool === 'create_task' ? '正在创建待办' : tool.tool}</span>{tool.status === 'running' ? <LoaderCircle size={15} className="spin" /> : <span className="tool-done">完成</span>}</div>)}</div> : null}
        {chat.draftAssistant ? <article className="message-card assistant streaming"><div className="message-avatar">{displayPersona.avatar ? <img src={displayPersona.avatar} className="persona-avatar-img" /> : <Sparkles size={17} />}</div><div className="message-content"><span className="message-author">{displayPersona.name} · 正在输入</span><MarkdownMessage content={chat.draftAssistant} /></div></article> : isRunning && !chat.draftAssistant ? <article className="message-card assistant"><div className="message-avatar">{displayPersona.avatar ? <img src={displayPersona.avatar} className="persona-avatar-img" /> : <Sparkles size={17} />}</div><div className="message-content"><span className="message-author">{displayPersona.name}</span><div className="thinking-indicator"><LoaderCircle size={14} className="spin" /><span>{displayPersona.name}正在思考中...</span></div></div></article> : null}
        {error ? <div className="inline-error"><span>{error}</span><button onClick={() => setError(undefined)}><RotateCcw size={14} />关闭</button></div> : null}
      </div>
      <div className="composer-area">
        <form className="composer" onSubmit={submit}><textarea value={content} onChange={(event) => setContent(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} placeholder="输入消息，Shift + Enter 换行" rows={1} disabled={isRunning} /><div className="composer-actions"><button type="button" className="persona-selector" onClick={(e) => { const el = e.currentTarget.nextElementSibling as HTMLElement; el.style.display = el.style.display === 'flex' ? 'none' : 'flex' }}>{activePersona.name} ▾</button><div className="persona-dropdown">{personas.map((p) => <div key={p.id} style={{display:'flex',alignItems:'center',gap:'4px'}}><button type="button" style={{flex:1}} className={p.id === activePersonaId ? 'active' : ''} onClick={(e) => { setActivePersonaId(p.id); ((e.currentTarget.parentElement as HTMLElement).parentElement as HTMLElement).style.display = 'none' }}>{p.name}</button><button type="button" style={{border:0,background:'transparent',padding:'4px',color:'var(--muted)'}} onClick={(e) => { setEditingPersona(p); setModalOpen(true); ((e.currentTarget.parentElement as HTMLElement).parentElement as HTMLElement).style.display = 'none' }}><Pencil size={12}/></button></div>)}<button type="button" style={{color:'var(--accent)',borderTop:'1px solid var(--line)',marginTop:'4px',paddingTop:'8px'}} onClick={(e) => { setEditingPersona(null); setModalOpen(true); ((e.currentTarget.parentElement as HTMLElement)).style.display = 'none' }}>+ 新建人格</button></div>{isRunning && chat.runId ? <button type="button" className="send-button stop" aria-label="停止生成" onClick={() => cancelRun.mutate(chat.runId!)}><Square size={15} /></button> : <button className="send-button" disabled={!content.trim()} aria-label="发送消息"><ArrowUp size={18} /></button>}</div></form>
      </div>
      <PersonaModal
        open={modalOpen}
        editingPersona={editingPersona}
        onClose={() => { setModalOpen(false); setEditingPersona(null) }}
        onSave={(p) => {
          const customs = loadCustomPersonas()
          const idx = customs.findIndex((c) => c.id === p.id)
          if (idx >= 0) customs[idx] = p; else customs.push(p)
          saveCustomPersonas(customs)
          setPersonas(getAllPersonas())
          setActivePersonaId(p.id)
        }}
        onDelete={(id) => {
          markPersonaDeleted(id)
          const customs = loadCustomPersonas().filter((c) => c.id !== id)
          saveCustomPersonas(customs)
          setPersonas(getAllPersonas())
          if (activePersonaId === id) setActivePersonaId('buddy')
        }}
      />
    </section>
  </div>
}
