import { Routes, Route, Navigate } from 'react-router-dom'
import MapPage from './pages/MapPage'
codex/add-/graph-route-and-graphpage-component
import GraphPage from './pages/GraphPage'

import TimelinePage from './pages/TimelinePage'
main

export default function App() {
  return (
    <Routes>
      <Route path="/map" element={<MapPage />} />
codex/add-/graph-route-and-graphpage-component
      <Route path="/graph" element={<GraphPage />} />

      <Route path="/timeline" element={<TimelinePage />} />
main
      <Route path="*" element={<Navigate to="/map" replace />} />
    </Routes>
  )
}
