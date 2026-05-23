"use client"

import { useState, useEffect } from 'react'

const EVENT_SCORING: Record<string, { impact: number; urgency: number; customer_risk: number; always_exec: boolean; label: string }> = {
  po_delay: { impact: 80_000, urgency: 2.5, customer_risk: 1.2, always_exec: false, label: 'PO Delay' },
  production_broken: { impact: 500_000, urgency: 3.0, customer_risk: 2.0, always_exec: true, label: 'Production Broken' },
  machine_broken: { impact: 50_000, urgency: 1.5, customer_risk: 1.0, always_exec: false, label: 'Machine Broken' },
  demand_spike: { impact: 200_000, urgency: 2.0, customer_risk: 1.5, always_exec: false, label: 'Demand Spike' },
  inventory_shortage: { impact: 100_000, urgency: 2.0, customer_risk: 1.3, always_exec: false, label: 'Inventory Shortage' },
  quality_incident: { impact: 150_000, urgency: 2.5, customer_risk: 1.8, always_exec: false, label: 'Quality Incident' },
  supplier_crisis: { impact: 300_000, urgency: 3.0, customer_risk: 2.0, always_exec: true, label: 'Supplier Crisis' },
  customer_complaint: { impact: 30_000, urgency: 1.5, customer_risk: 1.0, always_exec: false, label: 'Customer Complaint' },
  safety_incident: { impact: 1_000_000, urgency: 4.0, customer_risk: 3.0, always_exec: true, label: 'Safety Incident' },
}

const LEVELS = [
  { level: 'worker', label: 'Worker', desc: 'Alert detection, initial scoring', color: 'bg-slate-500', range: 'Detection' },
  { level: 'manager', label: 'Manager', desc: 'Within-department resolution', color: 'bg-blue-500', range: 'Score ≤ 2,000' },
  { level: 'director', label: 'Director', desc: 'Cross-department coordination', color: 'bg-amber-500', range: 'Score 2,001–10,000' },
  { level: 'executive', label: 'Executive', desc: 'Strategic HITL decision', color: 'bg-red-500', range: 'Score > 10,000' },
]

function computeScore(event_type: string, dept_count: number): number {
  const s = EVENT_SCORING[event_type]
  if (!s) return 0
  let score = s.impact * s.urgency * dept_count * s.customer_risk
  if (s.always_exec) score = Math.max(score, 10_001)
  return Math.round(score)
}

function getLevel(score: number, always_exec: boolean): string {
  if (always_exec || score > 10_000) return 'executive'
  if (score > 2_000) return 'director'
  if (score > 0) return 'manager'
  return 'worker'
}

interface EscalationStartResponse {
  thread_id: string
  status: string
  severity_score: number
  summary: string | null
}

interface EscalationStatusResponse {
  thread_id: string
  event_type: string
  severity_score: number
  escalation_level: string
  escalation_steps: { level: string; agent: string; summary: string; timestamp: string }[]
  status: string
}

