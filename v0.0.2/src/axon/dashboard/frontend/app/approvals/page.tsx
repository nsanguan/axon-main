"use client"

import { useState, useEffect } from 'react'

interface PendingApproval {
  plan_id: string
  context_summary: string
  deadlock: boolean
  demand_count: number
  supply_count: number
  agent_proposals: number
  negotiation_rounds: number
  global_utility: number | null
  created_at: string | null
  requires_approval: boolean
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<PendingApproval[]>([])
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState('')

  const fetchApprovals = () => {
    setLoading(true)
    fetch('/api/approvals/pending')
      .then(r => r.json())
      .then(data => setApprovals(data || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchApprovals() }, [])

  const handleAction = async (plan_id: string, approved: boolean, note: string = '') => {
    try {
      const res = await fetch('/api/approvals/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id, approved, note }),
      })
      if (res.ok) {
        setActionMsg(approved ? 'Plan approved' : 'Plan rejected')
        fetchApprovals()
      } else {
        setActionMsg('Action failed')
      }
    } catch {
      setActionMsg('Network error')
    }
  }

  if (loading && approvals.length === 0) {
    return <p className="text-gray-500">Loading pending approvals...</p>
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Pending Approvals</h2>
        <p className="text-gray-500 mt-1">
          Plans requiring human-in-the-loop review before execution
        </p>
      </div>

      {actionMsg && (
        <div className="px-4 py-3 rounded-lg text-sm bg-blue-50 text-blue-700">{actionMsg}</div>
      )}

      {approvals.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <p className="text-gray-400 text-lg">No pending approvals</p>
          <p className="text-gray-400 text-sm mt-1">All plans have been reviewed or auto-approved</p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map(a => (
            <div key={a.plan_id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-gray-500">Plan {a.plan_id.slice(0, 8)}...</span>
                    {a.deadlock && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">Deadlock</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{a.context_summary || 'No context summary available'}</p>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
                <div><span className="text-gray-500">Demands:</span> <span className="font-medium">{a.demand_count}</span></div>
                <div><span className="text-gray-500">Supplies:</span> <span className="font-medium">{a.supply_count}</span></div>
                <div><span className="text-gray-500">Proposals:</span> <span className="font-medium">{a.agent_proposals}</span></div>
                <div><span className="text-gray-500">Utility:</span> <span className="font-medium">{a.global_utility?.toFixed(2) ?? '-'}</span></div>
              </div>

              <div className="flex gap-3 mt-6 pt-4 border-t border-gray-100">
                <button
                  onClick={() => handleAction(a.plan_id, true, 'Approved by manager')}
                  className="px-5 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium transition-colors"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleAction(a.plan_id, false, 'Rejected — needs revision')}
                  className="px-5 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 text-sm font-medium transition-colors"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
