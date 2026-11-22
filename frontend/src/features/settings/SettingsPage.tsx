import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Database, KeyRound, Save, Server } from 'lucide-react'
import { useEffect, useState } from 'react'

import { api } from '../../api/client'
import { PageHeader } from '../../components/PageHeader'

interface ProviderPreset {
  label: string
  description: string
  base_url: string
  model: string
}

interface ProviderSettingsData {
  llm_provider: string
  llm_model: string
  llm_api_key_set: boolean
  fallback_available: boolean
  presets: Record<string, ProviderPreset>
}

const FALLBACK_PRESETS: Record<string, ProviderPreset> = {
  modelscope: { label: 'ModelScope', description: 'Qwen', base_url: 'https://api-inference.modelscope.cn/v1', model: 'Qwen/Qwen3.8-27B' },
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30000 })
  const provider = useQuery<ProviderSettingsData>({ queryKey: ['provider-settings'], queryFn: () => api.fetch<ProviderSettingsData>('/settings/provider') })

  const [selected, setSelected] = useState('modelscope')
  const [apiKey, setApiKey] = useState('')
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState('')

  const presets = provider.data?.presets ?? FALLBACK_PRESETS
  const presetKeys = Object.keys(presets)

  useEffect(() => {
    if (provider.data && presetKeys.includes(provider.data.llm_provider)) {
      setSelected(provider.data.llm_provider)
    }
  }, [provider.data])

  const saveProvider = useMutation({
    mutationFn: () => fetch('/api/v1/settings/provider', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ llm_provider: selected, llm_api_key: apiKey }),
    }).then(async (r) => {
      const body = await r.json().catch(() => ({}))
      if (!r.ok) {
        throw new Error(body?.error?.message ?? `保存失败（${r.status}）`)
      }
      return body
    }),
    onSuccess: () => {
      setApiKey('')
      setSaveError('')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
      queryClient.invalidateQueries({ queryKey: ['provider-settings'] })
      queryClient.invalidateQueries({ queryKey: ['health'] })
    },
    onError: (err: Error) => setSaveError(err.message),
  })

  const currentPreset = presets[selected]

  const modelStatus = provider.data?.llm_api_key_set
    ? (presets[provider.data.llm_provider]
        ? `你的 ${presets[provider.data.llm_provider].label} · ${presets[provider.data.llm_provider].description}`
        : provider.data.llm_model || '自定义模型')
    : provider.data?.fallback_available
      ? '服务端公共模型（可填写自己的 Key 替换）'
      : '未配置（mock）'

  return <div className="content-page">
    <PageHeader eyebrow="System" title="设置" description="配置你自己的模型服务，Key 只保存在你的账户下。" />

    <div className="settings-grid">
      <section className="settings-card"><Server size={20} /><div><span>后端服务</span><strong>{health.data?.status === 'ok' ? '运行正常' : health.isLoading ? '检查中' : '不可用'}</strong></div><CheckCircle2 size={18} className={health.data ? 'success' : 'muted-icon'} /></section>
      <section className="settings-card"><Database size={20} /><div><span>数据库</span><strong>{health.data?.database ?? '检查中'}</strong></div></section>
      <section className="settings-card"><KeyRound size={20} /><div><span>当前模型</span><strong>{modelStatus}</strong></div>{provider.data?.llm_api_key_set ? <CheckCircle2 size={18} className="success" /> : null}</section>
    </div>

    <div style={{ marginTop: '24px' }}>
      <h3 style={{ margin: '0 0 6px' }}>我的模型服务</h3>
      <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '0 0 14px' }}>选择一个模型服务并填写你自己的 API Key。Key 仅保存到你的账户，其他用户不可见、也不共享。</p>

      <div className="provider-options">
        {presetKeys.map((key) => {
          const preset = presets[key]
          const active = selected === key
          return <button
            key={key}
            type="button"
            className={`provider-option${active ? ' active' : ''}`}
            onClick={() => setSelected(key)}
          >
            <span className="provider-radio" />
            <div>
              <strong>{preset.label}</strong>
              <em>{preset.description}</em>
            </div>
          </button>
        })}
      </div>

      <div className="settings-form" style={{ marginTop: '16px' }}>
        <div className="modal-field">
          <label>{currentPreset ? `${currentPreset.label} API Key` : 'API Key'}</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setSaveError('') }}
            placeholder={provider.data?.llm_api_key_set ? '已配置（留空则沿用现有 Key）' : '粘贴你的 API Key'}
          />
        </div>
      </div>

      {saveError ? <p style={{ color: 'var(--danger)', fontSize: '12px', margin: '10px 0 0' }}>{saveError}</p> : null}

      <button className="modal-btn primary" style={{ marginTop: '16px' }} onClick={() => saveProvider.mutate()} disabled={saveProvider.isPending || (!apiKey && !provider.data?.llm_api_key_set)}>
        <Save size={14} /> {saved ? '已保存，下次对话生效！' : '保存配置'}
      </button>
    </div>
  </div>
}
