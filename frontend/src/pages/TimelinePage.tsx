import { useEffect, useState } from 'react'
import { fetchTimelineEvents } from '../lib/api'
import type { TimelineEvent } from '../types'

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [cursor, setCursor] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  const loadMore = () => {
    if (loading) return
    setLoading(true)
    fetchTimelineEvents(cursor)
      .then(({ events: newEvents, nextCursor }) => {
        setEvents((prev) => [...prev, ...newEvents])
        setCursor(nextCursor)
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadMore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div style={{ padding: '1rem' }}>
      {events.map((ev) => (
        <div
          key={ev.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '0.5rem 0',
            borderBottom: '1px solid #ddd',
          }}
        >
          <div style={{ width: '12rem', marginRight: '1rem' }}>
            {new Date(ev.detected_at).toLocaleString()}
          </div>
          <span
            style={{
              marginRight: '1rem',
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              backgroundColor: '#e0e0e0',
            }}
          >
            {ev.event_type}
          </span>
          <div style={{ flex: 1 }}>{ev.title}</div>
          <button
            type="button"
            onClick={() => console.log('Add to Notebook', ev.id)}
            style={{ marginLeft: '1rem' }}
          >
            Add to Notebook
          </button>
        </div>
      ))}
      {cursor && (
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button type="button" onClick={loadMore} disabled={loading}>
            {loading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  )
}
