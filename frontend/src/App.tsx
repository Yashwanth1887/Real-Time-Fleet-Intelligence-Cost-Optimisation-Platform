import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Activity, ArrowUpRight, Bell, CarFront, Check, ChevronDown, CircleHelp,
  Compass, Fuel, Gauge, LayoutDashboard, LogOut, Menu, RefreshCw, ShieldCheck,
  Sparkles, TrendingDown, Truck, X,
} from 'lucide-react'
import { api, type AlertItem, type CostCategory, type DailyMetric, type LiveState, type Page, type Recommendation, type Summary, type Vehicle } from './api'

type View = 'overview' | 'vehicles' | 'alerts' | 'recommendations' | 'analytics'
type User = { user_id: string; email: string; fleet_id: string; role: string }
type Data = {
  summary: Summary | null; live: LiveState[]; vehicles: Page<Vehicle> | null
  alerts: Page<AlertItem> | null; recommendations: Page<Recommendation> | null
  costs: CostCategory[]; daily: DailyMetric[]
}

const emptyData: Data = { summary: null, live: [], vehicles: null, alerts: null, recommendations: null, costs: [], daily: [] }
const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('fleetguard_token') || '')
  const [user, setUser] = useState<User | null>(null)
  const [view, setView] = useState<View>('overview')
  const [data, setData] = useState<Data>(emptyData)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [connected, setConnected] = useState(false)
  const [mobileNav, setMobileNav] = useState(false)

  const refresh = useCallback(async (accessToken = token) => {
    if (!accessToken) return
    setBusy(true)
    setError('')
    try {
      const [summary, live, vehicles, alerts, recommendations, costs, daily] = await Promise.all([
        api.summary(accessToken), api.live(accessToken), api.vehicles(accessToken),
        api.alerts(accessToken), api.recommendations(accessToken), api.costs(accessToken), api.daily(accessToken),
      ])
      setData({ summary, live: live.items, vehicles, alerts, recommendations, costs: costs.items, daily })
      setLastUpdated(new Date())
      setConnected(true)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Could not load fleet data'
      setError(message)
      setConnected(false)
      if (message.toLowerCase().includes('token') || message.toLowerCase().includes('bearer')) signOut()
    } finally {
      setBusy(false)
    }
  }, [token])

  useEffect(() => {
    if (!token) return
    const timer = window.setInterval(async () => {
      try {
        const [summary, live, alerts, recommendations, costs] = await Promise.all([
          api.summary(token), api.live(token), api.alerts(token), api.recommendations(token), api.costs(token),
        ])
        setData(previous => ({ ...previous, summary, live: live.items, alerts, recommendations, costs: costs.items }))
        setLastUpdated(new Date())
        setConnected(true)
      } catch { setConnected(false) }
    }, 5000)
    return () => window.clearInterval(timer)
  }, [token])

  useEffect(() => {
    if (!token) return
    api.me(token).then(setUser).then(() => refresh(token)).catch(() => signOut())
  }, [token, refresh])

  function signOut() {
    sessionStorage.removeItem('fleetguard_token')
    setToken('')
    setUser(null)
    setData(emptyData)
  }

  async function signIn(email: string, password: string) {
    const response = await api.login(email, password)
    sessionStorage.setItem('fleetguard_token', response.access_token)
    setToken(response.access_token)
  }

  async function changeAlert(item: AlertItem) {
    try {
      await api.updateAlert(token, item.id, item.status === 'open' ? 'resolved' : 'open')
      await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update alert') }
  }

  async function completeRecommendation(item: Recommendation) {
    try {
      await api.updateRecommendation(token, item.id, item.status === 'completed' ? 'open' : 'completed')
      await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update recommendation') }
  }

  if (!token) return <Login onSignIn={signIn} />

  const canManage = user?.role === 'ADMIN' || user?.role === 'FLEET_MANAGER'
  const openAlerts = data.alerts?.items.filter(item => item.status === 'open') ?? []
  const navItems: { id: View; label: string; icon: typeof LayoutDashboard; count?: number }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'vehicles', label: 'Vehicles', icon: Truck },
    { id: 'alerts', label: 'Alerts', icon: Bell, count: openAlerts.length },
    { id: 'recommendations', label: 'Actions', icon: Sparkles },
    { id: 'analytics', label: 'Analytics', icon: Activity },
  ]

  return (
    <div className="shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand-lockup"><div className="brand-mark"><Compass size={21} strokeWidth={2.4} /></div><div><b>fleetguard</b><span>FLEET INTELLIGENCE</span></div></div>
        <div className="fleet-switch"><div className="fleet-icon"><Truck size={17} /></div><div><small>ACTIVE FLEET</small><strong>Synthetic demo fleet</strong></div><ChevronDown size={15} /></div>
        <div className="nav-caption">WORKSPACE</div>
        <nav>{navItems.map(item => {
          const Icon = item.icon
          return <button className={`nav-link ${view === item.id ? 'active' : ''}`} key={item.id} onClick={() => { setView(item.id); setMobileNav(false) }}>
            <Icon size={18} strokeWidth={1.9} /><span>{item.label}</span>{item.count ? <i>{item.count}</i> : null}
          </button>
        })}</nav>
        <div className="sidebar-bottom">
          <div className="privacy-note"><ShieldCheck size={17} /><div><strong>Synthetic data</strong><span>No real driver data is used</span></div></div>
          <button className="nav-link help-link" onClick={() => setView('analytics')}><CircleHelp size={18} /><span>About the metrics</span></button>
          <div className="sidebar-user"><div className="avatar">{user?.email.slice(0, 1).toUpperCase() || 'F'}</div><div className="user-label"><strong>{user?.email ?? 'Fleet manager'}</strong><span>{user?.role?.replace('_', ' ') ?? 'Loading access…'}</span></div><button className="icon-button logout" title="Sign out" onClick={signOut}><LogOut size={16} /></button></div>
        </div>
      </aside>

      {mobileNav && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu icon-button" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="crumb"><span>Fleet operations</span><b>/</b><strong>{navItems.find(item => item.id === view)?.label}</strong></div>
          <div className="topbar-right"><div className={`live-indicator ${connected ? '' : 'offline-indicator'}`}><span />{connected ? 'API ONLINE · 5S POLL' : 'API OFFLINE'}</div><span className="top-divider" /><span className="updated-label">{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Waiting for data'}</span><button className={`icon-button refresh-button ${busy ? 'spinning' : ''}`} onClick={() => refresh()} disabled={busy} title="Refresh data"><RefreshCw size={17} /></button></div>
        </header>
        <div className="page-content">
          {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss"><X size={16} /></button></div>}
          {view === 'overview' && <Overview data={data} busy={busy} onAlerts={() => setView('alerts')} onActions={() => setView('recommendations')} />}
          {view === 'vehicles' && <VehiclesPage data={data} busy={busy} />}
          {view === 'alerts' && <AlertsPage alerts={data.alerts?.items ?? []} busy={busy} canManage={canManage} onChange={changeAlert} />}
          {view === 'recommendations' && <RecommendationsPage items={data.recommendations?.items ?? []} busy={busy} canManage={canManage} onChange={completeRecommendation} />}
          {view === 'analytics' && <AnalyticsPage data={data} busy={busy} />}
          <footer className="page-footer"><span>FleetGuard <i>•</i> Real-time fleet intelligence</span><span>Synthetic telemetry <i>•</i> Estimates are explainable</span></footer>
        </div>
      </main>
    </div>
  )
}

function Login({ onSignIn }: { onSignIn: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try { await onSignIn(email, password) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Sign in failed') }
    finally { setBusy(false) }
  }
  return <div className="login-screen">
    <div className="login-brand"><div className="brand-mark"><Compass size={22} /></div><b>fleetguard</b></div>
    <div className="login-card"><div className="login-eyebrow"><ShieldCheck size={15} /> SECURE FLEET ACCESS</div><h1>Good operations<br />start with clarity.</h1><p>Sign in to see where your fleet is spending time, fuel, and money.</p>
      <form onSubmit={submit}><label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" required placeholder="you@company.com" /></label><label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required placeholder="Your password" /></label>{error && <div className="login-error">{error}</div>}<button className="primary-button login-submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}<ArrowUpRight size={16} /></button></form>
      <div className="login-foot"><ShieldCheck size={15} />Protected with short-lived access tokens</div>
    </div><div className="login-note">Synthetic fleet data only <span>•</span> FleetGuard demo environment</div>
  </div>
}

function Overview({ data, busy, onAlerts, onActions }: { data: Data; busy: boolean; onAlerts: () => void; onActions: () => void }) {
  const summary = data.summary
  return <>
    <section className="page-heading"><div><div className="eyebrow">{new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase()} <span>•</span> FLEET OVERVIEW</div><h1>Good morning<span className="heading-period">.</span></h1><p>Here’s what’s happening across your fleet right now.</p></div><button className="range-select">Last 30 days <ChevronDown size={15} /></button></section>
    <div className="metric-grid">
      <MetricCard icon={Truck} label="Active vehicles" value={summary ? summary.active_vehicle_count.toLocaleString() : '—'} detail={summary ? `${summary.vehicle_count.toLocaleString()} registered` : 'Waiting for fleet data'} tone="blue" />
      <MetricCard icon={Fuel} label="Estimated idle cost" value={summary ? currency.format(summary.idle_cost_usd) : '—'} detail="From detected idle events" tone="amber" trend={<TrendingDown size={14} />} />
      <MetricCard icon={Bell} label="Open alerts" value={summary ? summary.open_alert_count.toString() : '—'} detail="Needs fleet manager review" tone="rose" onClick={onAlerts} />
      <MetricCard icon={Gauge} label="Fleet efficiency" value={summary?.fleet_efficiency_score == null ? '—' : `${summary.fleet_efficiency_score}`} suffix={summary?.fleet_efficiency_score == null ? '' : '/100'} detail={summary?.fleet_efficiency_score == null ? 'Awaiting trip summaries' : 'Deterministic fleet score'} tone="green" />
    </div>

    <div className="content-grid">
      <section className="panel cost-panel"><div className="panel-head"><div><div className="panel-kicker">COST BREAKDOWN <span className="data-dot" /></div><h2>Where money is going</h2></div><button className="text-button" onClick={onActions}>View actions <ArrowUpRight size={15} /></button></div>
        <CostBars costs={data.costs} busy={busy} />
        <div className="panel-foot-note"><span className="note-mark"><Fuel size={14} /></span><span>Costs use reported fuel rate × idle duration × configured fuel price.</span></div>
      </section>
      <section className="panel live-panel"><div className="panel-head"><div><div className="panel-kicker">LIVE VEHICLES <span className="pulse-dot" /></div><h2>On the move</h2></div><span className="live-count">{data.live.length} <small>reporting</small></span></div>
        <LiveList rows={data.live.slice(0, 5)} busy={busy} />
        <div className="panel-link-row"><span>Latest state from Redis</span><span className="data-source"><span /> LIVE</span></div>
      </section>
    </div>
    <div className="content-grid lower-grid">
      <section className="panel alert-panel"><div className="panel-head"><div><div className="panel-kicker">NEEDS ATTENTION</div><h2>Recent alerts</h2></div><button className="text-button" onClick={onAlerts}>All alerts <ArrowUpRight size={15} /></button></div>
        <AlertList rows={(data.alerts?.items ?? []).slice(0, 4)} busy={busy} />
      </section>
      <section className="savings-card"><div className="savings-icon"><Sparkles size={19} /></div><div className="savings-label">POTENTIAL SAVINGS</div><div className="savings-value">{summary ? currency.format(summary.potential_savings_usd) : '—'}</div><p>Estimated from open recommendations using the configured avoidable-cost assumption.</p><button className="savings-link" onClick={onActions}>Review recommended actions <ArrowUpRight size={15} /></button><div className="savings-decoration" /></section>
    </div>
  </>
}

function MetricCard({ icon: Icon, label, value, detail, tone, suffix, trend, onClick }: { icon: typeof Truck; label: string; value: string; detail: string; tone: string; suffix?: string; trend?: ReactNode; onClick?: () => void }) {
  return <button className={`metric-card metric-${tone} ${onClick ? 'metric-clickable' : ''}`} onClick={onClick}><div className="metric-top"><span className="metric-icon"><Icon size={17} /></span><span className="metric-label">{label}</span>{trend && <span className="metric-trend">{trend}</span>}</div><div className="metric-value">{value}<small>{suffix}</small></div><div className="metric-detail">{detail}</div></button>
}

function CostBars({ costs, busy }: { costs: CostCategory[]; busy: boolean }) {
  if (busy && !costs.length) return <div className="empty-chart">Loading cost analytics…</div>
  if (!costs.length) return <div className="empty-chart"><div className="empty-icon"><Fuel size={19} /></div><strong>No cost events yet</strong><span>Start the idle demo to see an explainable cost estimate here.</span></div>
  const max = Math.max(...costs.map(item => item.cost_usd), 0.01)
  return <div className="cost-bars">{costs.map(item => <div className="cost-row" key={item.category}><div className="cost-row-top"><span>{item.category.replaceAll('_', ' ')}</span><strong>{currency.format(item.cost_usd)}</strong></div><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(4, item.cost_usd / max * 100)}%` }} /></div></div>)}</div>
}

function LiveList({ rows, busy }: { rows: LiveState[]; busy: boolean }) {
  if (busy && !rows.length) return <div className="list-empty">Loading latest vehicle state…</div>
  if (!rows.length) return <div className="list-empty"><div className="empty-icon"><Activity size={18} /></div><strong>No live events received</strong><span>Start the simulator to bring vehicles online.</span></div>
  return <div className="live-list">{rows.map(row => <div className="live-row" key={row.vehicle_id}><div className="live-vehicle-icon"><CarFront size={17} /></div><div className="live-vehicle-copy"><strong>{row.vehicle_id}</strong><span>{row.engine_on === 'true' ? Number(row.speed_kph ?? 0) === 0 ? 'Engine on · stationary' : 'Engine on · moving' : 'Engine off'}</span></div><div className="live-speed">{Number(row.speed_kph ?? 0)}<small>km/h</small></div></div>)}</div>
}

function AlertList({ rows, busy }: { rows: AlertItem[]; busy: boolean }) {
  if (busy && !rows.length) return <div className="list-empty compact-empty">Loading alerts…</div>
  if (!rows.length) return <div className="list-empty compact-empty"><div className="empty-icon"><Check size={18} /></div><strong>All clear</strong><span>No alerts in the current data.</span></div>
  return <div className="alert-list">{rows.map(row => <div className="alert-row" key={row.id}><div className={`severity-dot severity-${row.severity}`} /><div className="alert-copy"><strong>{row.alert_type.replaceAll('_', ' ')}</strong><span>{row.vehicle_id} · {row.description}</span></div><time>{row.created_at ? new Date(row.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</time></div>)}</div>
}

function VehiclesPage({ data, busy }: { data: Data; busy: boolean }) {
  return <><section className="page-heading"><div><div className="eyebrow">FLEET DIRECTORY</div><h1>Your vehicles<span className="heading-period">.</span></h1><p>Latest registered vehicles and their current reported state.</p></div><div className="count-pill"><Truck size={15} />{data.vehicles?.total ?? '—'} vehicles</div></section>
    <section className="panel table-panel"><div className="table-toolbar"><div className="panel-title-inline"><div className="panel-kicker">VEHICLE REGISTER</div><h2>Fleet vehicles</h2></div><span className="table-meta">{data.vehicles?.items.length ?? 0} shown</span></div>
      <div className="table-wrap"><table><thead><tr><th>VEHICLE</th><th>STATUS</th><th>LIVE STATE</th><th>SPEED</th><th>FUEL LEVEL</th><th>LAST EVENT</th></tr></thead><tbody>{(data.vehicles?.items ?? []).map(vehicle => {
        const live = data.live.find(item => item.vehicle_id === vehicle.vehicle_id)
        return <tr key={vehicle.id}><td><div className="table-vehicle"><span><CarFront size={16} /></span><div><strong>{vehicle.vehicle_id}</strong><small>{vehicle.make} · {vehicle.model}</small></div></div></td><td><span className={`status-pill ${vehicle.status === 'active' ? 'status-active' : ''}`}><i />{vehicle.status}</span></td><td>{live ? live.engine_on === 'true' ? Number(live.speed_kph) > 0 ? 'In motion' : 'Idling' : 'Parked' : <span className="muted">No recent signal</span>}</td><td>{live ? `${live.speed_kph ?? 0} km/h` : '—'}</td><td>{live ? `${live.fuel_level_litres ?? '—'} L` : '—'}</td><td>{live?.timestamp ? new Date(live.timestamp).toLocaleString() : '—'}</td></tr>
      })}</tbody></table></div>
      {!data.vehicles?.items.length && <div className="empty-table"><Truck size={22} /><strong>{busy ? 'Loading vehicles…' : 'No vehicles registered'}</strong><span>Vehicles appear after synthetic telemetry triggers fleet registration.</span></div>}
    </section>
  </>
}

function AlertsPage({ alerts, busy, canManage, onChange }: { alerts: AlertItem[]; busy: boolean; canManage: boolean; onChange: (item: AlertItem) => void }) {
  return <><section className="page-heading"><div><div className="eyebrow">WHY IT NEEDS ATTENTION</div><h1>Fleet alerts<span className="heading-period">.</span></h1><p>Signals are tied to the vehicle and rule that produced them.</p></div><div className="count-pill"><Bell size={15} />{alerts.filter(item => item.status === 'open').length} open</div></section>
    <section className="panel table-panel"><div className="table-toolbar"><div className="panel-title-inline"><div className="panel-kicker">ALERT FEED</div><h2>Recent fleet signals</h2></div><span className="table-meta">{alerts.length} records</span></div>
      {alerts.length ? <div className="table-wrap"><table><thead><tr><th>SEVERITY</th><th>VEHICLE</th><th>DETECTION</th><th>WHY</th><th>STATUS</th><th /></tr></thead><tbody>{alerts.map(item => <tr key={item.id}><td><span className={`severity-label severity-label-${item.severity}`}><i />{item.severity}</span></td><td><strong>{item.vehicle_id}</strong></td><td>{item.alert_type.replaceAll('_', ' ')}</td><td className="reason-cell">{item.description}</td><td><span className={`status-pill ${item.status === 'open' ? 'status-open' : 'status-done'}`}><i />{item.status}</span></td><td>{canManage && <button className="small-action" onClick={() => onChange(item)}>{item.status === 'open' ? 'Resolve' : 'Reopen'}</button>}</td></tr>)}</tbody></table></div> : <div className="empty-table"><Bell size={22} /><strong>{busy ? 'Loading alerts…' : 'No alerts detected'}</strong><span>New alerts appear when the rules detect a fleet condition.</span></div>}
    </section>
  </>
}

function RecommendationsPage({ items, busy, canManage, onChange }: { items: Recommendation[]; busy: boolean; canManage: boolean; onChange: (item: Recommendation) => void }) {
  return <><section className="page-heading"><div><div className="eyebrow">TURN INSIGHT INTO ACTION</div><h1>Recommended actions<span className="heading-period">.</span></h1><p>Each action links a detected condition to its estimated operational impact.</p></div><div className="count-pill"><Sparkles size={15} />{items.filter(item => item.status === 'open').length} to review</div></section>
    {items.length ? <div className="recommendation-grid">{items.map(item => <article className="recommendation-card" key={item.id}><div className="rec-card-top"><div className="rec-icon"><Sparkles size={17} /></div><span className={`priority-pill priority-${item.priority}`}>{item.priority} priority</span></div><div className="rec-vehicle">{item.vehicle_id} <span>·</span> {item.reason}</div><h2>{item.recommended_action}</h2><div className="rec-savings"><div><small>POTENTIAL SAVINGS</small><strong>{currency.format(item.estimated_savings_usd)}</strong></div><span className={`status-pill ${item.status === 'open' ? 'status-open' : 'status-done'}`}><i />{item.status}</span></div>{canManage && <button className="rec-action" onClick={() => onChange(item)}>{item.status === 'completed' ? 'Mark open' : 'Mark complete'}<ArrowUpRight size={15} /></button>}</article>)}</div> : <section className="panel empty-panel"><div className="empty-icon"><Sparkles size={20} /></div><h2>{busy ? 'Loading recommended actions…' : 'No actions recommended yet'}</h2><p>When an operational rule detects a condition, FleetGuard will explain why it matters and what to do next.</p></section>}
  </>
}

function AnalyticsPage({ data, busy }: { data: Data; busy: boolean }) {
  const metrics = useMemo(() => data.daily.slice(0, 14), [data.daily])
  const dailyCost = metrics.filter(item => item.metric === 'daily_cost_usd')
  const max = Math.max(...dailyCost.map(item => item.value), 0.01)
  return <><section className="page-heading"><div><div className="eyebrow">HISTORICAL PERFORMANCE</div><h1>Analytics<span className="heading-period">.</span></h1><p>Stored fleet metrics and cost estimates from completed processing.</p></div><div className="range-select">Last 30 days <ChevronDown size={15} /></div></section>
    <div className="analytics-kpis"><div className="panel analytics-kpi"><span>Recorded idle cost</span><strong>{data.summary ? currency.format(data.summary.idle_cost_usd) : '—'}</strong><small>All persisted cost events</small></div><div className="panel analytics-kpi"><span>Potential savings</span><strong>{data.summary ? currency.format(data.summary.potential_savings_usd) : '—'}</strong><small>Configured avoidable-cost assumption</small></div><div className="panel analytics-kpi"><span>Fleet efficiency</span><strong>{data.summary?.fleet_efficiency_score == null ? '—' : `${data.summary.fleet_efficiency_score}/100`}</strong><small>Requires daily telemetry summaries</small></div></div>
    <section className="panel history-panel"><div className="panel-head"><div><div className="panel-kicker">DAILY COST HISTORY</div><h2>Cost trend</h2></div><span className="table-meta">Materialized analytics</span></div>
      {dailyCost.length ? <div className="history-chart">{dailyCost.slice().reverse().map((item, index) => <div className="history-column" key={`${item.window_start}-${index}`}><div className="history-value">{currency.format(item.value)}</div><div className="history-bar-wrap"><div className="history-bar" style={{ height: `${Math.max(5, item.value / max * 100)}%` }} /></div><small>{new Date(item.window_start).toLocaleDateString([], { month: 'short', day: 'numeric' })}</small></div>)}</div> : <div className="empty-chart"><div className="empty-icon"><Activity size={19} /></div><strong>{busy ? 'Loading analytics…' : 'No materialized history yet'}</strong><span>Run the daily analytics job after events have been recorded.</span></div>}
    </section>
    <section className="panel cost-panel analytics-costs"><div className="panel-head"><div><div className="panel-kicker">COST BY CONDITION</div><h2>Where cost was detected</h2></div></div><CostBars costs={data.costs} busy={busy} /></section>
  </>
}
