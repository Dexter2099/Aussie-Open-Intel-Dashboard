import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.markercluster'
import api from '../lib/api'
import { Event } from '../types'

const FALLBACK_CENTER: [number, number] = [-27.47, 153.03]
const FALLBACK_ZOOM = 6

export default function MapView() {
  const mapRef = useRef<L.Map | null>(null)

  useEffect(() => {
    if (!mapRef.current) return
    const cluster = L.markerClusterGroup()

    api
      .get<Event[]>('/events?since=48h&type=bushfire|weather|maritime')
      .then((res) => {
        const markers: L.Marker[] = []
        res.data.forEach((ev) => {
          if (typeof ev.lat === 'number' && typeof ev.lon === 'number') {
            const marker = L.marker([ev.lat, ev.lon])
            const title = ev.title ?? 'Untitled'
            const time = (ev as any).time ?? ''
            const type = (ev as any).type ?? ''
            marker.bindPopup(`<strong>${title}</strong><br/>${time}<br/>${type}<br/>Open`)
            markers.push(marker)
          }
        })

        if (markers.length) {
          cluster.addLayers(markers)
          mapRef.current!.addLayer(cluster)
          const bounds = L.latLngBounds(markers.map((m) => m.getLatLng()))
          mapRef.current!.fitBounds(bounds)
        } else {
          mapRef.current!.setView(FALLBACK_CENTER, FALLBACK_ZOOM)
        }
      })
      .catch((err) => console.error(err))
  }, [])

  return (
    <MapContainer
      center={FALLBACK_CENTER}
      zoom={FALLBACK_ZOOM}
      whenCreated={(map) => (mapRef.current = map)}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
    </MapContainer>
  )
}
