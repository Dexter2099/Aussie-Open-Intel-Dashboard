import { useEffect, useState } from 'react'

import { fetchEvent } from '../lib/api'
import type { Event, EventType } from '../types'

interface Props {
  eventId: string | null
  onClose: () => void
}

const TYPE_COLORS: Record<EventType, string> = {
  bushfire: '#e53935',
  weather: '#1e88e5',
  maritime: '#00897b',
  cyber: '#757575',
  news: '#757575',
}

export default function EventDrawer({ eventId, onClose }: Props) {
  const [event, setEvent] = useState<Event | null>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!eventId) return
    setVisible(false)
    fetchEvent(eventId)
      .then((res) => setEvent(res.data))
      .catch((err) => console.error(err))
    // allow slide-in animation
    requestAnimationFrame(() => setVisible(true))
  }, [eventId])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  if (!eventId) return null

  const localTime = event ? new Date(event.time).toLocaleString() : ''
  const color = event ? TYPE_COLORS[event.type] : '#ccc'

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'rgba(0,0,0,0.3)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '90%',
          maxWidth: '360px',
          height: '100%',
          background: '#fff',
          boxShadow: '-2px 0 8px rgba(0,0,0,0.2)',
          padding: '1rem',
          overflowY: 'auto',
          transform: visible ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s ease-in-out',
        }}
      >
        {!event ? (
          <div>Loading...</div>
        ) : (
          <>
            <button
              onClick={onClose}
              aria-label="Close"
              style={{
                float: 'right',
                background: 'none',
                border: 'none',
                fontSize: '1.5rem',
                cursor: 'pointer',
              }}
            >
              &times;
            </button>
            <h2 style={{ marginTop: 0 }}>{event.title}</h2>
            <div style={{ margin: '0.5rem 0' }}>
              <span
                style={{
                  background: color,
                  color: '#fff',
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                }}
              >
                {event.type}
              </span>
            </div>
            <div>{localTime}</div>
            {event.entities.length > 0 && (
              <ul>
                {event.entities.map((ent) => (
                  <li key={ent}>{ent}</li>
                ))}
              </ul>
            )}
            <div style={{ margin: '0.5rem 0' }}>
              <a href={event.source} target="_blank" rel="noopener noreferrer">
                Source
              </a>
            </div>
            <button
              type="button"
              onClick={() => console.log('Add to Notebook', event.id)}
            >
              Add to Notebook
            </button>
          </>
        )}
      </div>
    </div>
  )
}

