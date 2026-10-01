const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export type Page<T> = { items: T[]; total: number; limit: number; offset: number }
export type Vehicle = { id: string; vehicle_id: string; make: string; model: string; status: string }
export type AlertItem = {
  id: string; vehicle_id: string; alert_type: string; severity: string
  description: string; status: string; created_at: string | null
}
export type Recommendation = {
  id: string; vehicle_id: string; reason: string; recommended_action: string
  estimated_savings_usd: number; priority: string; status: string; created_at: string | null
}
export type Summary = {
  vehicle_count: number; active_vehicle_count: number; open_alert_count: number
  idle_cost_usd: number; potential_savings_usd: number
  fleet_efficiency_score: number | null; currency: string; as_of: string
}
export type LiveState = { vehicle_id: string; timestamp?: string; speed_kph?: string; engine_on?: string; fuel_level_litres?: string }
export type CostCategory = { category: string; cost_usd: number }
export type DailyMetric = { fleet_id: string; metric: string; value: number; window_start: string }

async function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  login: (email: string, password: string) => fetch(`${baseUrl}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  }).then(async response => {
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Sign in failed')
    return response.json() as Promise<{ access_token: string; expires_in: number }>
  }),
  me: (token: string) => request<{ user_id: string; email: string; fleet_id: string; role: string }>('/auth/me', token),
  summary: (token: string) => request<Summary>('/dashboard/summary', token),
  live: (token: string) => request<{ items: LiveState[] }>('/dashboard/live?limit=30', token),
  vehicles: (token: string) => request<Page<Vehicle>>('/vehicles?limit=100', token),
  alerts: (token: string) => request<Page<AlertItem>>('/alerts?limit=100', token),
  recommendations: (token: string) => request<Page<Recommendation>>('/recommendations?limit=100', token),
  costs: (token: string) => request<{ items: CostCategory[] }>('/analytics/cost?days=30', token),
  daily: (token: string) => request<DailyMetric[]>('/analytics/daily?days=30', token),
  updateAlert: (token: string, id: string, status: string) => request(`/alerts/${id}/status?status=${status}`, token, { method: 'PATCH' }),
  updateRecommendation: (token: string, id: string, status: string) => request(`/recommendations/${id}/status?status=${status}`, token, { method: 'PATCH' }),
}
