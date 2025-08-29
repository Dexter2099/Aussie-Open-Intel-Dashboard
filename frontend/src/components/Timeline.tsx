import React, { useEffect, useState } from 'react'

type EventItem = {
  id: number
  title: string
  event_type?: string
  detected_at?: string
  occurred_at?: string
  source_name?: string
  jurisdiction?: string
}

type Props = {
  apiBase: string
  q?: string
  timeRange?: string
  sourceId?: number | ''
}

export default function Timeline({ apiBase, q, timeRange, sourceId }: Props) {
  const [items, setItems] = useState<EventItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const run = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        params.set('limit', '500')
        params.set('sort', 'occurred_at')
        if (q) params.set('q', q)
        if (timeRange) params.set('time_range', timeRange)
        if (sourceId) params.set('source_id', String(sourceId))
        const res = await fetch(`${apiBase}/search?${params.toString()}`)
        const json = await res.json()
        const list: EventItem[] = (json.results || []).sort((a: any, b: any) => {
          const ta = Date.parse(a.occurred_at || a.detected_at || 0)
          const tb = Date.parse(b.occurred_at || b.detected_at || 0)
          return ta - tb
        })
        setItems(list)
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [apiBase, q, timeRange, sourceId])

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #eee', display: 'flex', alignItems: 'center', gap: 8 }}>
        <strong>Timeline</strong>
        {loading && <span style={{ fontSize: 12, opacity: 0.7 }}>Loading…</span>}
        <span style={{ marginLeft: 'auto', fontSize: 12, opacity: 0.7 }}>{items.length} items</span>
      </div>
      <div style={{ padding: 12 }}>
        {items.map((it) => {
          const ts = (it.occurred_at || it.detected_at || '').replace('T',' ').replace('Z','')
          return (
            <div key={it.id} style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 12, padding: '10px 0', borderBottom: '1px solid #f5f5f5' }}>
              <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#555' }}>{ts}</div>
              <div>
                <div style={{ fontWeight: 600 }}>{it.title}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{it.event_type} • {it.source_name || 'Unknown source'} {it.jurisdiction ? `• ${it.jurisdiction}` : ''}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

