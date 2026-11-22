import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, createBrowserRouter } from 'react-router-dom'

import { AppShell } from '../components/AppShell'

const ChatPage = lazy(() => import('../features/chat/ChatPage').then((module) => ({ default: module.ChatPage })))
const GroupChatPage = lazy(() => import('../features/chat/GroupChatPage').then((module) => ({ default: module.GroupChatPage })))
const CompanionPage = lazy(() => import('../features/companion/CompanionPage').then((module) => ({ default: module.CompanionPage })))
const CompanionChatPage = lazy(() => import('../features/companion/CompanionChatPage').then((module) => ({ default: module.CompanionChatPage })))
const CirclePage = lazy(() => import('../features/circle/CirclePage').then((module) => ({ default: module.CirclePage })))
const MemoriesPage = lazy(() => import('../features/memories/MemoriesPage').then((module) => ({ default: module.MemoriesPage })))
const TasksPage = lazy(() => import('../features/tasks/TasksPage').then((module) => ({ default: module.TasksPage })))
const NotificationsPage = lazy(() => import('../features/notifications/NotificationsPage').then((module) => ({ default: module.NotificationsPage })))
const RunDetailsPage = lazy(() => import('../features/runs/RunDetailsPage').then((module) => ({ default: module.RunDetailsPage })))
const SettingsPage = lazy(() => import('../features/settings/SettingsPage').then((module) => ({ default: module.SettingsPage })))

function lazyPage(element: ReactNode) {
  return <Suspense fallback={<div className="route-loading">正在加载页面…</div>}>{element}</Suspense>
}

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { path: '/chat', element: lazyPage(<ChatPage />) },
      { path: '/chat/:conversationId', element: lazyPage(<ChatPage />) },
      { path: '/companion', element: lazyPage(<CompanionPage />) },
      { path: '/companion/chat/:conversationId', element: lazyPage(<CompanionChatPage />) },
      { path: '/group/:conversationId', element: lazyPage(<GroupChatPage />) },
      { path: '/circle', element: lazyPage(<CirclePage />) },
      { path: '/memories', element: lazyPage(<MemoriesPage />) },
      { path: '/tasks', element: lazyPage(<TasksPage />) },
      { path: '/notifications', element: lazyPage(<NotificationsPage />) },
      { path: '/settings', element: lazyPage(<SettingsPage />) },
      { path: '/runs/:runId', element: lazyPage(<RunDetailsPage />) },
      { path: '*', element: <Navigate to="/chat" replace /> },
    ],
  },
])
