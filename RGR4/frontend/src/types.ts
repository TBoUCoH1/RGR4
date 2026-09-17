export type UserRole = 'admin' | 'coordinator' | 'security_officer' | 'analyst' | 'viewer'
export type EventStatus = 'planned' | 'active' | 'completed' | 'cancelled'
export type ThreatLevel = 'low' | 'medium' | 'high' | 'critical'
export type IncidentSeverity = 'minor' | 'moderate' | 'serious' | 'critical'
export type IncidentStatus = 'open' | 'investigating' | 'resolved' | 'closed'

export interface User {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponse { access_token: string; token_type: string; user: User }
export interface Event {
  id: number; title: string; description?: string | null; location?: string | null
  start_dt: string; end_dt: string; status: EventStatus; threat_level: ThreatLevel
  max_capacity?: number | null; created_by: number; created_at: string; updated_at: string
}
export interface IncidentUpdate { id: number; incident_id: number; user_id: number; status?: IncidentStatus | null; comment?: string | null; created_at: string }
export interface Incident {
  id: number; event_id: number; reported_by: number; title?: string | null; description: string
  severity: IncidentSeverity; status: IncidentStatus; latitude?: number | null; longitude?: number | null
  occurred_at?: string | null; resolved_at?: string | null; resolution?: string | null
  created_at: string; updated_at: string; updates: IncidentUpdate[]
}
export interface Paginated<T> { items: T[]; total: number; skip: number; limit: number }
export interface DashboardStats { events: number; incidents: number; open_incidents: number; active_events: number }
export interface IncidentFilters { event_id?: number; severity?: IncidentSeverity; status?: IncidentStatus; skip?: number; limit?: number }
export interface EventFilters { status?: EventStatus; threat_level?: ThreatLevel; date?: string; skip?: number; limit?: number }
