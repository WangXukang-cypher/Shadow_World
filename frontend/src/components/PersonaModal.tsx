import { type FormEvent, useEffect, useRef, useState } from 'react'
import { Camera, X } from 'lucide-react'

export interface PersonaConfig {
  id: string
  name: string
  style: string
  traits: string
  addressUser: string
  avatar?: string
  model?: string
  isBuiltin?: boolean
  maxReplies?: number
}

export const BUILTIN_PERSONAS: PersonaConfig[] = [
  { id: 'buddy', name: '好伙伴', style: '平等对话的好朋友，轻松幽默，会开玩笑也会认真聊', traits: '真诚、有趣、随和、偶尔吐槽', addressUser: '你' },
  { id: 'bro', name: '小老弟', style: '把用户当大哥/大姐看待，语气尊重但不谄媚，会卖萌示弱', traits: '机灵、忠诚、接地气、会撒娇', addressUser: '哥' },
  { id: 'warm', name: '暖心搭子', style: '温柔治愈系，善于倾听，先共情再给建议，语气轻柔', traits: '温暖、细腻、有耐心、善解人意', addressUser: '亲爱的' },
]

const STORAGE_KEY = 'xiaoji_custom_personas'
const DELETED_KEY = 'xiaoji_deleted_personas'

export function loadCustomPersonas(): PersonaConfig[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function saveCustomPersonas(personas: PersonaConfig[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(personas))
}

function loadDeletedIds(): Set<string> {
  try {
    const raw = localStorage.getItem(DELETED_KEY)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch {
    return new Set()
  }
}

export function markPersonaDeleted(id: string): void {
  const deleted = loadDeletedIds()
  deleted.add(id)
  localStorage.setItem(DELETED_KEY, JSON.stringify([...deleted]))
}

export function getAllPersonas(): PersonaConfig[] {
  const customs = loadCustomPersonas()
  const deleted = loadDeletedIds()
  const customIds = new Set(customs.map((c) => c.id))
  const builtins = BUILTIN_PERSONAS.filter((b) => !customIds.has(b.id) && !deleted.has(b.id))
  return [...builtins, ...customs.filter((c) => !deleted.has(c.id))]
}

interface PersonaModalProps {
  open: boolean
  editingPersona?: PersonaConfig | null
  onClose: () => void
  onSave: (persona: PersonaConfig) => void
  onDelete?: (id: string) => void
  showMaxReplies?: boolean
}

export function PersonaModal({ open, editingPersona, onClose, onSave, onDelete, showMaxReplies }: PersonaModalProps) {
  const [name, setName] = useState('')
  const [style, setStyle] = useState('')
  const [traits, setTraits] = useState('')
  const [addressUser, setAddressUser] = useState('你')
  const [avatar, setAvatar] = useState<string | undefined>(undefined)
  const [model, setModel] = useState('default')
  const [maxReplies, setMaxReplies] = useState(5)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setName(editingPersona?.name ?? '')
      setStyle(editingPersona?.style ?? '')
      setTraits(editingPersona?.traits ?? '')
      setAddressUser(editingPersona?.addressUser ?? '你')
      setAvatar(editingPersona?.avatar)
      setModel(editingPersona?.model ?? 'default')
      setMaxReplies(editingPersona?.maxReplies ?? 5)
    }
  }, [open, editingPersona])

  function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setAvatar(reader.result as string)
    reader.readAsDataURL(file)
  }

  if (!open) return null

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim() || !style.trim()) return
    onSave({
      id: editingPersona?.id ?? `custom_${Date.now()}`,
      name: name.trim(),
      style: style.trim(),
      traits: traits.trim(),
      addressUser: addressUser.trim() || '你',
      avatar,
      model: model === 'default' ? undefined : model,
      maxReplies: showMaxReplies ? maxReplies : undefined,
    })
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{editingPersona ? '编辑人格' : '创建自定义人格'}</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="avatar-upload" onClick={() => fileRef.current?.click()}>
            {avatar ? <img src={avatar} className="avatar-preview" /> : <div className="avatar-placeholder"><Camera size={20} /><span>上传头像</span></div>}
            <input ref={fileRef} type="file" accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }} />
          </div>
          <div className="modal-field">
            <label>人格名称</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：毒舌闺蜜、知心大叔" maxLength={20} autoFocus />
          </div>
          <div className="modal-field">
            <label>对话风格</label>
            <input value={style} onChange={(e) => setStyle(e.target.value)} placeholder="如：犀利吐槽但关心你、慢条斯理给建议" maxLength={100} />
          </div>
          <div className="modal-field">
            <label>性格特点</label>
            <input value={traits} onChange={(e) => setTraits(e.target.value)} placeholder="如：直率、幽默、毒舌但善良" maxLength={100} />
          </div>
          <div className="modal-field">
            <label>对你的称呼</label>
            <input value={addressUser} onChange={(e) => setAddressUser(e.target.value)} placeholder="如：宝子、老板、兄弟" maxLength={20} />
          </div>
          <div className="modal-field">
            <label>使用模型</label>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="modal-select">
              <option value="default">默认（使用主模型）</option>
              <option value="group">群聊模型（未单独配置时用主模型）</option>
            </select>
            <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
              模型服务在"设置"页面选择并配置 API Key
            </span>
          </div>
          {showMaxReplies ? (
            <div className="modal-field">
              <label>自动回复轮次</label>
              <input
                type="number"
                min={1}
                max={20}
                value={maxReplies}
                onChange={(e) => setMaxReplies(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
              />
              <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
                群聊中被 @ 后最多自动回复几轮
              </span>
            </div>
          ) : null}
          <div className="modal-actions">
            {editingPersona && onDelete ? (
              <button type="button" className="modal-btn danger" onClick={() => { onDelete(editingPersona.id); onClose() }}>删除</button>
            ) : <span />}
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="button" className="modal-btn secondary" onClick={onClose}>取消</button>
              <button type="submit" className="modal-btn primary" disabled={!name.trim() || !style.trim()}>保存</button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
