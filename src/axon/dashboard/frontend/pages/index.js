import { useState, useEffect, useCallback } from 'react';

const API = '';

async function fetchJSON(url) {
  const res = await fetch(`${API}${url}`);
  if (!res.ok) throw new Error(`GET ${url} failed: ${res.status}`);
  return res.json();
}

async function putJSON(url, body) {
  const res = await fetch(`${API}${url}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT ${url} failed: ${res.status}`);
  return res.json();
}

async function postJSON(url, body) {
  const res = await fetch(`${API}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${url} failed: ${res.status}`);
  return res.json();
}

// ─── Weights Panel ───────────────────────────────────────────────

function WeightsPanel({ weights, onChange, onSave }) {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  const valid = Math.abs(total - 1.0) < 0.01;

  return (
    <div className="card">
      <h3>Strategic Weights</h3>
      <div className="slider-group">
        {Object.entries(weights).map(([key, val]) => (
          <div className="slider-row" key={key}>
            <label>{key.charAt(0).toUpperCase() + key.slice(1)}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={val}
              onChange={(e) => onChange(key, parseFloat(e.target.value))}
            />
            <span className="slider-value">{(val * 100).toFixed(0)}%</span>
          </div>
        ))}
        <div className="sum-row">
          <span>Sum</span>
          <span className={`sum-value ${valid ? 'valid' : 'invalid'}`}>
            {total.toFixed(2)} {valid ? '✓' : '✗'}
          </span>
        </div>
      </div>
      <div className="actions">
        <button className="btn btn-primary" onClick={onSave}>Save Weights</button>
      </div>
    </div>
  );
}

// ─── Metrics Panel ───────────────────────────────────────────────

