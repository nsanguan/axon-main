"use client"

import { useState, useEffect } from 'react'

interface SystemHealth {
  degradation_level: string
  healthy_servers: string[]
  unhealthy_servers: string[]
  total_plans: number
  pending_approvals: number
}

interface WeightsData {
  cost: number
  delivery: number
  quality: number
  sustainability: number
  flexibility: number
}

export default function Dashboard() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [weights, setWeights] = useState<WeightsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/system').then(r => r.json()),
      fetch('/api/weights').then(r => r.json()),
    ]).then(([h, w]) => {
      setHealth(h)
      setWeights(w.weights)
    }).catch(console.error)
    .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-gray-500">Loading...</p></div>
  }

  const degColors: Record<string, string> = {
    FULL: 'bg-green-100 text-green-800',
    DEGRADED: 'bg-yellow-100 text-yellow-800',
    LIMITED: 'bg-orange-100 text-orange-800',
    CRITICAL: 'bg-red-100 text-red-800',
  }

  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-3xl bg-slate-950 px-8 py-10 text-white shadow-2xl">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.28),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(34,197,94,0.18),transparent_28%)]" />
        <div className="relative max-w-4xl">
          <div className="mb-4 inline-flex items-center rounded-full border border-blue-400/30 bg-blue-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">
            Agentic Supply Chain Planning
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            The agentic nerve system for supply chain planning
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
            Axon is an AI-native planning and orchestration layer for modern ERPs, turning demand,
            inventory, procurement, and operational signals into coordinated decisions and actionable workflows.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="/weights"
              className="inline-flex items-center rounded-xl bg-blue-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-400"
            >
              Tune Strategic Weights
            </a>
            <a
              href="/plans"
              className="inline-flex items-center rounded-xl border border-slate-700 bg-slate-900/60 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:bg-slate-900"
            >
              View Planning Queue
            </a>
          </div>
          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <HeroMetric
              label="ERP-aware orchestration"
              value="MCP-native"
              detail="No direct DB coupling"
            />
            <HeroMetric
              label="Operational model"
              value="Human + AI"
              detail="Approval-ready workflows"
            />
            <HeroMetric
              label="Planning scope"
              value="10 domains"
              detail="Cross-functional agent mesh"
            />
          </div>
        </div>
      </section>

      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-gray-500 mt-1">System overview and strategic settings</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard title="System Status" value={health?.degradation_level || 'Unknown'}
          badge={health?.degradation_level || ''}
          badgeColor={degColors[health?.degradation_level || 'FULL'] || degColors.FULL} />
        <StatCard title="Total Plans" value={String(health?.total_plans || 0)} />
        <StatCard title="Pending Approvals" value={String(health?.pending_approvals || 0)} />
        <StatCard title="Healthy Servers" value={`${health?.healthy_servers?.length || 0} / ${(health?.healthy_servers?.length || 0) + (health?.unhealthy_servers?.length || 0)}`} />
      </div>

      {weights && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Strategic Weights</h3>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <WeightBar label="Cost" value={weights.cost} color="bg-red-500" />
            <WeightBar label="Delivery" value={weights.delivery} color="bg-blue-500" />
            <WeightBar label="Quality" value={weights.quality} color="bg-green-500" />
            <WeightBar label="Sustainability" value={weights.sustainability} color="bg-emerald-500" />
            <WeightBar label="Flexibility" value={weights.flexibility} color="bg-purple-500" />
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">MCP Server Status</h3>
        <div className="space-y-2">
          {health?.healthy_servers?.map(s => (
            <div key={s} className="flex items-center gap-3 px-3 py-2 bg-green-50 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm font-medium text-gray-700">{s}</span>
              <span className="text-xs text-green-600 ml-auto">Healthy</span>
            </div>
          ))}
          {health?.unhealthy_servers?.map(s => (
            <div key={s} className="flex items-center gap-3 px-3 py-2 bg-red-50 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-sm font-medium text-gray-700">{s}</span>
              <span className="text-xs text-red-600 ml-auto">Unavailable</span>
            </div>
          ))}
          {(!health?.healthy_servers?.length && !health?.unhealthy_servers?.length) && (
            <p className="text-sm text-gray-400 italic">No MCP servers registered</p>
          )}
        </div>
      </div>
    </div>
  )
}

function HeroMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-sm text-slate-300">{detail}</p>
    </div>
  )
}

function StatCard({ title, value, badge, badgeColor }: { title: string; value: string; badge?: string; badgeColor?: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {badge && badgeColor && (
        <span className={`inline-block mt-2 px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeColor}`}>{badge}</span>
      )}
    </div>
  )
}

function WeightBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{Math.round(value * 100)}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  )
}
