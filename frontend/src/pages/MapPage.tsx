import { useState } from 'react'
import MapView from '../components/MapView'
import EventDrawer from '../components/EventDrawer'
import { MAP_EVENT_TYPES, MapEventType } from '../types'

const TYPES = MAP_EVENT_TYPES.map((t) => ({
  key: t,
  label: t.charAt(0).toUpperCase() + t.slice(1),
}))

export default function MapPage() {
  const [selected, setSelected] = useState<MapEventType[]>([...MAP_EVENT_TYPES])
  const [openId, setOpenId] = useState<string | null>(null)

  const toggle = (type: string) => {
    setSelected((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    )
  }

  const typeQuery = selected.join('|')

  return (
    <>
      <div style={{ padding: '0.5rem' }}>
        {TYPES.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => toggle(key)}
            style={{
              marginRight: '0.5rem',
              padding: '0.25rem 0.5rem',
              borderRadius: '16px',
              border: '1px solid #ccc',
              backgroundColor: selected.includes(key) ? '#1976d2' : '#e0e0e0',
              color: selected.includes(key) ? '#fff' : '#000',
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <MapView types={typeQuery} onOpen={setOpenId} />
      <EventDrawer eventId={openId} onClose={() => setOpenId(null)} />
    </>
  )
}