function MetricsPanel({ metrics }) {
  if (!metrics) return null;

  const cards = [
    { label: 'Total Plans', value: metrics.total_plans, color: 'blue' },
    { label: 'On-Time Rate', value: `${(metrics.on_time_rate * 100).toFixed(1)}%`, color: 'green' },
    { label: 'Over Budget', value: `${(metrics.over_budget_rate * 100).toFixed(1)}%`, color: 'red' },
    { label: 'Avg Confidence', value: `${(metrics.avg_confidence * 100).toFixed(1)}%`, color: 'yellow' },
    { label: 'Pending Approval', value: metrics.pending_approval, color: 'yellow' },
    { label: 'Approved Plans', value: metrics.approved_plans, color: 'green' },
  ];

  return (
    <div className="grid">
      {cards.map((c) => (
        <div className="card" key={c.label}>
          <h3>{c.label}</h3>
          <div className={`value ${c.color}`}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Plan List ───────────────────────────────────────────────────

function PlanList({ plans, onSelect }) {
  if (!plans || plans.length === 0) {
    return (
      <div className="empty-state">
        <p>No plans recorded yet</p>
        <p className="sub">Plans appear here after the LEARN phase completes.</p>
      </div>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Plan ID</th>
          <th>Created</th>
          <th>Confidence</th>
          <th>Demands</th>
          <th>Supplies</th>
          <th>Tags</th>
          <th>Outcome</th>
        </tr>
      </thead>
      <tbody>
        {plans.map((plan) => (
          <tr key={plan.plan_id} className="clickable" onClick={() => onSelect(plan.plan_id)}>
            <td>
              <a>{plan.plan_id.slice(0, 8)}…</a>
            </td>
            <td>{new Date(plan.created_at).toLocaleDateString()}</td>
            <td>
              {plan.plan_confidence != null
                ? <span className={`badge ${plan.plan_confidence >= 0.8 ? 'badge-green' : 'badge-yellow'}`}>
                    {(plan.plan_confidence * 100).toFixed(0)}%
                  </span>
                : '—'
              }
            </td>
            <td>{plan.demand_count}</td>
            <td>{plan.supply_count}</td>
            <td>
              {plan.tag_list.map((t) => (
                <span className={`tag ${t === 'on_time' ? 'green' : t === 'over_budget' ? 'red' : ''}`} key={t}>
                  {t}
                </span>
              ))}
              {plan.tag_list.length === 0 && '—'}
            </td>
            <td>
              {plan.outcome_recorded
                ? <span className={`badge ${plan.on_time ? 'badge-green' : 'badge-red'}`}>
                    {plan.on_time ? '✓ On Time' : '✗ Delayed'}
                  </span>
                : <span className="badge badge-yellow">Pending</span>
              }
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ─── Plan Detail ─────────────────────────────────────────────────

function PlanDetailView({ plan, onBack, onApprove, onReject }) {
  if (!plan) return null;

  return (
    <div>
      <button className="btn btn-outline" onClick={onBack} style={{ marginBottom: 16 }}>
        ← Back to Plans
      </button>

      {plan.warm_archived && (
        <div className="pending-alert">
          <span className="alert-icon">📦</span>
          <div className="alert-text">This plan is in <strong>warm storage</strong> (archive). Full detail no longer available.</div>
        </div>
      )}

      <div className="plan-detail">
        <div className="card">
          <h3>Plan Overview</h3>
          <table>
            <tbody>
              <tr><td style={{ width: 160 }}>Plan ID</td><td>{plan.plan_id}</td></tr>
              <tr><td>Correlation ID</td><td>{plan.correlation_id}</td></tr>
              <tr><td>Created</td><td>{new Date(plan.created_at).toLocaleString()}</td></tr>
              <tr><td>Confidence</td><td>{plan.plan_confidence != null ? `${(plan.plan_confidence * 100).toFixed(1)}%` : '—'}</td></tr>
              <tr><td>Tags</td><td>{plan.tags.map(t => <span className="tag" key={t}>{t}</span>)}</td></tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Context</h3>
          <table>
            <tbody>
              <tr><td>Demands</td><td>{plan.context?.demands?.length ?? 0}</td></tr>
              <tr><td>Supplies</td><td>{plan.context?.supplies?.length ?? 0}</td></tr>
              <tr><td>Policies</td><td>{plan.context?.policies?.length ?? 0}</td></tr>
              <tr><td>Degradation</td><td>{plan.context?.degradation_level ?? '—'}</td></tr>
            </tbody>
          </table>
        </div>

        {plan.outcome && (
          <div className="card">
            <h3>Outcome</h3>
            <table>
              <tbody>
                <tr><td>On Time</td><td>{plan.outcome.on_time ? '✓ Yes' : '✗ No'}</td></tr>
                <tr><td>Over Budget</td><td>{plan.outcome.over_budget ? '✓ Yes' : '✗ No'}</td></tr>
                <tr><td>Cost Variance</td><td>{plan.outcome.cost_variance_pct != null ? `${plan.outcome.cost_variance_pct}%` : '—'}</td></tr>
                <tr><td>Quality Score</td><td>{plan.outcome.quality_score != null ? `${(plan.outcome.quality_score * 100).toFixed(0)}%` : '—'}</td></tr>
                <tr><td>Violations</td><td>{plan.outcome.violations_detected ?? 0}</td></tr>
                <tr><td>Notes</td><td>{plan.outcome.notes || '—'}</td></tr>
              </tbody>
            </table>
          </div>
        )}

        <div className="card" style={{ gridColumn: '1 / -1' }}>
          <h3>Negotiation Rounds</h3>
          {plan.negotiations && plan.negotiations.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Round</th>
                  <th>Global Utility</th>
                  <th>Resolved</th>
                  <th>Resolution</th>
                </tr>
              </thead>
              <tbody>
                {plan.negotiations.map((r, i) => (
                  <tr key={i}>
                    <td>#{r.round_number ?? i + 1}</td>
                    <td>{r.global_utility != null ? (r.global_utility * 100).toFixed(1) + '%' : '—'}</td>
                    <td>{r.resolved ? '✓' : '✗'}</td>
                    <td>{r.resolution || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>No negotiation data available (warm-archived or empty).</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────

export default function ControlTower() {
  const [view, setView] = useState('dashboard');
  const [weights, setWeights] = useState(null);
  const [weightsDraft, setWeightsDraft] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [health, setHealth] = useState(null);

  // ── Load initial data ─────────────────────────────────────────

  useEffect(() => {
    fetchJSON('/api/weights').then(setWeights).catch(() => {});
    fetchJSON('/api/dashboard/metrics').then(setMetrics).catch(() => {});
    fetchJSON('/api/plans?limit=50').then(setPlans).catch(() => {});
    fetchJSON('/api/approvals').then(setPendingApprovals).catch(() => {});
    fetchJSON('/api/health').then(setHealth).catch(() => {});
  }, []);

  // ── WebSocket ─────────────────────────────────────────────────

  useEffect(() => {
    let ws;
    let reconnectTimer;

    function connect() {
      try {
        ws = new WebSocket(`${API.replace(/^http/, 'ws')}/ws`);
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimer = setTimeout(connect, 3000);
        };
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'weights_updated') {
              setWeights(msg.data);
            }
            if (msg.type === 'plan_recorded') {
              fetchJSON('/api/plans?limit=50').then(setPlans).catch(() => {});
            }
            if (msg.type === 'pending_approval') {
              setPendingApprovals((prev) => [...prev, msg]);
            }
            if (msg.type === 'plan_approved' || msg.type === 'plan_rejected') {
              setPendingApprovals((prev) => prev.filter((a) => a.plan_id !== msg.plan_id));
            }
          } catch {}
        };
      } catch {}
    }

    connect();
    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimer);
    };
  }, []);

  // ── Weights handler ────────────────────────────────────────────

  const handleWeightChange = useCallback((key, val) => {
    setWeightsDraft((prev) => ({ ...(prev || weights), [key]: val }));
  }, [weights]);

  const handleSaveWeights = useCallback(async () => {
    const draft = weightsDraft || weights;
    if (!draft) return;
    const result = await putJSON('/api/weights', draft);
    setWeights(result);
    setWeightsDraft(null);
  }, [weights, weightsDraft]);

  // ── Plan selection ─────────────────────────────────────────────

  const handleSelectPlan = useCallback(async (planId) => {
    try {
      const plan = await fetchJSON(`/api/plans/${planId}`);
      setSelectedPlan(plan);
      setView('detail');
    } catch {}
  }, []);

  const handleBack = useCallback(() => {
    setSelectedPlan(null);
    setView('dashboard');
  }, []);

  // ── Approval handlers ─────────────────────────────────────────

  const handleApprove = useCallback(async (planId) => {
    await postJSON(`/api/approvals/${planId}/approve`, { plan_id: planId, approved: true });
    fetchJSON('/api/approvals').then(setPendingApprovals).catch(() => {});
  }, []);

  const handleReject = useCallback(async (planId) => {
    await postJSON(`/api/approvals/${planId}/approve`, { plan_id: planId, approved: false });
    fetchJSON('/api/approvals').then(setPendingApprovals).catch(() => {});
  }, []);

  // ── Weights display ───────────────────────────────────────────

  const displayWeights = weightsDraft || weights || {
    cost: 0.3, delivery: 0.3, quality: 0.2, sustainability: 0.1, flexibility: 0.1,
  };

  // ── Render ────────────────────────────────────────────────────

  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'weights', label: 'Strategic Weights' },
    { id: 'plans', label: 'Plan History' },
    { id: 'approvals', label: `Approvals (${pendingApprovals.length})` },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>🧠 Axon</h1>
        <nav>
          {navItems.map((item) => (
            <a
              key={item.id}
              href="#"
              className={view === item.id ? 'active' : ''}
              onClick={(e) => { e.preventDefault(); setView(item.id); }}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div style={{ marginTop: 32, fontSize: 12, color: 'var(--text-secondary)' }}>
          <span className={`online-indicator ${wsConnected ? 'connected' : 'disconnected'}`} />
          {wsConnected ? 'Connected' : 'Disconnected'}
          <br />
          <span style={{ fontSize: 11 }}>
            {health?.database === 'connected' ? 'DB: Connected' : 'DB: Unavailable'}
          </span>
        </div>
      </aside>

      <main className="main">
        {/* DASHBOARD */}

        {view === 'dashboard' && (
          <>
            <div className="header">
              <h2>Control Tower</h2>
              <p>Axon Supply Chain Planning — executive overview</p>
            </div>

            {pendingApprovals.length > 0 && (
              <div className="pending-alert">
                <span className="alert-icon">⚠️</span>
                <div className="alert-text">
                  <strong>{pendingApprovals.length} plan(s)</strong> pending human approval.
                  <br />
                  <span style={{ fontSize: 13 }}>{pendingApprovals.map((a) => a.reason).join('; ')}</span>
                </div>
                <button className="btn btn-primary" onClick={() => setView('approvals')}>Review</button>
              </div>
            )}

            <MetricsPanel metrics={metrics} />

            <div className="section">
              <h3>Weights Overview</h3>
              <WeightsPanel
                weights={displayWeights}
                onChange={handleWeightChange}
                onSave={handleSaveWeights}
              />
            </div>

            <div className="section">
              <h3>Recent Plans</h3>
              <PlanList plans={plans.slice(0, 10)} onSelect={handleSelectPlan} />
            </div>
          </>
        )}

        {/* STRATEGIC WEIGHTS */}

        {view === 'weights' && (
          <>
            <div className="header">
              <h2>Strategic Weights</h2>
              <p>Adjust business priorities to influence the utility scoring engine.</p>
            </div>
            <div style={{ maxWidth: 500 }}>
              <WeightsPanel
                weights={displayWeights}
                onChange={handleWeightChange}
                onSave={handleSaveWeights}
              />
            </div>
          </>
        )}

        {/* PLAN HISTORY */}

        {view === 'plans' && (
          <>
            <div className="header">
              <h2>Plan History</h2>
              <p>All planning cycles recorded in the Experience Ledger.</p>
            </div>
            <div className="section">
              <PlanList plans={plans} onSelect={handleSelectPlan} />
            </div>
          </>
        )}

        {/* PLAN DETAIL */}

        {view === 'detail' && selectedPlan && (
          <PlanDetailView
            plan={selectedPlan}
            onBack={handleBack}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        )}

        {/* APPROVALS */}

        {view === 'approvals' && (
          <>
            <div className="header">
              <h2>Approvals</h2>
              <p>Plans requiring human review and sign-off.</p>
            </div>

            {pendingApprovals.length === 0 ? (
              <div className="empty-state">
                <p>No pending approvals</p>
                <p className="sub">All plans have been reviewed.</p>
              </div>
            ) : (
              pendingApprovals.map((pa) => (
                <div className="card" key={pa.plan_id} style={{ marginBottom: 16 }}>
                  <table>
                    <tbody>
                      <tr><td style={{ width: 140 }}>Plan ID</td><td>{pa.plan_id}</td></tr>
                      <tr><td>Reason</td><td>{pa.reason}</td></tr>
                      <tr><td>Created</td><td>{new Date(pa.created_at).toLocaleString()}</td></tr>
                    </tbody>
                  </table>
                  <div className="actions">
                    <button className="btn btn-green" onClick={() => handleApprove(pa.plan_id)}>
                      ✓ Approve
                    </button>
                    <button className="btn btn-red" onClick={() => handleReject(pa.plan_id)}>
                      ✗ Reject
                    </button>
                    <button className="btn btn-outline" onClick={() => handleSelectPlan(pa.plan_id)}>
                      View Details
                    </button>
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </main>
    </div>
  );
}
