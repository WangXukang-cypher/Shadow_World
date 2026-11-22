import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { useState } from 'react'

import { BUILTIN_PERSONAS } from './PersonaModal'

/** 新访客引导：填昵称 + 选初始人格。服务端通过 cookie 识别匿名用户。 */
export function OnboardingModal({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [personaId, setPersonaId] = useState(BUILTIN_PERSONAS[0].id)
  const [error, setError] = useState('')

  const finish = useMutation({
    mutationFn: (displayName: string) =>
      fetch('/api/v1/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: displayName }),
      }).then((r) => {
        if (!r.ok) throw new Error('保存失败')
        return r.json()
      }),
    onSuccess: () => {
      localStorage.setItem('preferred_persona', personaId)
      queryClient.invalidateQueries({ queryKey: ['me'] })
      onDone()
    },
  })

  const start = () => {
    const trimmed = name.trim()
    if (!trimmed) {
      setError('给自己起个名字吧，伙伴们会这样称呼你')
      return
    }
    finish.mutate(trimmed)
  }

  return (
    <div className="modal-overlay" style={{ zIndex: 200 }}>
      <div className="modal-card onboarding-card">
        <div className="onboarding-hero">
          <div className="brand-mark"><Sparkles size={18} /></div>
          <h2>欢迎来到影伴</h2>
          <p>一个有人格记忆的 AI 伙伴。先简单认识一下：</p>
        </div>

        <div className="modal-field">
          <label>怎么称呼你？</label>
          <input
            autoFocus
            value={name}
            maxLength={30}
            onChange={(e) => { setName(e.target.value); setError('') }}
            onKeyDown={(e) => { if (e.key === 'Enter') start() }}
            placeholder="比如：小明"
          />
          {error ? <span className="field-error">{error}</span> : null}
        </div>

        <div className="modal-field">
          <label>选一个初始伙伴（之后可以随时换）</label>
          <div className="onboarding-personas">
            {BUILTIN_PERSONAS.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`provider-option${personaId === p.id ? ' active' : ''}`}
                onClick={() => setPersonaId(p.id)}
              >
                <span className="provider-radio" />
                <div>
                  <strong>{p.name}</strong>
                  <em>{p.traits.split('、').slice(0, 3).join(' · ')}</em>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="modal-actions">
          <button className="link-button" onClick={() => finish.mutate('访客')} disabled={finish.isPending}>
            先随便看看
          </button>
          <button className="modal-btn primary" onClick={start} disabled={finish.isPending}>
            {finish.isPending ? '正在进入…' : '开始体验'}
          </button>
        </div>
      </div>
    </div>
  )
}
