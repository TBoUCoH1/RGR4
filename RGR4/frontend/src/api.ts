import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from './store'
import type { TokenResponse, UserRole, AuthResponse, DashboardStats, Event, EventFilters, Incident, IncidentFilters, Paginated, User } from './types'
import { notify } from './components/ToastHost'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshPromise: Promise<string> | null = null
api.interceptors.response.use((response) => response, async (error: AxiosError) => {
  const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
  if (error.response?.status !== 401 || !original || original._retry || original.url?.includes('/auth/refresh') || original.url?.includes('/auth/login')) {
    if (error.response?.status === 401 && original?._retry) {
      useAuthStore.getState().clear()
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    if (error.response?.status === 403) notify('Недостаточно прав для этой операции', 'error')
    else if (error.response && error.response.status !== 401) notify((error.response.data as { error?: { message?: string }; detail?: string })?.error?.message || (error.response.data as { detail?: string })?.detail || 'Операция не выполнена', 'error')
    else if (!error.response) notify('Сервер недоступен. Проверьте подключение.', 'error')
    return Promise.reject(error)
  }
  original._retry = true
  try {
    refreshPromise ??= axios.post<AuthResponse>(`${api.defaults.baseURL}/auth/refresh`, {}, { withCredentials: true }).then(({ data }) => {
      useAuthStore.getState().setSession(data.access_token, data.user)
      return data.access_token
    }).finally(() => { refreshPromise = null })
    const token = await refreshPromise
    original.headers.Authorization = `Bearer ${token}`
    return api(original)
  } catch (refreshError) {
    useAuthStore.getState().clear()
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    return Promise.reject(refreshError)
  }
})

const params = (values: Record<string, string | number | undefined>) => Object.fromEntries(Object.entries(values).filter(([, value]) => value !== undefined && value !== ''))

export const authApi = {
  refresh: () => api.post<AuthResponse>('/auth/refresh').then((r) => r.data),
  logout: () => api.post('/auth/logout').then(() => undefined),
  me: () => api.get<User>('/auth/me').then((r) => r.data),
  register: (data: { email: string; full_name: string; password: string }) => api.post<User>('/auth/register', data).then((r) => r.data),
  login: (email: string, password: string, code?: string) =>
    api
    .post<TokenResponse>('/auth/login', {
      email,
      password,
      ...(code ? { code } : {}),
    })
    .then((r) => r.data),
}

export const dashboardApi = {
  stats: () => api.get<DashboardStats>('/dashboard/stats').then((r) => r.data)
}

export const incidentsApi = {
  list: (filters: IncidentFilters = {}) => api.get<Paginated<Incident>>('/incidents', { params: { ...params(filters as Record<string, string | number | undefined>) } }).then((r) => r.data),
  map: () => api.get<Incident[]>('/incidents/map').then((r) => r.data),
  get: (id: number) => api.get<Incident>(`/incidents/${id}`).then((r) => r.data),
  create: (data: Partial<Incident> & { event_id: number; description: string }) => api.post<Incident>('/incidents', data).then((r) => r.data),
  updateStatus: (id: number, data: { status: string; comment?: string; resolution?: string }) => api.patch<Incident>(`/incidents/${id}/status`, data).then((r) => r.data),
  update: (id: number, data: Partial<Incident>) => api.put<Incident>(`/incidents/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/incidents/${id}`).then(() => undefined)
}

export const eventsApi = {
  list: (filters: EventFilters = {}) => api.get<Paginated<Event>>('/events', { params: params(filters as Record<string, string | number | undefined>) }).then((r) => r.data),
  get: (id: number) => api.get<Event>(`/events/${id}`).then((r) => r.data),
  incidents: (id: number) => api.get<Incident[]>(`/events/${id}/incidents`).then((r) => r.data),
  stats: (id: number) => api.get<{ event_id: number; incident_count: number; open_incident_count: number }>(`/events/${id}/stats`).then((r) => r.data),
  create: (data: Omit<Event, 'id' | 'created_by' | 'created_at' | 'updated_at'>) => api.post<Event>('/events', data).then((r) => r.data),
  update: (id: number, data: Partial<Event>) => api.patch<Event>(`/events/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete<Event>(`/events/${id}`).then((r) => r.data)
}

export const usersApi = {
  list: (filters: { role?: string; skip?: number; limit?: number } = {}) => api.get<Paginated<User>>('/users', { params: params(filters) }).then((r) => r.data),
  create: (data: { email: string; full_name: string; role: string; password: string }) => api.post<User>('/users', data).then((r) => r.data),
  get: (id: number) => api.get<User>(`/users/${id}`).then((r) => r.data),
  update: (id: number, data: Partial<User> & { password?: string }) => api.put<User>(`/users/${id}`, data).then((r) => r.data),
  toggle: (id: number) => api.patch<User>(`/users/${id}/deactivate`).then((r) => r.data),
  remove: (id: number) => api.delete(`/users/${id}`).then(() => undefined)
}

export interface AuditLogItem {
  id: number;
  actor_id: number | null;
  actor_email?: string | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
}

export interface PaginatedAuditLogs {
  items: AuditLogItem[];
  total: number;
  skip: number;
  limit: number;
}

export const fetchAuditLogs = async (skip = 0, limit = 50): Promise<PaginatedAuditLogs> => {
  const response = await api.get('/audit-log', {
    params: { skip, limit },
  });
  return response.data;
};

export default api
