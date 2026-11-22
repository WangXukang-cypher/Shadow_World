import { useQuery } from '@tanstack/react-query'
import { Calendar, MessageCircle, Trash2, Users } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '../../api/client'
import { PageHeader } from '../../components/PageHeader'

interface PersonNode {
  id: string
  name: string
  nickname: string | null
  relationship: string
  traits: string[]
  birthday: string | null
  mention_count: number
  notes: string | null
}

interface Commitment {
  id: string
  person_id: string
  content: string
  created_at: string | null
}

interface SocialGraph {
  nodes: PersonNode[]
  commitments: Commitment[]
}

const RELATIONSHIP_COLORS: Record<string, string> = {
  '朋友': '#6c5ce7',
  '同事': '#00b894',
  '家人': '#e74c3c',
  '同学': '#fdcb6e',
  '恋人': '#ff7675',
}

interface NodePosition {
  x: number
  y: number
}

export function CirclePage() {
  const { data, isLoading, refetch } = useQuery<SocialGraph>({
    queryKey: ['social-graph'],
    queryFn: () => api.fetch('/people/graph'),
  })
  const [positions, setPositions] = useState<Record<string, NodePosition>>({})
  const [dragging, setDragging] = useState<string | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const nodes = data?.nodes ?? []
  const commitments = data?.commitments ?? []

  // Initialize positions in a circle layout
  useEffect(() => {
    if (nodes.length && Object.keys(positions).length !== nodes.length) {
      const pos: Record<string, NodePosition> = {}
      nodes.forEach((node, i) => {
        const angle = (2 * Math.PI * i) / nodes.length
        pos[node.id] = { x: 300 + 140 * Math.cos(angle), y: 200 + 120 * Math.sin(angle) }
      })
      setPositions(pos)
    }
  }, [nodes, positions])

  const handleMouseDown = useCallback((id: string) => {
    setDragging(id)
  }, [])

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!dragging || !svgRef.current) return
    const svg = svgRef.current
    const rect = svg.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * 600
    const y = ((e.clientY - rect.top) / rect.height) * 400
    setPositions((prev) => ({ ...prev, [dragging]: { x, y } }))
  }, [dragging])

  const handleMouseUp = useCallback(() => {
    setDragging(null)
  }, [])

  async function deletePerson(id: string) {
    if (!confirm('确定删除这个人物？')) return
    await fetch(`/api/v1/people/${id}`, { method: 'DELETE' })
    refetch()
  }

  if (isLoading) return <div className="content-page"><div className="route-loading">加载中…</div></div>

  return (
    <div className="content-page">
      <PageHeader eyebrow="People" title="我的圈子" description="聊天中提到的人会自动出现在这里，你也可以拖拽调整布局" />

      {nodes.length === 0 ? (
        <div className="empty-state" style={{ marginTop: '60px' }}>
          <Users size={48} />
          <strong>还没有人物记录</strong>
          <p>在对话中聊到朋友、同事、家人时，会自动帮你记住他们</p>
        </div>
      ) : (
        <div className="circle-layout">
          <div className="graph-container">
            <svg
              ref={svgRef}
              viewBox="0 0 600 400"
              style={{ width: '100%', height: '100%', cursor: dragging ? 'grabbing' : 'default' }}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              {nodes.map((node) => {
                const pos = positions[node.id] ?? { x: 300, y: 200 }
                const color = RELATIONSHIP_COLORS[node.relationship] ?? '#a29bfe'
                const radius = Math.min(30, 16 + node.mention_count * 2)
                return (
                  <g key={node.id} style={{ cursor: 'grab' }} onMouseDown={() => handleMouseDown(node.id)}>
                    <line x1={300} y1={200} x2={pos.x} y2={pos.y} stroke="#e2e2ee" strokeWidth={1} />
                    <circle cx={pos.x} cy={pos.y} r={radius} fill={color} opacity={0.15} />
                    <circle cx={pos.x} cy={pos.y} r={radius - 4} fill={color} opacity={0.8} />
                    <text x={pos.x} y={pos.y + radius + 14} textAnchor="middle" fontSize={11} fill="#4a4a60">
                      {node.nickname ?? node.name}
                    </text>
                  </g>
                )
              })}
              <circle cx={300} cy={200} r={24} fill="#6c5ce7" />
              <text x={300} y={204} textAnchor="middle" fontSize={10} fill="white" fontWeight="bold">我</text>
            </svg>
          </div>

          <div className="person-panel">
            {nodes.map((person) => (
              <div key={person.id} className="person-card">
                <h3>
                  {person.name}
                  <span className="relationship-tag">{person.relationship}</span>
                  <button style={{ marginLeft: 'auto', border: 0, background: 'transparent', color: 'var(--muted)', cursor: 'pointer' }} onClick={() => deletePerson(person.id)}><Trash2 size={13} /></button>
                </h3>
                {person.notes && <p>{person.notes}</p>}
                <div className="meta">
                  {person.birthday && <span><Calendar size={10} /> {person.birthday}</span>}
                  <span><MessageCircle size={10} /> 提及 {person.mention_count} 次</span>
                </div>
                {commitments
                  .filter((c) => c.person_id === person.id)
                  .map((c) => (
                    <div key={c.id} className="commitment-badge">
                      ❤️ {c.content}
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
