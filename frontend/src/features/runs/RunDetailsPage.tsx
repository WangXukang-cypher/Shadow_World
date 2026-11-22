import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock3, Cpu, Route, Wrench } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../../api/client'
import { EmptyState } from '../../components/EmptyState'
import { PageHeader } from '../../components/PageHeader'

export function RunDetailsPage() {
  const { runId } = useParams()
  const run = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) =>
      ['completed', 'failed', 'cancelled'].includes(query.state.data?.status ?? '') ? false : 1000,
  })
  if (run.isLoading) {
    return <div className="content-page"><EmptyState icon={Clock3} title="正在读取运行详情" description="请稍候。" /></div>
  }
  if (!run.data) {
    return <div className="content-page"><EmptyState icon={Clock3} title="运行不存在" description="该运行可能已被清理。" /></div>
  }
  const item = run.data
  return <div className="content-page">
    <PageHeader eyebrow="Run inspector" title="运行详情" description="展示可审计的模型、工具和 Token 元数据，不包含隐藏思维链或敏感 Prompt。" actions={<Link className="text-button" to={`/chat/${item.conversation_id}`}><ArrowLeft size={15} />返回对话</Link>} />
    <div className="run-metric-grid">
      <article><Cpu size={18} /><span>模型</span><strong>{item.model_name || 'unknown'}</strong></article>
      <article><Route size={18} /><span>最终路由</span><strong>{item.route || 'chat'}</strong></article>
      <article><Clock3 size={18} /><span>状态 / 轮次</span><strong>{item.status} · {item.iteration_count}</strong></article>
      <article><span className="token-symbol">T</span><span>Token</span><strong>{item.prompt_tokens} / {item.completion_tokens}</strong></article>
    </div>
    <section className="run-section"><h2><Wrench size={18} />工具调用</h2>
      {item.tool_calls.length ? <div className="run-tool-list">{item.tool_calls.map((tool) => <article key={tool.id}><div><strong>{tool.tool_name}</strong><span>{tool.side_effect} · {tool.status}</span></div><div><span>{tool.latency_ms ?? 0} ms</span>{tool.error_code ? <span className="error-text">{tool.error_code}</span> : null}</div></article>)}</div> : <p className="muted">本轮没有调用工具。</p>}
    </section>
    <section className="run-section"><h2>时间线</h2><dl className="detail-list"><div><dt>开始</dt><dd>{new Date(item.created_at).toLocaleString('zh-CN')}</dd></div><div><dt>结束</dt><dd>{item.completed_at ? new Date(item.completed_at).toLocaleString('zh-CN') : '运行中'}</dd></div><div><dt>错误码</dt><dd>{item.error_code || '无'}</dd></div></dl></section>
  </div>
}
