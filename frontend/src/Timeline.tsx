import React, { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function Timeline() {
  const [events, setEvents] = useState<any[]>([])

  useEffect(() => {
    fetch(`${API_BASE}/search?limit=100`)
      .then(r => r.json())
      .then(d => {
        const sorted = (d.results || []).sort((a: any, b: any) =>
          new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime()
        )
        setEvents(sorted)
      })
      .catch(console.error)
  }, [])

  return (
    <div style={{ overflow: 'auto', height: '100%' }}>
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #eee', fontWeight: 600 }}>Timeline</div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {events.map(e => (
          <li key={e.id} style={{ padding: '8px 12px', borderBottom: '1px solid #f5f5f5' }}>
            <div style={{ fontWeight: 600 }}>{e.title || 'Event'}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{e.detected_at?.replace('T', ' ').replace('Z', '')}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}
