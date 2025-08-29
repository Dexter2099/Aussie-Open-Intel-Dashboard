import 'maplibre-gl/dist/maplibre-gl.css'
import maplibregl, { Map as MlMap } from 'maplibre-gl'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

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
  const initialBboxRef = useRef<string | null>(null)
  const [stats, setStats] = useState<{total:number; counts_by_type:any[]; counts_by_source:any[]}>({ total: 0, counts_by_type: [], counts_by_source: [] })

  const sourceColors = useMemo(() => {
    const palette = ['#e57373', '#64b5f6', '#81c784', '#ffb74d', '#ba68c8', '#4db6ac', '#9575cd', '#dce775', '#ff8a65', '#a1887f']
    const map: Record<number, string> = {}
    sources.forEach((s, i) => {
      map[s.id] = palette[i % palette.length]
    })
    return map
  }, [sources])

  // Parse URL on first render
  useEffect(() => {
    const sp = new URLSearchParams(window.location.search)
    const q0 = sp.get('q')
    const tr0 = sp.get('time_range')
    const sid0 = sp.get('source_id')
    const bbox0 = sp.get('bbox')
    const sel0 = sp.get('selected_id')
    if (q0) setQ(q0)
    if (tr0) setTimeRange(tr0)
    if (sid0 !== null) setSourceId(Number(sid0))
    if (bbox0) initialBboxRef.current = bbox0
    if (sel0) setSelectedId(Number(sel0))
  }, [])

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
      // If URL contained bbox, fit to it before refresh
      if (initialBboxRef.current) {
        const parts = initialBboxRef.current.split(',').map(Number)
        if (parts.length === 4 && parts.every((v) => Number.isFinite(v))) {
          const [minlon, minlat, maxlon, maxlat] = parts
          map.fitBounds([[minlon, minlat], [maxlon, maxlat]], { padding: 32, animate: false })
        }
      }
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
      if (sourceId !== '') params.set('source_id', String(sourceId))
      const urlGeo = `${API_BASE}/events/geojson?${params.toString()}`
      const urlList = `${API_BASE}/search?${params.toString()}`
      const urlStats = `${API_BASE}/stats/summary?${params.toString()}`
      const [resGeo, resList, resStats] = await Promise.all([fetch(urlGeo), fetch(urlList), fetch(urlStats)])
      const data: FC = await resGeo.json()
      const list = await resList.json()
      const s = await resStats.json()
      setCount(data.count)
      setResults(list.results || [])
      setStats(s)
      upsertGeoJSON(data)

      // Sync URL (avoid stacking history)
      const qs = new URLSearchParams()
      if (q) qs.set('q', q)
      if (timeRange) qs.set('time_range', timeRange)
      if (sourceId !== '') qs.set('source_id', String(sourceId))
      if (selectedId) qs.set('selected_id', String(selectedId))
      qs.set('bbox', bbox)
      const next = `${window.location.pathname}?${qs.toString()}`
      window.history.replaceState(null, '', next)

      // If selectedId present in URL and now we have results, recenter to it once
      if (selectedId && list.results) {
        const found = list.results.find((r: any) => r.id === selectedId)
        if (found && found.lon != null && found.lat != null && mapRef.current) {
          mapRef.current.easeTo({ center: [found.lon, found.lat], zoom: Math.max(mapRef.current.getZoom(), 8) })
        }
      }
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
      const html = `<strong>${p.title ?? 'Event'}</strong>`+
        `<br/>${p.event_type ?? ''}`+
        (p.source_name ? `<br/>Source: ${p.source_name}` : '')+
        `<br/>Detected: ${p.detected_at ?? ''}`+
        (p.severity != null ? `<br/>Severity: ${p.severity}` : '')+
        (p.confidence != null ? `<br/>Confidence: ${p.confidence}` : '')
      new maplibregl.Popup().setLngLat(coords).setHTML(html).addTo(map)
      const id = Number(p.id)
      setSelectedId(id)
      const sp = new URLSearchParams(window.location.search)
      sp.set('selected_id', String(id))
      window.history.replaceState(null, '', `${window.location.pathname}?${sp.toString()}`)
    })
  }

  const noop = () => {}

  const onRefreshClick = () => refresh()

  const setQuickRange = (hours: number) => {
    const end = new Date()
    const start = new Date(end.getTime() - hours * 3600 * 1000)
    setTimeRange(`${start.toISOString()}..${end.toISOString()}`)
  }

  const saveToNotebook = async (eventId: number) => {
    const title = window.prompt('Notebook title?')
    if (!title) return
    try {
      await fetch(`${API_BASE}/notebooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, items: [{ event: eventId }] })
      })
      window.alert('Saved to notebook')
    } catch (e) {
      console.error(e)
      window.alert('Failed to save')
    }
  }

  // Update selected ring highlight when selection changes
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (map.getLayer('events-selected')) {
      const id = selectedId ?? -1
      // @ts-ignore setFilter exists
      map.setFilter('events-selected', ['==', ['get', 'id'], id])
    }
  }, [selectedId])

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
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 16 }}>
          <span style={{ fontSize: 12, opacity: 0.8 }}>Legend:</span>
          <span style={{ width: 10, height: 10, background: '#4fc3f7', borderRadius: 9999 }} />
          <span style={{ fontSize: 12 }}>low</span>
          <span style={{ width: 10, height: 10, background: '#ffb74d', borderRadius: 9999 }} />
          <span style={{ fontSize: 12 }}>med</span>
          <span style={{ width: 10, height: 10, background: '#ef5350', borderRadius: 9999 }} />
          <span style={{ fontSize: 12 }}>high</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 16 }}>
          <span style={{ fontSize: 12, opacity: 0.8 }}>Total: {stats.total}</span>
          {stats.counts_by_type?.slice(0,4).map((t:any) => (
            <span key={t.event_type} style={{ fontSize: 12, background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>{t.event_type}: {t.c}</span>
          ))}
        </div>
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
                      const html = `<strong>${r.title ?? 'Event'}</strong>`+
                        `<br/>${r.event_type ?? ''}`+
                        (r.source_name ? `<br/>Source: ${r.source_name}` : '')+
                        `<br/>Detected: ${r.detected_at ?? ''}`+
                        (r.severity != null ? `<br/>Severity: ${r.severity}` : '')+
                        (r.confidence != null ? `<br/>Confidence: ${r.confidence}` : '')
                      new maplibregl.Popup().setLngLat([r.lon, r.lat]).setHTML(html).addTo(mapRef.current)
                    }
                    const sp = new URLSearchParams(window.location.search)
                    sp.set('selected_id', String(r.id))
                    window.history.replaceState(null, '', `${window.location.pathname}?${sp.toString()}`)
                  }}
                  style={{
                    padding: '10px 12px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f5f5f5',
                    background: isSel ? '#e3f2fd' : 'transparent'
                  }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.title || 'Event'}</div>
                  <div style={{ fontSize: 12, color: '#666' }}>
                    {r.event_type}
                    {r.source_name ? (
                      <>
                        {' '}
                        <span
                          className="source-badge"
                          style={{ backgroundColor: sourceColors[r.source_id] || '#999' }}
                        >
                          {r.source_name}
                        </span>
                      </>
                    ) : (
                      <> • Unknown source</>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: '#666' }}>{r.detected_at?.replace('T', ' ').replace('Z','')} {r.jurisdiction ? `• ${r.jurisdiction}` : ''}</div>
                  <button
                    onClick={(e) => { e.stopPropagation(); saveToNotebook(r.id) }}
                    style={{ marginTop: 6 }}
                  >
                    Save to notebook
                  </button>
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
