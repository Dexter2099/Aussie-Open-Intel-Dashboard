import { useCallback, useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.markercluster'
import { fetchEvents } from '../lib/api'
import { EventType } from '../types'

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
}

export default function MapView({ types }: Props) {
  const mapRef = useRef<L.Map | null>(null)
  const clusterRef = useRef<L.MarkerClusterGroup>(L.markerClusterGroup())
  const [mapReady, setMapReady] = useState(false)

  const fetchData = useCallback(() => {
    if (!mapRef.current) return
    fetchEvents(types)
      .then((res) => {
        clusterRef.current.clearLayers()
        const markers: L.Marker[] = []
        res.data.forEach((ev) => {
          const loc = ev.location
          if (loc && typeof loc.lat === 'number' && typeof loc.lon === 'number') {
            const marker = L.marker([loc.lat, loc.lon], { icon: ICONS[ev.type] })
            const popupDiv = document.createElement('div')
            const localTime = new Date(ev.time).toLocaleString()
            popupDiv.innerHTML = `<strong>${ev.title}</strong><br/>${localTime}<br/>${ev.type}<br/><a href="${ev.source}" target="_blank" rel="noopener noreferrer">Source</a><br/>`
            const addBtn = document.createElement('button')
            addBtn.textContent = 'Add to Notebook'
            addBtn.type = 'button'
            addBtn.addEventListener('click', () => {
              // Stub action - replace with real notebook integration
              console.log('Add to Notebook', ev.id)
            })
            popupDiv.appendChild(addBtn)
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
  }, [types])

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
