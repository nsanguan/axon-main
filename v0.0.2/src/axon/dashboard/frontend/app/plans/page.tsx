"use client"

import { useState, useEffect } from 'react'

interface PlanSummary {
  plan_id: string
  created_at: string
  tags: string[]
  plan_confidence: number | null
  allocation_count: number
  deadlock: boolean
  approved: boolean
}

export default function PlansPage() {
  const [plans, setPlans] = useState<PlanSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/plans?limit=50')
      .then(r => r.json())
      .then(data => {
        setPlans(data.plans || [])
        setTotal(data.total || 0)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <p className="text-gray-500">Loading plans...</p>
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Plan History</h2>
        <p className="text-gray-500 mt-1">{total} total plans recorded</p>
      </div>

      {plans.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <p className="text-gray-400 text-lg">No plans recorded yet</p>
          <p className="text-gray-400 text-sm mt-1">Plans will appear here after running planning cycles</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Plan ID</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Allocations</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Tags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {plans.map(p => (
                <tr key={p.plan_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <a href={`/plans/${p.plan_id}`} className="text-sm font-mono text-axon-600 hover:text-axon-800">
                      {p.plan_id.slice(0, 8)}...
                    </a>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(p.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4">
                    {p.plan_confidence != null ? (
                      <span className={`text-sm font-medium ${p.plan_confidence >= 0.7 ? 'text-green-600' : 'text-yellow-600'}`}>
                        {Math.round(p.plan_confidence * 100)}%
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{p.allocation_count}</td>
                  <td className="px-6 py-4">
                    {p.deadlock ? (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-700">Deadlock</span>
                    ) : p.approved ? (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-700">Approved</span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600">Draft</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-1 flex-wrap">
                      {p.tags.slice(0, 3).map(t => (
                        <span key={t} className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-600">{t}</span>
                      ))}
                      {p.tags.length > 3 && (
                        <span className="text-xs text-gray-400">+{p.tags.length - 3}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
