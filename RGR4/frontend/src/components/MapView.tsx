import { useEffect } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import { MapPinned } from 'lucide-react'
import type { Incident } from '../types'
import { severityLabels, statusLabels } from '../pages/IncidentDetailPage'

const colors: Record<string, string> = { minor: '#65d6a4', moderate: '#f0ba56', serious: '#ff875f', critical: '#fb5570' }
function markerIcon(severity: string) { return L.divIcon({ className: 'incident-marker-wrap', html: `<span class="incident-marker" style="--marker-color:${colors[severity] || colors.minor}"></span>`, iconSize: [22, 22], iconAnchor: [11, 11] }) }
function FitBounds({ incidents }: { incidents: Incident[] }) { const map = useMap(); useEffect(() => { const points = incidents.filter((i) => i.latitude != null && i.longitude != null).map((i) => [i.latitude!, i.longitude!] as [number, number]); if (points.length) map.fitBounds(points, { padding: [30, 30], maxZoom: 13 }) }, [incidents, map]); return null }

export default function MapView({ incidents, compact = false }: { incidents: Incident[]; compact?: boolean }) {
  const placed = incidents.filter((incident) => incident.latitude != null && incident.longitude != null)
  return <div className={`map-frame ${compact ? 'map-compact' : ''}`}><MapContainer center={[55.75, 37.61]} zoom={compact ? 10 : 5} scrollWheelZoom={!compact} zoomControl={!compact}>
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <FitBounds incidents={placed} />
    {placed.map((incident) => <Marker key={incident.id} position={[incident.latitude!, incident.longitude!]} icon={markerIcon(incident.severity)}><Popup><strong>{incident.title || `Инцидент #${incident.id}`}</strong><br />{severityLabels[incident.severity]} · {statusLabels[incident.status]}</Popup></Marker>)}
  </MapContainer>{!placed.length && <div className="map-empty"><MapPinned size={20} /> Нет инцидентов с координатами</div>}</div>
}
