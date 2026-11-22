import { useQuery } from '@tanstack/react-query'
import { Bell, Brain, Briefcase, CheckSquare2, Orbit, Settings2, Sparkles, Users } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { api } from '../api/client'
import { useNotificationStream } from '../hooks/useNotificationStream'
import { OnboardingModal } from './OnboardingModal'

const navigation = [
  { to: '/chat', label: '事界', icon: Briefcase, section: 'work' },
  { to: '/companion', label: '影界', icon: Orbit, section: 'social' },
  { to: '/circle', label: '圈子', icon: Users, section: 'social' },
  { to: '/memories', label: '记忆', icon: Brain, section: 'data' },
  { to: '/tasks', label: '待办', icon: CheckSquare2, section: 'data' },
  { to: '/notifications', label: '通知', icon: Bell, section: 'data' },
  { to: '/settings', label: '设置', icon: Settings2, section: 'system' },
]

export function AppShell() {
  const { latestNotification, connectionState } = useNotificationStream()
  const [onboardingDismissed, setOnboardingDismissed] = useState(false)
  const me = useQuery({ queryKey: ['me'], queryFn: api.fetchMe })
  const showOnboarding = me.data && !me.data.onboarded && !onboardingDismissed
  return (
    <div className="app-shell">
      <aside className="primary-nav">
        <div className="brand-block">
          <div className="brand-mark"><Sparkles size={18} /></div>
          <div><strong>影伴</strong><span>你从不孤单</span></div>
        </div>
        <nav aria-label="主导航">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="nav-footer">
          <span className={`connection-dot ${connectionState}`} />
          {connectionState === 'streaming' ? '在线' : connectionState === 'reconnecting' ? '重连中' : '连接中'}
        </div>
      </aside>
      <main className="page-stage"><Outlet /></main>
      {showOnboarding ? <OnboardingModal onDone={() => setOnboardingDismissed(true)} /> : null}
      {latestNotification ? (
        <div className="toast" role="status">
          <Bell size={17} />
          <div><strong>提醒</strong><span>{String(latestNotification.payload.title ?? '有一项事情到期啦')}</span></div>
        </div>
      ) : null}
    </div>
  )
}
