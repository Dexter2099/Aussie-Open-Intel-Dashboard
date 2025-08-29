import React, { useState } from 'react'
import MapView from './MapView'
import Timeline from './Timeline'
import Graph from './Graph'

export default function App() {
  const [view, setView] = useState<'map' | 'timeline' | 'graph'>('map')
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', gap: 8, padding: '8px 12px', borderBottom: '1px solid #eee' }}>
        <button onClick={() => setView('map')}>Map</button>
        <button onClick={() => setView('timeline')}>Timeline</button>
        <button onClick={() => setView('graph')}>Graph</button>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        {view === 'map' && <MapView />}
        {view === 'timeline' && <Timeline />}
        {view === 'graph' && <Graph />}
      </div>
    </div>
  )
}