export default function EscalationPage() {
  const [eventType, setEventType] = useState('po_delay')
  const [rawDetail, setRawDetail] = useState('')
  const [departments, setDepartments] = useState('operations')
  const [deptCount, setDeptCount] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<EscalationStartResponse | null>(null)
  const [startError, setStartError] = useState('')

  const [statusThreadId, setStatusThreadId] = useState('')
  const [statusResult, setStatusResult] = useState<EscalationStatusResponse | null>(null)
  const [statusLoading, setStatusLoading] = useState(false)
  const [statusError, setStatusError] = useState('')

  const [tab, setTab] = useState<'reference' | 'launch' | 'status'>('reference')

  const previewScore = computeScore(eventType, deptCount)
  const previewLevel = getLevel(previewScore, EVENT_SCORING[eventType]?.always_exec ?? false)

  const handleStart = async () => {
    setSubmitting(true)
    setStartError('')
    setResult(null)
    try {
      const deptList = departments.split(',').map(d => d.trim()).filter(Boolean)
      const actualDeptCount = deptList.length || deptCount
      const res = await fetch('/api/escalation/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: eventType,
          raw_detail: rawDetail,
          affected_departments: deptList,
          thread_id: null,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as any).detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
    } catch (e: any) {
      setStartError(e.message || 'Failed to start escalation')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCheckStatus = async () => {
    setStatusLoading(true)
    setStatusError('')
    setStatusResult(null)
    try {
      const res = await fetch(`/api/escalation/${statusThreadId}/status`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as any).detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setStatusResult(data)
    } catch (e: any) {
      setStatusError(e.message || 'Failed to fetch status')
    } finally {
      setStatusLoading(false)
    }
  }

  const levelColors: Record<string, string> = {
    worker: 'bg-slate-100 text-slate-700',
    manager: 'bg-blue-100 text-blue-700',
    director: 'bg-amber-100 text-amber-700',
    executive: 'bg-red-100 text-red-700',
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Escalation Engine</h2>
        <p className="text-gray-500 mt-1">
          Four-tier escalation ladder for supply chain disruptions — severity scoring and HITL workflow
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(['reference', 'launch', 'status'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'reference' ? 'Architecture' : t === 'launch' ? 'New Escalation' : 'Check Status'}
          </button>
        ))}
      </div>

      {/* Tab: Reference */}
      {tab === 'reference' && (
        <div className="space-y-6">
          {/* Escalation Ladder */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Escalation Ladder</h3>
            <div className="space-y-3">
              {LEVELS.map((l, i) => (
                <div key={l.level} className="relative">
                  <div className={`rounded-xl ${l.color} bg-opacity-10 border border-opacity-20`}
                    style={{ borderColor: l.color.replace('bg-', '') }}>
                    <div className="flex items-center gap-4 p-4">
                      <div className={`w-10 h-10 rounded-full ${l.color} text-white flex items-center justify-center text-sm font-bold`}>
                        {i + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">{l.label}</span>
                          <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${levelColors[l.level]}`}>
                            {l.range}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 mt-0.5">{l.desc}</p>
                      </div>
                      {l.level === 'executive' && (
                        <span className="px-2 py-1 text-xs font-semibold uppercase rounded-full bg-red-100 text-red-700">
                          HITL
                        </span>
                      )}
                    </div>
                  </div>
                  {i < LEVELS.length - 1 && (
                    <div className="ml-9 my-1 border-l-2 border-dashed border-gray-300 h-4" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Always Executive */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Always Executive Events</h3>
            <p className="text-sm text-gray-500 mb-4">
              These event types bypass severity scoring and escalate directly to Executive level:
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(EVENT_SCORING)
                .filter(([_, s]) => s.always_exec)
                .map(([key, s]) => (
                  <span key={key} className="px-3 py-1.5 rounded-lg text-sm font-medium bg-red-50 text-red-700 border border-red-200">
                    {s.label}
                  </span>
                ))}
            </div>
          </div>

          {/* Event Type Reference Table */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Event Type Scoring Reference</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-600">Event Type</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">Impact ($)</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">Urgency</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">Customer Risk</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">Score (1 dept)</th>
                    <th className="text-center py-3 px-4 font-semibold text-gray-600">Level</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(EVENT_SCORING).map(([key, s]) => {
                    const score = computeScore(key, 1)
                    const level = getLevel(score, s.always_exec)
                    return (
                      <tr key={key} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4">
                          <span className="font-medium text-gray-900">{s.label}</span>
                          {s.always_exec && (
                            <span className="ml-2 px-1.5 py-0.5 text-xs rounded bg-red-100 text-red-600">AUTO-EXEC</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-600 font-mono">${(s.impact).toLocaleString()}</td>
                        <td className="py-3 px-4 text-right text-gray-600 font-mono">{s.urgency}x</td>
                        <td className="py-3 px-4 text-right text-gray-600 font-mono">{s.customer_risk}x</td>
                        <td className="py-3 px-4 text-right text-gray-900 font-mono font-semibold">{score.toLocaleString()}</td>
                        <td className="py-3 px-4 text-center">
                          <span className={`px-2 py-1 text-xs rounded-full font-medium ${levelColors[level]}`}>
                            {level.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Launch */}
      {tab === 'launch' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Form */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Start Escalation</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
                <select
                  value={eventType}
                  onChange={e => setEventType(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {Object.entries(EVENT_SCORING).map(([key, s]) => (
                    <option key={key} value={key}>{s.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Detail</label>
                <textarea
                  value={rawDetail}
                  onChange={e => setRawDetail(e.target.value)}
                  placeholder="Describe the disruption event..."
                  rows={4}
                  maxLength={2000}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                />
                <p className="text-xs text-gray-400 mt-1">{rawDetail.length}/2000</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Affected Departments</label>
                <input
                  value={departments}
                  onChange={e => setDepartments(e.target.value)}
                  onBlur={() => {
                    const count = departments.split(',').map(d => d.trim()).filter(Boolean).length
                    setDeptCount(count || 1)
                  }}
                  placeholder="operations, procurement, logistics"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <button
                onClick={handleStart}
                disabled={submitting || !rawDetail.trim()}
                className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? 'Starting...' : 'Start Escalation'}
              </button>

              {startError && (
                <div className="px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">{startError}</div>
              )}
            </div>
          </div>

          {/* Preview */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Severity Preview</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Severity Score</p>
                  <p className="text-xl font-bold text-gray-900 font-mono">{previewScore.toLocaleString()}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Escalation Level</p>
                  <p className={`text-xl font-bold font-mono ${
                    previewLevel === 'executive' ? 'text-red-600' :
                    previewLevel === 'director' ? 'text-amber-600' :
                    previewLevel === 'manager' ? 'text-blue-600' :
                    'text-slate-600'
                  }`}>
                    {previewLevel.toUpperCase()}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Departments</p>
                  <p className="text-xl font-bold text-gray-900 font-mono">{deptCount}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Auto-Executive</p>
                  <p className={`text-xl font-bold font-mono ${EVENT_SCORING[eventType]?.always_exec ? 'text-red-600' : 'text-green-600'}`}>
                    {EVENT_SCORING[eventType]?.always_exec ? 'YES' : 'NO'}
                  </p>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-2">Scoring Formula</p>
                <p className="text-sm text-blue-800 font-mono">
                  score = impact × urgency × dept_count × customer_risk
                </p>
              </div>
            </div>

            {result && (
              <div className="mt-6 pt-4 border-t border-gray-100 space-y-2">
                <p className="text-sm font-semibold text-gray-900">Result</p>
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Thread ID</span>
                    <span className="font-mono font-medium text-gray-900">{result.thread_id.slice(0, 12)}...</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Status</span>
                    <span className={`font-semibold ${result.status === 'waiting_for_approval' ? 'text-amber-600' : 'text-green-600'}`}>
                      {result.status === 'waiting_for_approval' ? 'Waiting for Approval' : 'Complete'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Severity</span>
                    <span className="font-mono font-medium text-gray-900">{result.severity_score.toFixed(0)}</span>
                  </div>
                  {result.summary && (
                    <div className="pt-2 text-sm text-gray-700">{result.summary}</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Status */}
      {tab === 'status' && (
        <div className="max-w-2xl space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Check Escalation Status</h3>
            <div className="flex gap-3">
              <input
                value={statusThreadId}
                onChange={e => setStatusThreadId(e.target.value)}
                placeholder="Thread ID (UUID)"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                onClick={handleCheckStatus}
                disabled={statusLoading || !statusThreadId.trim()}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {statusLoading ? 'Checking...' : 'Check'}
              </button>
            </div>
            {statusError && (
              <div className="mt-4 px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">{statusError}</div>
            )}
          </div>

          {statusResult && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Escalation State</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Status</p>
                  <p className="text-lg font-semibold text-gray-900">{statusResult.status}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Level</p>
                  <p className="text-lg font-semibold text-gray-900">{statusResult.escalation_level || '-'}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Event Type</p>
                  <p className="text-lg font-semibold text-gray-900">{statusResult.event_type || '-'}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Severity Score</p>
                  <p className="text-lg font-semibold text-gray-900 font-mono">{statusResult.severity_score}</p>
                </div>
              </div>
              {statusResult.escalation_steps.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-2">Escalation Steps</p>
                  <div className="space-y-2">
                    {statusResult.escalation_steps.map((step, i) => (
                      <div key={i} className="border border-gray-200 rounded-lg p-3">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${levelColors[step.level] || 'bg-gray-100 text-gray-700'}`}>
                            {step.level}
                          </span>
                          <span className="text-xs text-gray-500">{step.agent}</span>
                        </div>
                        <p className="text-sm text-gray-700 mt-1">{step.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
