import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageCircle, Sparkles, Trash2, Users } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../../api/client'
import { GroupCreateModal } from '../../components/GroupCreateModal'
import { getAllPersonas, type PersonaConfig } from '../../components/PersonaModal'
import { PageHeader } from '../../components/PageHeader'

export function CompanionPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [groupModalOpen, setGroupModalOpen] = useState(false)
  const [showNewChat, setShowNewChat] = useState(false)
  const personas = getAllPersonas()

  const conversations = useQuery({ queryKey: ['conversations'], queryFn: api.listConversations })
  const deleteConversation = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conversations'] }),
  })
  const socialChats = (conversations.data ?? []).filter((c: any) => c.is_group || (c.persona_ids && c.persona_ids.length > 0))

  async function startPrivateChat(persona: PersonaConfig) {
    const conv = await fetch('/api/v1/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: `和${persona.name}的私聊`,
        persona_ids: [{ name: persona.name, style: persona.style, traits: persona.traits, addressUser: persona.addressUser, avatar: persona.avatar, model: persona.model }],
      }),
    }).then((r) => r.json())
    localStorage.setItem(`persona_${conv.id}`, persona.id)
    await queryClient.invalidateQueries({ queryKey: ['conversations'] })
    navigate(`/companion/chat/${conv.id}`)
    setShowNewChat(false)
  }

  return (
    <div className="content-page">
      <PageHeader eyebrow="Companion" title="影界" description="你的分身们都在这里等你" />

      <div className="companion-actions">
        <button className="companion-action-btn" onClick={() => setShowNewChat(!showNewChat)}>
          <MessageCircle size={16} /> 新建私聊
        </button>
        <button className="companion-action-btn" onClick={() => setGroupModalOpen(true)}>
          <Users size={16} /> 创建群聊
        </button>
      </div>

      {showNewChat && (
        <div className="persona-picker">
          <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '0 0 10px' }}>选择一个人格开始私聊：</p>
          <div className="persona-picker-grid">
            {personas.map((p) => (
              <button key={p.id} className="persona-picker-item" onClick={() => startPrivateChat(p)}>
                <div className="persona-picker-avatar">
                  {p.avatar ? <img src={p.avatar} /> : <Sparkles size={16} />}
                </div>
                <div>
                  <strong>{p.name}</strong>
                  <span>{p.style?.slice(0, 15)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="companion-list">
        {socialChats.length === 0 && !showNewChat ? (
          <div className="empty-state" style={{ padding: '40px 20px' }}>
            <Sparkles size={40} />
            <strong>影界还很安静</strong>
            <p>创建一个私聊或群聊，让分身们活跃起来吧</p>
          </div>
        ) : null}
        {socialChats.map((conv: any) => {
          const isGroup = conv.is_group
          const personaId = localStorage.getItem(`persona_${conv.id}`)
          const persona = personaId ? personas.find((p) => p.id === personaId) : null
          return (
            <div key={conv.id} className="companion-chat-row">
              <button
                type="button"
                style={{ display: 'contents', font: 'inherit' }}
                onClick={() => navigate(isGroup ? `/group/${conv.id}` : `/companion/chat/${conv.id}`)}
              >
                <div className="companion-chat-avatar">
                  {isGroup ? <Users size={18} /> : persona?.avatar ? <img src={persona.avatar} /> : <Sparkles size={18} />}
                </div>
                <div className="companion-chat-info">
                  <strong>{conv.title || (persona?.name ? `和${persona.name}的私聊` : '对话')}</strong>
                  <span>{isGroup ? `${(conv.persona_ids || []).length} 人群聊` : persona?.style?.slice(0, 20) || ''}</span>
                </div>
                <time>{new Date(conv.updated_at).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}</time>
              </button>
              <button
                type="button"
                className="row-delete"
                title={isGroup ? '删除群聊' : '删除私聊'}
                onClick={(e) => {
                  e.stopPropagation()
                  if (window.confirm(isGroup ? '删除这个群聊？聊天记录将一并删除。' : '删除这个私聊？聊天记录将一并删除。')) {
                    deleteConversation.mutate(conv.id)
                  }
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          )
        })}
      </div>

      <GroupCreateModal
        open={groupModalOpen}
        onClose={() => setGroupModalOpen(false)}
        onCreate={async (title, selected, maxReplies) => {
          const conv = await fetch('/api/v1/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title,
              is_group: true,
              persona_ids: selected.map((p) => ({ name: p.name, style: p.style, traits: p.traits, addressUser: p.addressUser, avatar: p.avatar, model: p.model, max_replies: (p as any).max_replies ?? maxReplies })),
              max_auto_replies: maxReplies,
            }),
          }).then((r) => r.json())
          await queryClient.invalidateQueries({ queryKey: ['conversations'] })
          navigate(`/group/${conv.id}`)
        }}
      />
    </div>
  )
}
