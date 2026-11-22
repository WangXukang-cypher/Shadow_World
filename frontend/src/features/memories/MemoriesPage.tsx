import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Brain, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { type FormEvent, useMemo, useState } from 'react'

import { api } from '../../api/client'
import { EmptyState } from '../../components/EmptyState'
import { PageHeader } from '../../components/PageHeader'

export function MemoriesPage() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [content, setContent] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const memories = useQuery({ queryKey: ['memories'], queryFn: api.listMemories })
  const create = useMutation({ mutationFn: (value: string) => api.createMemory(value), onSuccess: async () => { setContent(''); await queryClient.invalidateQueries({ queryKey: ['memories'] }) } })
  const deleteMemory = useMutation({ mutationFn: (id: string) => api.deleteMemory(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memories'] }) })
  const updateMemory = useMutation({
    mutationFn: ({ id, newContent }: { id: string; newContent: string }) =>
      fetch(`/api/v1/memories/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: newContent }) }).then((r) => r.json()),
    onSuccess: () => { setEditingId(null); queryClient.invalidateQueries({ queryKey: ['memories'] }) },
  })
  const filtered = useMemo(() => memories.data?.filter((item) => `${item.subject}${item.content}${item.type}`.toLowerCase().includes(query.toLowerCase())) ?? [], [memories.data, query])
  function submit(event: FormEvent) { event.preventDefault(); if (content.trim()) create.mutate(content.trim()) }

  return <div className="content-page">
    <PageHeader eyebrow="Memory control" title="记忆中心" description="查看、编辑和删除助理保存的长期记忆。" />
    <section className="toolbar-card"><label className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索记忆" /></label><form className="quick-create" onSubmit={submit}><input value={content} onChange={(event) => setContent(event.target.value)} placeholder="手动添加一条记忆" /><button disabled={!content.trim() || create.isPending}><Plus size={16} />添加</button></form></section>
    {filtered.length ? <div className="memory-grid">{filtered.map((item) => <article className="memory-card" key={item.id}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="memory-type">{item.type}</div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button className="memory-action" title="编辑" onClick={() => { setEditingId(item.id); setEditContent(item.content) }}><Pencil size={12} /></button>
          <button className="memory-action delete" title="删除" onClick={() => { if (window.confirm('删除这条记忆？')) deleteMemory.mutate(item.id) }}><Trash2 size={12} /></button>
        </div>
      </div>
      <h3>{item.subject}</h3>
      {editingId === item.id ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} rows={3} style={{ border: '1px solid var(--accent)', borderRadius: '8px', padding: '8px', fontSize: '13px', resize: 'vertical' }} />
          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
            <button className="modal-btn secondary" onClick={() => setEditingId(null)} style={{ padding: '5px 10px', fontSize: '11px' }}>取消</button>
            <button className="modal-btn primary" onClick={() => updateMemory.mutate({ id: item.id, newContent: editContent })} style={{ padding: '5px 10px', fontSize: '11px' }}>保存</button>
          </div>
        </div>
      ) : (
        <p>{item.content}</p>
      )}
      <footer><span>{item.status}</span><time>{new Date(item.updated_at).toLocaleString('zh-CN')}</time></footer>
    </article>)}</div> : <EmptyState icon={Brain} title="还没有长期记忆" description={'在对话中说"记住……"，或者在上方手动添加。'} />}
  </div>
}
