import { type FormEvent, useState } from 'react'
import { X, Check } from 'lucide-react'
import { type PersonaConfig, getAllPersonas } from './PersonaModal'

interface GroupCreateModalProps {
  open: boolean
  onClose: () => void
  onCreate: (title: string, personas: Array<PersonaConfig & { max_replies: number }>, maxReplies: number) => void
}

export function GroupCreateModal({ open, onClose, onCreate }: GroupCreateModalProps) {
  const [title, setTitle] = useState('')
  const [maxReplies, setMaxReplies] = useState(5)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [perPersonaLimits, setPerPersonaLimits] = useState<Record<string, number>>({})
  const personas = getAllPersonas()

  if (!open) return null

  function toggle(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim() || selectedIds.size < 2) return
    const selected = personas.filter((p) => selectedIds.has(p.id)).map((p) => ({
      ...p,
      max_replies: perPersonaLimits[p.id] ?? maxReplies,
    }))
    onCreate(title.trim(), selected, maxReplies)
    setTitle('')
    setSelectedIds(new Set())
    setPerPersonaLimits({})
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '500px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>创建群聊</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-field">
            <label>群聊名称</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="如：摸鱼群、创意讨论组" maxLength={50} autoFocus />
          </div>

          <div className="modal-field">
            <label>选择人格成员（至少2个）</label>
            <div className="persona-select-grid">
              {personas.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`persona-select-item ${selectedIds.has(p.id) ? 'selected' : ''}`}
                  onClick={() => toggle(p.id)}
                >
                  <div className="persona-select-avatar">
                    {p.avatar ? <img src={p.avatar} /> : p.name[0]}
                  </div>
                  <span>{p.name}</span>
                  {selectedIds.has(p.id) && <Check size={14} className="check-icon" />}
                </button>
              ))}
            </div>
          </div>

          <div className="modal-field">
            <label>默认自动回复轮次（{maxReplies}轮）</label>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                type="range"
                min={1}
                max={100}
                value={maxReplies}
                onChange={(e) => setMaxReplies(Number(e.target.value))}
                style={{ flex: 1 }}
              />
              <input
                type="number"
                min={1}
                max={100}
                value={maxReplies}
                onChange={(e) => setMaxReplies(Math.min(100, Math.max(1, Number(e.target.value))))}
                style={{ width: '60px', border: '1px solid var(--line)', borderRadius: '8px', padding: '6px', textAlign: 'center' }}
              />
            </div>
            <div style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px' }}>
              每个人格可以单独设置（选中后下方调整）
            </div>
          </div>

          {selectedIds.size > 0 && (
            <div className="modal-field">
              <label>每人格独立轮次（可选）</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {personas.filter((p) => selectedIds.has(p.id)).map((p) => (
                  <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', minWidth: '60px' }}>{p.name}</span>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={perPersonaLimits[p.id] ?? maxReplies}
                      onChange={(e) => setPerPersonaLimits((prev) => ({ ...prev, [p.id]: Number(e.target.value) }))}
                      style={{ width: '60px', border: '1px solid var(--line)', borderRadius: '8px', padding: '5px', textAlign: 'center', fontSize: '12px' }}
                    />
                    <span style={{ fontSize: '10px', color: 'var(--muted)' }}>轮</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="modal-actions">
            <span style={{ fontSize: '12px', color: 'var(--muted)' }}>
              已选 {selectedIds.size} 个人格
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="button" className="modal-btn secondary" onClick={onClose}>取消</button>
              <button type="submit" className="modal-btn primary" disabled={!title.trim() || selectedIds.size < 2}>
                创建群聊
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
