import { useCallback, useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.markercluster'
import api from '../lib/api'
import { Event } from '../types'

const FALLBACK_CENTER: [number, number] = [-27.47, 153.03]
const FALLBACK_ZOOM = 6

interface Props {
  types: string
}

export default function MapView({ types }: Props) {
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
