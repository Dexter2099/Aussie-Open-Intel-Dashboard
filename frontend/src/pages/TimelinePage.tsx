import { useEffect, useState } from 'react'
import { fetchTimelineEvents } from '../lib/api'
codex/add-event-drawer-component
import EventDrawer from '../components/EventDrawer'
import type { TimelineEvent } from '../types'

import type { EventType, TimelineEvent } from '../types'
import EventDrawer from '../components/EventDrawer'

const EVENT_TYPES: EventType[] = ['bushfire', 'weather', 'maritime', 'cyber', 'news']
const TYPE_CHIPS = [
  { key: 'all', label: 'All' },
  ...EVENT_TYPES.map((t) => ({
    key: t,
    label: t.charAt(0).toUpperCase() + t.slice(1),
  })),
]

const RANGES = [
  { value: '24h', label: 'Last 24h' },
  { value: '48h', label: 'Last 48h' },
  { value: '7d', label: 'Last 7d' },
  { value: '30d', label: 'Last 30d' },
]
main

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [cursor, setCursor] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
codex/add-event-drawer-component

  const [selectedTypes, setSelectedTypes] = useState<EventType[]>([...EVENT_TYPES])
  const [since, setSince] = useState('48h')
 main
  const [openId, setOpenId] = useState<string | null>(null)

  const typeQuery =
    selectedTypes.length === EVENT_TYPES.length ? undefined : selectedTypes.join('|')

  const loadMore = (reset = false) => {
    if (loading) return
    setLoading(true)
    const currentCursor = reset ? undefined : cursor
    fetchTimelineEvents({ cursor: currentCursor, types: typeQuery, since })
      .then(({ events: newEvents, nextCursor }) => {
        setEvents((prev) => (reset ? newEvents : [...prev, ...newEvents]))
        setCursor(nextCursor)
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadMore(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeQuery, since])

  const toggleType = (key: string) => {
    if (key === 'all') {
      setSelectedTypes([...EVENT_TYPES])
    } else {
      setSelectedTypes((prev) =>
        prev.includes(key as EventType)
          ? prev.filter((t) => t !== key)
          : [...prev, key as EventType]
      )
    }
  }

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ marginBottom: '0.5rem' }}>
        {TYPE_CHIPS.map(({ key, label }) => {
          const active =
            key === 'all'
              ? selectedTypes.length === EVENT_TYPES.length
              : selectedTypes.includes(key as EventType)
          return (
            <button
              key={key}
              onClick={() => toggleType(key)}
              style={{
                marginRight: '0.5rem',
                padding: '0.25rem 0.5rem',
                borderRadius: '16px',
                border: '1px solid #ccc',
                backgroundColor: active ? '#1976d2' : '#e0e0e0',
                color: active ? '#fff' : '#000',
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          )
        })}
        <select
          value={since}
          onChange={(e) => setSince(e.target.value)}
          style={{ marginLeft: '1rem' }}
        >
          {RANGES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>
      {loading && events.length === 0 ? (
        <div>Loading...</div>
      ) : (
        events.map((ev) => (
          <div
            key={ev.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '0.5rem 0',
              borderBottom: '1px solid #ddd',
            }}
          >
codex/add-event-drawer-component
            {ev.event_type}
          </span>
          <div style={{ flex: 1 }}>{ev.title}</div>
          <button
            type="button"
            onClick={() => setOpenId(ev.id)}
            style={{ marginLeft: '1rem' }}
          >
            Open
          </button>
          <button
            type="button"
            onClick={() => console.log('Add to Notebook', ev.id)}
            style={{ marginLeft: '0.5rem' }}
          >
            Add to Notebook
          </button>
        </div>
      ))}

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
              onClick={() => setOpenId(ev.id)}
              style={{ marginLeft: '1rem' }}
            >
              Open
            </button>
            <button
              type="button"
              onClick={() => console.log('Add to Notebook', ev.id)}
              style={{ marginLeft: '0.5rem' }}
            >
              Add to Notebook
            </button>
          </div>
        ))
      )}

main
      {cursor && (
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button type="button" onClick={() => loadMore()} disabled={loading}>
            {loading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
      <EventDrawer eventId={openId} onClose={() => setOpenId(null)} />
    </div>
  )
}

