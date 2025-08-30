import { useCallback, useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.markercluster'
import { api } from '../lib/api'
import { Event, EventType } from '../types'

const FALLBACK_CENTER: [number, number] = [-27.47, 153.03]
const FALLBACK_ZOOM = 6

const ICONS: Record<EventType, L.Icon> = {
  bushfire: L.icon({
    iconUrl:
      'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiIGZpbGw9IiNlNTM5MzUiLz48L3N2Zz4=',
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
  }),
  weather: L.icon({
    iconUrl:
      'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiIGZpbGw9IiMxZTg4ZTUiLz48L3N2Zz4=',
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
  }),
  maritime: L.icon({
    iconUrl:
      'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiIGZpbGw9IiMwMDg5N2IiLz48L3N2Zz4=',
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
  }),
  cyber: L.icon({
    iconUrl:
      'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiIGZpbGw9IiM3NTc1NzUiLz48L3N2Zz4=',
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
  }),
  news: L.icon({
    iconUrl:
      'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiIGZpbGw9IiM3NTc1NzUiLz48L3N2Zz4=',
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
  }),
}

interface Props {
  types: string
  onSelect: (ev: Event) => void
}

export default function MapView({ types, onSelect }: Props) {
  const mapRef = useRef<L.Map | null>(null)
  const clusterRef = useRef<L.MarkerClusterGroup>(L.markerClusterGroup())
  const [mapReady, setMapReady] = useState(false)

  const fetchData = useCallback(() => {
    if (!mapRef.current) return
    const typeParam = types ? `&type=${types}` : ''
    api
      .get<Event[]>(`/events?since=48h${typeParam}`)
      .then((res) => {
        clusterRef.current.clearLayers()
        const markers: L.Marker[] = []
        res.data.forEach((ev) => {
          const loc = ev.location
          if (loc && typeof loc.lat === 'number' && typeof loc.lon === 'number') {
            const marker = L.marker([loc.lat, loc.lon], { icon: ICONS[ev.type] })
            const popupDiv = document.createElement('div')
            popupDiv.innerHTML = `<strong>${ev.title}</strong><br/>${new Date(ev.time).toLocaleString()}<br/>${ev.type}<br/>`
            const btn = document.createElement('button')
            btn.textContent = 'Open'
            btn.type = 'button'
            btn.addEventListener('click', () => {
              onSelect(ev)
              marker.closePopup()
            })
            popupDiv.appendChild(btn)
            marker.bindPopup(popupDiv)
            markers.push(marker)
          }
        })

        if (markers.length) {
          clusterRef.current.addLayers(markers)
          const bounds = L.latLngBounds(markers.map((m) => m.getLatLng()))
          mapRef.current!.fitBounds(bounds)
        }
      })
      .catch((err) => console.error(err))
  }, [types, onSelect])

  useEffect(() => {
    if (!mapReady) return
    fetchData()
    const id = setInterval(fetchData, 30000)
    return () => clearInterval(id)
  }, [fetchData, mapReady])

  return (
    <MapContainer
      center={FALLBACK_CENTER}
      zoom={FALLBACK_ZOOM}
      whenCreated={(map) => {
        mapRef.current = map
        map.addLayer(clusterRef.current)
        setMapReady(true)
      }}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
    </MapContainer>
  )
}
