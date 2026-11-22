import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { connectSSE } from '../api/sse'
import type { Notification } from '../types/api'

export function useNotificationStream() {
  const queryClient = useQueryClient()
  const [latestNotification, setLatestNotification] = useState<Notification | null>(null)
  const [connectionState, setConnectionState] = useState<'connecting' | 'streaming' | 'reconnecting' | 'closed'>('connecting')

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void connectSSE('/api/v1/notifications/stream', {
      signal: controller.signal,
      reconnect: true,
      onStateChange: setConnectionState,
      onEvent: (event) => {
        if (event.event !== 'task.reminder') return
        const notification = event.data as unknown as Notification
        setLatestNotification(notification)
        void queryClient.invalidateQueries({ queryKey: ['notifications'] })
        void queryClient.invalidateQueries({ queryKey: ['tasks'] })
        window.setTimeout(() => setLatestNotification(null), 10000)
        if ('Notification' in window && Notification.permission === 'granted') {
          new window.Notification('影伴 · 待办提醒', {
            body: String(notification.payload?.title ?? '有一项事情到期了'),
            icon: '/favicon.ico',
          })
        }
      },
    }).catch(() => setConnectionState('closed'))
    return () => controller.abort()
  }, [queryClient])

  return { latestNotification, connectionState }
}
