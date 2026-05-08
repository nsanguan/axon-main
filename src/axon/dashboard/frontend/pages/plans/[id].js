/**
 * /plans/[id] — Plan detail page.
 *
 * Shows:
 *  - Negotiation timeline (rounds → utility score per round)
 *  - Allocation table (item / demand / supply / allocated qty / agent)
 *  - Utility score summary bar
 *
 * Fetches from GET /api/plans/:id
 */

import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

function UtilityBar({ score }) {
  const pct = score != null ? Math.min(100, Math.round(score * 100)) : 0;
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-3 rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-semibold text-gray-700 w-12 text-right">{pct} %</span>
    </div>
  );
}

function NegotiationTimeline({ rounds }) {
  if (!rounds || rounds.length === 0) {
    return <p className="text-sm text-gray-400">No negotiation rounds recorded.</p>;
  }
  return (
    <ol className="space-y-2">
      {rounds.map((r, idx) => (
        <li key={idx} className="flex items-center gap-4 text-sm">
          <span className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold shrink-0">
            {r.round_number ?? idx + 1}
          </span>
          <div className="flex-1">
            <div className="flex gap-2 items-center">
              <span className="font-medium text-gray-700">
                Global utility: {r.global_utility != null ? (r.global_utility * 100).toFixed(1) + ' %' : '—'}
              </span>
              {r.resolved ? (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">resolved</span>
              ) : (
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">{r.resolution ?? 'in progress'}</span>
              )}
            </div>
            <p className="text-xs text-gray-400">{formatDate(r.completed_at)}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function AllocationTable({ allocations }) {
  if (!allocations || allocations.length === 0) {
    return <p className="text-sm text-gray-400">No allocations.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-2 text-left text-gray-600 font-semibold">Item</th>
            <th className="px-4 py-2 text-left text-gray-600 font-semibold">Demand Qty</th>
            <th className="px-4 py-2 text-left text-gray-600 font-semibold">Supply Qty</th>
            <th className="px-4 py-2 text-left text-gray-600 font-semibold">Allocated</th>
            <th className="px-4 py-2 text-left text-gray-600 font-semibold">Agent</th>
            <th className="px-4 py-2 text-left text-gray-600 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {allocations.map((a, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              <td className="px-4 py-2 text-gray-700 font-mono text-xs">
                {a.demand?.item?.native_id ?? a.supply?.item?.native_id ?? '—'}
              </td>
              <td className="px-4 py-2 text-gray-600">{a.demand?.quantity ?? '—'}</td>
              <td className="px-4 py-2 text-gray-600">{a.supply?.quantity ?? '—'}</td>
              <td className="px-4 py-2 font-semibold text-indigo-700">{a.allocated_quantity ?? '—'}</td>
              <td className="px-4 py-2 text-gray-500 text-xs">{a.agent_id ?? '—'}</td>
              <td className="px-4 py-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  a.status === 'approved' ? 'bg-green-100 text-green-700' :
                  a.status === 'proposed' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-500'
                }`}>
                  {a.status ?? '—'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PlanDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/plans/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (!cancelled) {
          setPlan(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [id]);

  // Flatten all allocations from all proposals in the last round
  const allocations = (() => {
    if (!plan) return [];
    const lastRound = plan.negotiation_rounds?.[plan.negotiation_rounds.length - 1];
    if (!lastRound?.proposals) return plan.final_plan ?? [];
    return Object.entries(lastRound.proposals).flatMap(([agentId, proposal]) =>
      (proposal.allocations ?? []).map((a) => ({ ...a, agent_id: agentId }))
    );
  })();

  return (
    <>
      <Head>
        <title>Axon — Plan {id ? id.slice(0, 8) : '…'}</title>
      </Head>
      <main className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-5xl mx-auto">
          {/* Breadcrumb */}
          <nav className="mb-6 text-sm text-gray-500">
            <Link href="/" className="hover:underline">Dashboard</Link>
            <span className="mx-2">/</span>
            <Link href="/plans" className="hover:underline">Planning Runs</Link>
            <span className="mx-2">/</span>
            <span className="text-gray-700 font-mono text-xs">{id ?? '…'}</span>
          </nav>

          {loading && <div className="text-gray-400">Loading plan…</div>}
          {error && <div className="text-red-500">{error}</div>}
          {plan && (
            <div className="space-y-8">
              {/* Header */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h1 className="text-xl font-bold text-gray-800 font-mono text-sm">{plan.id}</h1>
                    <p className="text-xs text-gray-400 mt-1">Created: {formatDate(plan.created_at)}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className={`px-3 py-1 rounded text-sm font-semibold ${
                      plan.status === 'approved' ? 'bg-green-100 text-green-700' :
                      plan.status === 'hitl_required' ? 'bg-red-100 text-red-700' :
                      plan.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                      'bg-gray-100 text-gray-500'
                    }`}>
                      {plan.status}
                    </span>
                    {plan.hitl_required && (
                      <Link
                        href="/approvals"
                        className="text-xs text-indigo-600 hover:underline"
                      >
                        Pending HITL approval →
                      </Link>
                    )}
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Overall Utility</p>
                  <UtilityBar score={plan.utility_score} />
                </div>
              </div>

              {/* Negotiation Timeline */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-800 mb-4">Negotiation Timeline</h2>
                <NegotiationTimeline rounds={plan.negotiation_rounds} />
              </div>

              {/* Allocation Table */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-800 mb-4">
                  Allocations ({allocations.length})
                </h2>
                <AllocationTable allocations={allocations} />
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
