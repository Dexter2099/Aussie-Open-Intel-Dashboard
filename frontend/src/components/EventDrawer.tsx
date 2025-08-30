import { useEffect, useRef } from 'react'
import { Event, EventType } from '../types'

interface Props {
  event: Event | null
  onClose: () => void
}

const TYPE_COLORS: Record<EventType, string> = {
  bushfire: '#e53935',
  weather: '#1e88e5',
  maritime: '#00897b',
  cyber: '#757575',
  news: '#757575',
}

export default function EventDrawer({ event, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!event) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    closeRef.current?.focus()
    return () => document.removeEventListener('keydown', handler)
  }, [event, onClose])

  if (!event) return null

  const localTime = new Date(event.time).toLocaleString()
  const color = TYPE_COLORS[event.type]

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        width: '90%',
        maxWidth: '320px',
        height: '100%',
        background: '#fff',
        boxShadow: '-2px 0 8px rgba(0,0,0,0.2)',
        padding: '1rem',
        zIndex: 1000,
        overflowY: 'auto',
      }}
    >
      <button
        onClick={onClose}
        ref={closeRef}
        aria-label="Close"
        style={{ float: 'right', background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
      >
        &times;
      </button>
      <h2 style={{ marginTop: 0 }}>{event.title}</h2>
      <div>{localTime}</div>
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
      <div>
        <a href={event.source} target="_blank" rel="noopener noreferrer">
          Source
        </a>
      </div>
    </div>
  )
}
