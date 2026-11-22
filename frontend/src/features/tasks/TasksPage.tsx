import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarClock, Check, Plus, Trash2 } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import { api } from '../../api/client'
import { EmptyState } from '../../components/EmptyState'
import { PageHeader } from '../../components/PageHeader'

export function TasksPage() {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [remindAt, setRemindAt] = useState('')
  const tasks = useQuery({ queryKey: ['tasks'], queryFn: api.listTasks })
  const create = useMutation({ mutationFn: () => api.createTask(title.trim(), remindAt ? new Date(remindAt).toISOString() : undefined), onSuccess: async () => { setTitle(''); setRemindAt(''); await queryClient.invalidateQueries({ queryKey: ['tasks'] }) } })
  const complete = useMutation({ mutationFn: (id: string) => api.completeTask(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }) })
  const deleteTask = useMutation({ mutationFn: (id: string) => api.deleteTask(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }) })

  function submit(event: FormEvent) { event.preventDefault(); if (title.trim()) create.mutate() }

  return <div className="content-page">
    <PageHeader eyebrow="Task tracking" title="待办与提醒" description="点击复选框完成待办，点击垃圾桶删除。" />
    <form className="task-create-card" onSubmit={submit}><div><label>待办内容</label><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：整理本周项目进展" /></div><div><label>提醒时间（可选）</label><input type="datetime-local" value={remindAt} onChange={(event) => setRemindAt(event.target.value)} /></div><button disabled={!title.trim() || create.isPending}><Plus size={16} />创建待办</button></form>
    {tasks.data?.length ? <div className="task-list">{tasks.data.map((item) => <article className="task-row" key={item.id}>
      <button className="task-check" title="标记完成" onClick={() => complete.mutate(item.id)}><Check size={14} /></button>
      <div><h3>{item.title}</h3><p>{item.remind_at ? `提醒：${new Date(item.remind_at).toLocaleString('zh-CN')}` : '未设置提醒时间'}</p></div>
      <span className="status-chip">{item.status}</span>
      <button className="row-delete" onClick={() => { if (window.confirm('删除这个待办？')) deleteTask.mutate(item.id) }}><Trash2 size={14} /></button>
    </article>)}</div> : <EmptyState icon={CalendarClock} title="没有未完成待办" description={'可以在对话里说"提醒我明天 10:00 交周报"。'} />}
  </div>
}
