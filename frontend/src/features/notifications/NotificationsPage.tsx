import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Trash2 } from 'lucide-react'

import { api } from '../../api/client'
import { EmptyState } from '../../components/EmptyState'
import { PageHeader } from '../../components/PageHeader'

export function NotificationsPage() {
  const queryClient = useQueryClient()
  const notifications = useQuery({ queryKey: ['notifications'], queryFn: () => api.listNotifications() })

  const deleteOne = useMutation({
    mutationFn: (id: number) => api.deleteNotification(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const clearAll = useMutation({
    mutationFn: () => api.clearNotifications(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  return <div className="content-page"><PageHeader eyebrow="Notification history" title="通知中心" description="提醒会先持久化，再通过独立 SSE 推送；短暂断线后仍能在这里查看。" />
    {notifications.data?.length ? (
      <>
        <div className="list-toolbar">
          <button onClick={() => { if (window.confirm('清空全部通知？')) clearAll.mutate() }} disabled={clearAll.isPending}>
            <Trash2 size={13} /> 清空全部
          </button>
        </div>
        <div className="notification-list">{[...notifications.data].reverse().map((item) => <article className="notification-row" key={item.id}>
          <div className="notification-icon"><Bell size={18} /></div>
          <div><h3>{String(item.payload.title ?? item.type)}</h3><p>{item.type}</p></div>
          <time>{new Date(item.created_at).toLocaleString('zh-CN')}</time>
          <button className="row-delete" title="删除这条通知" onClick={() => deleteOne.mutate(item.id)}><Trash2 size={14} /></button>
        </article>)}</div>
      </>
    ) : <EmptyState icon={Bell} title="还没有通知" description="设置一个临近提醒，到期后会在这里出现。" />}
  </div>
}
