import { useState } from 'react'
import { MapContainer, Marker, TileLayer, useMapEvents } from 'react-leaflet'
import L from 'leaflet'

const markerIcon = L.divIcon({ className: 'location-picker-marker-wrap', html: '<span class="location-picker-marker"></span>', iconSize: [24, 24], iconAnchor: [12, 12] })

function ClickHandler({ onSelect }: { onSelect: (point: [number, number]) => void }) {
  useMapEvents({ click: ({ latlng }) => onSelect([latlng.lat, latlng.lng]) })
  return null
}

export default function IncidentLocationPicker({ latitude, longitude, onChange }: { latitude: string; longitude: string; onChange: (latitude: string, longitude: string) => void }) {
  const selected = latitude && longitude ? [Number(latitude), Number(longitude)] as [number, number] : null
  const [center] = useState<[number, number]>(selected || [55.75, 37.61])
  return <div className="location-picker"><MapContainer center={center} zoom={selected ? 14 : 10} scrollWheelZoom className="location-picker-map"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><ClickHandler onSelect={([lat, lng]) => onChange(lat.toFixed(6), lng.toFixed(6))} />{selected && <Marker position={selected} icon={markerIcon} />}</MapContainer><div className="location-picker-caption">Кликните по карте, чтобы поставить метку</div>{selected && <div className="location-picker-coordinates">{Number(latitude).toFixed(6)}, {Number(longitude).toFixed(6)}</div>}</div>
}
