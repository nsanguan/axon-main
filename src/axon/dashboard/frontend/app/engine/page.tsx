"use client"

import { useState, useEffect, useCallback } from 'react'

interface ThreadInfo {
  thread_id: string
  event_type: string
  status: string
  progress: number
  severity_score: number
  escalation_level: string
  affected_departments: string[]
  summary: string
  created_at: string
  updated_at: string
}

interface EngineSummary {
  total_threads: number
  running: number
  waiting_for_approval: number
  completed: number
  error: number
  avg_severity: number
  top_escalation_level: string
}

const EVENT_LABELS: Record<string, string> = {
  po_delay: 'PO Delay',
  production_broken: 'Production Broken',
  machine_broken: 'Machine Broken',
  demand_spike: 'Demand Spike',
  inventory_shortage: 'Inventory Shortage',
  quality_incident: 'Quality Incident',
  supplier_crisis: 'Supplier Crisis',
  customer_complaint: 'Customer Complaint',
  safety_incident: 'Safety Incident',
}

const STATUS_CONFIG: Record<string, { color: string; bg: string; border: string; bar: string; icon: string }> = {
  running: { color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200', bar: 'bg-blue-500', icon: '⊛' },
  waiting_for_approval: { color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', bar: 'bg-amber-500', icon: '⏸' },
  completed: { color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', bar: 'bg-green-500', icon: '✓' },
  error: { color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', bar: 'bg-red-500', icon: '✕' },
}

const LEVEL_COLORS: Record<string, string> = {
  worker: 'bg-slate-100 text-slate-700',
  manager: 'bg-blue-100 text-blue-700',
  director: 'bg-amber-100 text-amber-700',
  executive: 'bg-red-100 text-red-700',
}

export default function EnginePage() {
  const [threads, setThreads] = useState<ThreadInfo[]>([])
  const [summary, setSummary] = useState<EngineSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = useCallback(() => {
    Promise.all([
      fetch('/api/engine/summary').then(r => r.json()),
      fetch('/api/engine/threads').then(r => r.json()),
    ])
      .then(([s, t]) => {
        setSummary(s)
        setThreads(t || [])
        setError('')
      })
      .catch(() => setError('Failed to load engine data'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return <p className="text-gray-500">Loading engine monitor...</p>
  }

  const activeThreads = threads.filter(t => t.status !== 'completed' && t.status !== 'error')
  const resolvedThreads = threads.filter(t => t.status === 'completed' || t.status === 'error')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Engine Monitoring</h2>
          <p className="text-gray-500 mt-1">
            Real-time LangGraph orchestration threads — status, progress, and outcomes
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
          <span className="text-sm font-medium text-green-700">Live</span>
          <span className="text-xs text-gray-400">· 5s poll</span>
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">{error}</div>
      )}

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <SummaryCard label="Total Threads" value={summary.total_threads} sub="" bg="bg-white" />
          <SummaryCard label="Running" value={summary.running} sub="" bg="bg-blue-50" color="text-blue-700" icon="⊛" />
          <SummaryCard label="Waiting" value={summary.waiting_for_approval} sub="HITL" bg="bg-amber-50" color="text-amber-700" icon="⏸" />
          <SummaryCard label="Completed" value={summary.completed} sub="" bg="bg-green-50" color="text-green-700" icon="✓" />
          <SummaryCard label="Errors" value={summary.error} sub="" bg="bg-red-50" color="text-red-700" icon="✕" />
          <SummaryCard label="Avg Severity" value={summary.avg_severity.toLocaleString()} sub="" bg="bg-white" />
          <SummaryCard label="Top Level" value={summary.top_escalation_level.toUpperCase()} sub="" bg="bg-white"
            color={summary.top_escalation_level === 'executive' ? 'text-red-700' : summary.top_escalation_level === 'director' ? 'text-amber-700' : 'text-blue-700'}
          />
        </div>
      )}

      {/* Active threads */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
          Active Threads
          <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">{activeThreads.length}</span>
        </h3>
        {activeThreads.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-10 text-center">
            <p className="text-gray-400 text-lg">No active threads</p>
            <p className="text-gray-400 text-sm mt-1">Start an escalation to see live thread tracking</p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeThreads.map(t => (
              <ThreadCard key={t.thread_id} thread={t} />
            ))}
          </div>
        )}
      </div>

      {/* Resolved threads */}
      {resolvedThreads.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            Recent Completed
            <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">{resolvedThreads.length}</span>
          </h3>
          <div className="space-y-3">
            {resolvedThreads.map(t => (
              <ThreadCard key={t.thread_id} thread={t} />
            ))}
          </div>
        </div>
      )}

      {threads.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-10 text-center">
          <p className="text-gray-400 text-lg">No threads tracked yet</p>
          <p className="text-gray-400 text-sm mt-1">Threads will appear when escalations are started</p>
        </div>
      )}

      {/* Manual refresh */}
      <div className="flex justify-center">
        <button
          onClick={fetchData}
          className="px-4 py-2 text-sm font-medium text-gray-600 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
        >
          Refresh Now
        </button>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, sub, bg, color, icon }: {
  label: string
  value: string | number
  sub: string
  bg: string
  color?: string
  icon?: string
}) {
  return (
    <div className={`rounded-xl shadow-sm border border-gray-200 p-4 ${bg}`}>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <div className="flex items-baseline gap-1.5 mt-1">
        <p className={`text-2xl font-bold ${color || 'text-gray-900'}`}>{value}</p>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function ThreadCard({ thread }: { thread: ThreadInfo }) {
  const cfg = STATUS_CONFIG[thread.status] || STATUS_CONFIG.running
  const pct = Math.round(thread.progress * 100)
  const elapsed = thread.created_at ? getElapsed(thread.created_at) : '—'

  return (
    <div className={`rounded-xl shadow-sm border ${cfg.border} ${cfg.bg} overflow-hidden`}>
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm text-gray-500">
                {thread.thread_id.slice(0, 12)}...
              </span>
              <span className={`px-2 py-0.5 text-xs rounded-full font-semibold ${cfg.color} ${cfg.bg}`}>
                {thread.status === 'waiting_for_approval' ? 'WAITING' : thread.status.toUpperCase()}
              </span>
              <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${LEVEL_COLORS[thread.escalation_level] || 'bg-gray-100 text-gray-600'}`}>
                {thread.escalation_level.toUpperCase()}
              </span>
            </div>

            <p className="text-sm font-medium text-gray-900 mt-2">
              {EVENT_LABELS[thread.event_type] || thread.event_type}
            </p>

            {thread.affected_departments.length > 0 && (
              <div className="flex gap-1 mt-1.5 flex-wrap">
                {thread.affected_departments.map(d => (
                  <span key={d} className="px-2 py-0.5 text-xs rounded-full bg-white border border-gray-200 text-gray-600">
                    {d}
                  </span>
                ))}
              </div>
            )}

            {thread.summary && (
              <p className="text-xs text-gray-500 mt-2 line-clamp-2">{thread.summary}</p>
            )}
          </div>

          <div className="ml-4 flex flex-col items-end gap-1.5 shrink-0">
            <div className="text-right">
              <p className="text-xs text-gray-400">Elapsed</p>
              <p className="text-sm font-mono text-gray-700">{elapsed}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">Severity</p>
              <p className="text-sm font-mono font-semibold text-gray-900">{thread.severity_score.toFixed(0)}</p>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-gray-500 font-medium">Progress</span>
            <span className={`font-semibold ${cfg.color}`}>{pct}%</span>
          </div>
          <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${cfg.bar} ${
                thread.status === 'running' ? 'animate-pulse' : ''
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1.5">
            <span>{cfg.icon} {thread.status.replace('_', ' ')}</span>
            <span>{thread.updated_at ? new Date(thread.updated_at).toLocaleTimeString() : '—'}</span>
          </div>
        </div>
      </div>

      {/* Mini-phase indicators */}
      <div className="grid grid-cols-4 border-t border-gray-200 divide-x divide-gray-200">
        <PhaseDot label="Worker" active={!!thread.escalation_level} done={levelsAfter(thread.escalation_level, 'worker')} />
        <PhaseDot label="Manager" active={levelsAfter(thread.escalation_level, 'worker')} done={levelsAfter(thread.escalation_level, 'manager')} />
        <PhaseDot label="Director" active={levelsAfter(thread.escalation_level, 'manager')} done={levelsAfter(thread.escalation_level, 'director')} />
        <PhaseDot label="Executive" active={levelsAfter(thread.escalation_level, 'director')} done={false} />
      </div>
    </div>
  )
}

function PhaseDot({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  const cls = done
    ? 'bg-green-500 text-green-700'
    : active
    ? 'bg-blue-500 text-blue-700'
    : 'bg-gray-300 text-gray-400'

  return (
    <div className="py-2 flex items-center justify-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${cls.split(' ')[0]}`} />
      <span className={`text-[10px] font-medium ${cls.split(' ')[1]}`}>{label}</span>
    </div>
  )
}

function levelsAfter(current: string, reference: string): boolean {
  const order = ['worker', 'manager', 'director', 'executive']
  const ci = order.indexOf(current)
  const ri = order.indexOf(reference)
  return ci > ri
}

function getElapsed(iso: string): string {
  try {
    const ms = Date.now() - new Date(iso).getTime()
    const s = Math.floor(ms / 1000)
    if (s < 60) return `${s}s`
    const m = Math.floor(s / 60)
    if (m < 60) return `${m}m`
    const h = Math.floor(m / 60)
    return `${h}h ${m % 60}m`
  } catch {
    return '—'
  }
}
