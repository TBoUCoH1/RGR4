import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, CalendarDays, Clock3, MapPin, ShieldAlert } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { eventsApi } from '../api'
import LoadingScreen from '../components/LoadingScreen'
import PageHeader from '../components/PageHeader'
import { severityLabels, statusLabels } from './IncidentDetailPage'
import type { EventStatus, ThreatLevel } from '../types'

const statuses: Record<EventStatus, string> = { planned: 'Запланировано', active: 'Идёт сейчас', completed: 'Завершено', cancelled: 'Отменено' }
const threats: Record<ThreatLevel, string> = { low: 'Низкий риск', medium: 'Средний риск', high: 'Высокий риск', critical: 'Критический риск' }
const formatDate = (value: string) => new Intl.DateTimeFormat('ru-RU', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value))

export default function EventDetailPage() {
  const { id } = useParams()
  const eventId = Number(id)
  const event = useQuery({ queryKey: ['event', eventId], queryFn: () => eventsApi.get(eventId), enabled: Number.isInteger(eventId) && eventId > 0 })
  const stats = useQuery({ queryKey: ['event-stats', eventId], queryFn: () => eventsApi.stats(eventId), enabled: event.isSuccess })
  const incidents = useQuery({ queryKey: ['event-incidents', eventId], queryFn: () => eventsApi.incidents(eventId), enabled: event.isSuccess })

  if (event.isLoading) return <LoadingScreen />
  if (!event.data) return <div className="page"><div className="empty-state panel">Мероприятие не найдено</div></div>
  return <div className="page"><Link to="/events" className="back-link"><ArrowLeft size={15} /> Вернуться к реестру</Link><PageHeader eyebrow={`Реестр  /  EVT-${String(event.data.id).padStart(3, '0')}`} title={event.data.title} description={event.data.description || 'Описание мероприятия не добавлено.'} action={<span className={`status-chip large ${event.data.status}`}>{statuses[event.data.status]}</span>} /><section className="panel detail-overview"><div className="detail-grid"><div><span className="detail-label">Уровень угрозы</span><strong className={`threat-tag ${event.data.threat_level}`}>{threats[event.data.threat_level]}</strong></div><div><span className="detail-label">Локация</span><strong><MapPin size={15} /> {event.data.location || 'Не указана'}</strong></div><div><span className="detail-label">Начало</span><strong><CalendarDays size={15} /> {formatDate(event.data.start_dt)}</strong></div><div><span className="detail-label">Окончание</span><strong><Clock3 size={15} /> {formatDate(event.data.end_dt)}</strong></div></div></section><div className="kpi-grid"><div className="kpi-card"><div className="kpi-icon blue"><ShieldAlert size={19} /></div><div><span>Всего инцидентов</span><strong>{stats.data?.incident_count ?? '—'}</strong></div></div><div className="kpi-card"><div className="kpi-icon orange"><ShieldAlert size={19} /></div><div><span>Открытые инциденты</span><strong>{stats.data?.open_incident_count ?? '—'}</strong></div></div></div><section className="panel table-panel"><div className="panel-head"><div><p className="eyebrow">Связанные данные</p><h2>Инциденты мероприятия</h2></div><Link to="/incidents" className="text-link">Весь журнал</Link></div><div className="table-wrap"><table><thead><tr><th>Инцидент</th><th>Серьёзность</th><th>Статус</th><th>Время</th></tr></thead><tbody>{incidents.data?.map((incident) => <tr key={incident.id}><td><Link className="table-title" to={`/incidents/${incident.id}`}><strong>{incident.title || `Инцидент #${incident.id}`}</strong></Link></td><td>{severityLabels[incident.severity]}</td><td><span className={`status-chip ${incident.status}`}>{statusLabels[incident.status]}</span></td><td>{incident.occurred_at ? formatDate(incident.occurred_at) : '—'}</td></tr>)}</tbody></table></div>{incidents.data && !incidents.data.length && <div className="empty-state">Инцидентов по мероприятию пока нет</div>}</section></div>
}
