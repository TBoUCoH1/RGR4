import { useQuery } from '@tanstack/react-query'
import { MapPinned } from 'lucide-react'
import { incidentsApi } from '../api'
import MapView from '../components/MapView'
import PageHeader from '../components/PageHeader'
export default function MapPage() { const query = useQuery({ queryKey: ['incident-map'], queryFn: incidentsApi.map }); return <div className="page"><PageHeader eyebrow="Операционный центр  /  Геопозиция" title="Карта обстановки" description="Пространственный обзор зарегистрированных инцидентов" action={<div className="map-legend"><span><i className="legend-dot minor" /> Незначительный</span><span><i className="legend-dot serious" /> Серьёзный</span><span><i className="legend-dot critical" /> Критический</span></div>} /><section className="map-full panel"><div className="map-toolbar"><span><MapPinned size={16} /> {query.data?.length ?? 0} инцидентов с координатами</span><span>OpenStreetMap · обновлено сейчас</span></div><MapView incidents={query.data || []} /></section></div> }
