import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowUpRight, CalendarCheck, ChevronRight, Clock3, MapPin, Radio, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { dashboardApi, eventsApi, incidentsApi } from '../api'
import MapView from '../components/MapView'
import PageHeader from '../components/PageHeader'
import { severityLabels, statusLabels } from './IncidentDetailPage'

const fmt = (date?: string | null) => date ? new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(date)) : 'Время не указано'

export default function DashboardPage() {
  const stats = useQuery({ queryKey: ['dashboard'], queryFn: dashboardApi.stats })
  const incidents = useQuery({ queryKey: ['incidents', 'recent'], queryFn: () => incidentsApi.list({ limit: 5 }) })
  const events = useQuery({ queryKey: ['events', 'active'], queryFn: () => eventsApi.list({ limit: 3 }) })
  const map = useQuery({ queryKey: ['incident-map'], queryFn: incidentsApi.map })
  const kpis = [
    { label: 'Активные мероприятия', value: stats.data?.active_events ?? '—', change: 'под контролем', icon: CalendarCheck, tone: 'blue', to: '/events' },
    { label: 'Открытые инциденты', value: stats.data?.open_incidents ?? '—', change: 'требуют внимания', icon: ShieldAlert, tone: 'orange', to: '/incidents' },
    { label: 'Всего инцидентов', value: stats.data?.incidents ?? '—', change: 'за всё время', icon: Activity, tone: 'violet', to: '/incidents' },
    { label: 'Мероприятия в системе', value: stats.data?.events ?? '—', change: 'всего объектов', icon: Radio, tone: 'green', to: '/events' },
  ]

  return <div className="page">
    <PageHeader eyebrow="Операционный центр" title="Добрый день, оператор" description="Сводка текущей обстановки и последние события" />
    <div className="kpi-grid">{kpis.map(({ label, value, change, icon: Icon, tone, to }) => <Link to={to} className="kpi-card" key={label}>
      <div className={`kpi-icon ${tone}`}><Icon size={19} /></div><div><span>{label}</span><strong>{value}</strong><small>{change}</small></div><ArrowUpRight className="kpi-arrow" size={16} />
    </Link>)}</div>
    <div className="dashboard-grid">
      <section className="panel incidents-panel"><div className="panel-head"><div><p className="eyebrow">Мониторинг</p><h2>Последние инциденты</h2></div><Link to="/incidents" className="text-link">Все инциденты <ChevronRight size={15} /></Link></div>
        {incidents.isLoading ? <div className="loading"><span className="inline-spinner" /> Загрузка журнала...</div> : incidents.data?.items.length ? <div className="incident-feed">{incidents.data.items.map((incident) => <Link className="feed-row" to={`/incidents/${incident.id}`} key={incident.id}><span className={`severity-dot ${incident.severity}`} /><span className="feed-main"><strong>{incident.title || incident.description.slice(0, 54)}</strong><small><Clock3 size={12} /> {fmt(incident.occurred_at)} <i /> {severityLabels[incident.severity]}</small></span><span className={`status-chip ${incident.status}`}>{statusLabels[incident.status]}</span><ChevronRight size={15} className="row-chevron" /></Link>)}</div> : <div className="empty-state">Инцидентов пока нет</div>}
      </section>
      <section className="panel event-panel"><div className="panel-head"><div><p className="eyebrow">Сейчас</p><h2>Ближайшие мероприятия</h2></div><Link to="/events" className="text-link">Открыть реестр <ChevronRight size={15} /></Link></div>
        {events.isLoading ? <div className="loading"><span className="inline-spinner" /> Загрузка мероприятий...</div> : <div className="event-list">{events.data?.items.map((event) => <div className="event-row" key={event.id}><div className={`event-date ${event.threat_level}`}><strong>{new Date(event.start_dt).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })}</strong><small>{new Date(event.start_dt).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</small></div><div className="event-main"><strong>{event.title}</strong><small><MapPin size={12} /> {event.location || 'Локация не указана'}</small></div><span className={`threat-tag ${event.threat_level}`}>{event.threat_level}</span></div>)}</div>}
      </section>
    </div>
    <section className="panel dashboard-map"><div className="panel-head"><div><p className="eyebrow">Геопозиции</p><h2>Карта обстановки</h2></div><Link to="/map" className="text-link">Открыть карту <ChevronRight size={15} /></Link></div><MapView incidents={map.data || []} compact /></section>
  </div>
}
