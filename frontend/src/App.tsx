import 'maplibre-gl/dist/maplibre-gl.css'
import maplibregl, { Map as MlMap } from 'maplibre-gl'
import React, { useEffect, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

type Feature = {
  type: 'Feature'
  geometry: { type: 'Point', coordinates: [number, number] }
  properties: Record<string, any>
}

type FC = {
  type: 'FeatureCollection'
  features: Feature[]
  count: number
}

export default function App() {
  const mapRef = useRef<MlMap | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [q, setQ] = useState('')
  const [timeRange, setTimeRange] = useState('')
  const [loading, setLoading] = useState(false)
  const [count, setCount] = useState(0)
  const [results, setResults] = useState<any[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [sources, setSources] = useState<{id:number; name:string; type?:string}[]>([])
  const [sourceId, setSourceId] = useState<number | ''>('')

  useEffect(() => {
    if (!containerRef.current) return
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [133.7751, -25.2744],
      zoom: 3.5,
      attributionControl: true
    })
    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    mapRef.current = map
    map.on('load', () => {
      // fetch sources
      fetch(`${API_BASE}/sources`).then(r => r.json()).then(data => setSources(data.results || [])).catch(console.error)
      refresh()
    })
    map.on('moveend', () => {
      // Optional: auto-refresh on map move. Commented to avoid excessive calls.
      // refresh()
    })
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  const refresh = async () => {
    if (!mapRef.current) return
    setLoading(true)
    try {
      const b = mapRef.current.getBounds()
      const bbox = `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`
      const params = new URLSearchParams()
      params.set('bbox', bbox)
      params.set('limit', '1000')
      if (q) params.set('q', q)
      if (timeRange) params.set('time_range', timeRange)
      if (sourceId) params.set('source_id', String(sourceId))
      const urlGeo = `${API_BASE}/events/geojson?${params.toString()}`
      const urlList = `${API_BASE}/search?${params.toString()}`
      const [resGeo, resList] = await Promise.all([fetch(urlGeo), fetch(urlList)])
      const data: FC = await resGeo.json()
      const list = await resList.json()
      setCount(data.count)
      setResults(list.results || [])
      upsertGeoJSON(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const upsertGeoJSON = (fc: FC) => {
    const map = mapRef.current
    if (!map) return
    const srcId = 'events'
    if (!map.getSource(srcId)) {
      map.addSource(srcId, { type: 'geojson', data: fc })
      map.addLayer({
        id: 'events-circle',
        type: 'circle',
        source: srcId,
        paint: {
          'circle-radius': [
            'interpolate', ['linear'], ['coalesce', ['get', 'severity'], 0.2],
            0, 4,
            0.5, 7,
            1, 11
          ],
          'circle-color': [
            'interpolate', ['linear'], ['coalesce', ['get', 'severity'], 0],
            0, '#4fc3f7',
            0.5, '#ffb74d',
            0.8, '#ef5350'
          ],
          'circle-opacity': 0.85,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff'
        }
      })
      map.addLayer({
        id: 'events-selected',
        type: 'circle',
        source: srcId,
        filter: ['==', ['get', 'id'], -1],
        paint: {
          'circle-radius': 13,
          'circle-color': 'transparent',
          'circle-stroke-width': 3,
          'circle-stroke-color': '#212121'
        }
      })
    } else {
      const src = map.getSource(srcId) as maplibregl.GeoJSONSource
      src.setData(fc as any)
    }

    // Click popup
    map.off('click', 'events-circle', noop)
    map.on('click', 'events-circle', (e) => {
      const f = e.features?.[0]
      if (!f) return
      const coords = (f.geometry as any).coordinates.slice()
      const p = f.properties as any
      const html = `<strong>${p.title ?? 'Event'}</strong><br/>${p.event_type ?? ''}<br/>Detected: ${p.detected_at ?? ''}`
      new maplibregl.Popup().setLngLat(coords).setHTML(html).addTo(map)
      setSelectedId(Number(p.id))
    })
  }

  const noop = () => {}

  const onRefreshClick = () => refresh()

  const setQuickRange = (hours: number) => {
    const end = new Date()
    const start = new Date(end.getTime() - hours * 3600 * 1000)
    setTimeRange(`${start.toISOString()}..${end.toISOString()}`)
  }

  return (
    <div style={{ display: 'grid', gridTemplateRows: '48px 1fr', height: '100%' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 12px', borderBottom: '1px solid #eee' }}>
        <strong style={{ marginRight: 8 }}>Aussie Open Intel</strong>
        <input placeholder="Search text (q)" value={q} onChange={(e) => setQ(e.target.value)} style={{ padding: 6, minWidth: 220 }} />
        <input placeholder="Time range (start..end)" value={timeRange} onChange={(e) => setTimeRange(e.target.value)} style={{ padding: 6, minWidth: 240 }} />
        <select value={sourceId} onChange={(e) => setSourceId(e.target.value ? Number(e.target.value) : '')} style={{ padding: 6 }}>
          <option value="">All sources</option>
          {sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <div style={{ display: 'flex', gap: 4, marginLeft: 8 }}>
          <button onClick={() => setQuickRange(3)} style={{ padding: '6px 8px' }}>Last 3h</button>
          <button onClick={() => setQuickRange(12)} style={{ padding: '6px 8px' }}>12h</button>
          <button onClick={() => setQuickRange(24)} style={{ padding: '6px 8px' }}>24h</button>
          <button onClick={() => setQuickRange(24*7)} style={{ padding: '6px 8px' }}>7d</button>
        </div>
        <button onClick={onRefreshClick} disabled={loading} style={{ padding: '6px 10px' }}>{loading ? 'Loading…' : 'Refresh'}</button>
        <span style={{ marginLeft: 'auto', opacity: 0.7 }}>{count} on map</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', minHeight: 0 }}>
        <div style={{ borderRight: '1px solid #eee', overflow: 'auto' }}>
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #f2f2f2', fontWeight: 600 }}>Results ({results.length})</div>
          <div>
            {results.map((r) => {
              const isSel = selectedId === r.id
              return (
                <div key={r.id}
                  id={`event-${r.id}`}
                  onClick={() => {
                    setSelectedId(r.id)
                    if (r.lon != null && r.lat != null && mapRef.current) {
                      mapRef.current.easeTo({ center: [r.lon, r.lat], zoom: Math.max(mapRef.current.getZoom(), 8) })
                      const html = `<strong>${r.title ?? 'Event'}</strong><br/>${r.event_type ?? ''}<br/>Detected: ${r.detected_at ?? ''}`
                      new maplibregl.Popup().setLngLat([r.lon, r.lat]).setHTML(html).addTo(mapRef.current)
                    }
                  }}
                  style={{
                    padding: '10px 12px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f5f5f5',
                    background: isSel ? '#e3f2fd' : 'transparent'
                  }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.title || 'Event'}</div>
                  <div style={{ fontSize: 12, color: '#666' }}>{r.event_type} • {r.source_name || 'Unknown source'}</div>
                  <div style={{ fontSize: 12, color: '#666' }}>{r.detected_at?.replace('T', ' ').replace('Z','')} {r.jurisdiction ? `• ${r.jurisdiction}` : ''}</div>
                </div>
              )
            })}
          </div>
        </div>
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      </div>
    </div>
  )
}
