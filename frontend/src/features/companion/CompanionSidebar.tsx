import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Sparkles, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { api } from '../../api/client'
import { getAllPersonas } from '../../components/PersonaModal'

export function CompanionSidebar({ activeId }: { activeId?: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const personas = getAllPersonas()
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: api.listConversations })
  const deleteConversation = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: async (_data, deletedId) => {
      await queryClient.invalidateQueries({ queryKey: ['conversations'] })
      if (deletedId === activeId) navigate('/companion')
    },
  })
  const socialChats = (conversations.data ?? []).filter((c: any) => c.is_group || (c.persona_ids && c.persona_ids.length > 0))

  return (
    <aside className="companion-sidebar">
      <div className="companion-sidebar-header">
        <strong>影界</strong>
        <button className="icon-button" onClick={() => navigate('/companion')} title="新建对话"><Plus size={16} /></button>
      </div>
      <div className="companion-sidebar-list">
        {socialChats.map((conv: any) => {
          const isGroup = conv.is_group
          const personaIds = conv.persona_ids || []
          const isActive = conv.id === activeId
          return (
            <div key={conv.id} className={`companion-sidebar-item ${isActive ? 'active' : ''}`}>
              <button
                type="button"
                style={{ display: 'contents' }}
                onClick={() => navigate(isGroup ? `/group/${conv.id}` : `/companion/chat/${conv.id}`)}
              >
                <div className="companion-sidebar-avatar">
                  {isGroup ? (
                    <div className="group-grid-avatar">
                      {personaIds.slice(0, 4).map((p: any, i: number) => {
                        const found = personas.find((x) => x.name === p.name)
                        return (
                          <div key={i} className="grid-cell">
                            {found?.avatar ? <img src={found.avatar} /> : <span>{p.name?.[0] ?? '?'}</span>}
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    (() => {
                      const p = personaIds[0]
                      const found = p ? personas.find((x) => x.name === p.name) : null
                      return found?.avatar ? <img src={found.avatar} className="persona-avatar-img" /> : <Sparkles size={16} />
                    })()
                  )}
                </div>
                <div className="companion-sidebar-info">
                  <span className="companion-sidebar-name">{conv.title || '对话'}</span>
                  <span className="companion-sidebar-preview">
                    {isGroup ? `${personaIds.length}人群聊` : personaIds[0]?.name ?? ''}
                  </span>
                </div>
                <time>{new Date(conv.updated_at).toLocaleDateString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</time>
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
    </aside>
  )
}
