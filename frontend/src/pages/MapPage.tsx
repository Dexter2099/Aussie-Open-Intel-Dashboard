import { useState } from 'react'
import MapView from '../components/MapView'

const TYPES = [
  { key: 'bushfire', label: 'Bushfire' },
  { key: 'weather', label: 'Weather' },
  { key: 'maritime', label: 'Maritime' },
]

export default function MapPage() {
  const [selected, setSelected] = useState<string[]>(TYPES.map((t) => t.key))

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
      <MapView types={typeQuery} />
    </>
  )
}
