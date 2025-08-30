import { Routes, Route, Navigate } from 'react-router-dom'

import MapPage from './pages/MapPage'
import GraphPage from './pages/GraphPage'
import TimelinePage from './pages/TimelinePage'
codex/add-event-drawer-component

import NotebooksPage from './pages/NotebooksPage'
main

export default function App() {
  return (
    <Routes>
      <Route path="/map" element={<MapPage />} />
      <Route path="/graph" element={<GraphPage />} />
      <Route path="/timeline" element={<TimelinePage />} />
 codex/add-event-drawer-component

      <Route path="/notebooks" element={<NotebooksPage />} />
main
      <Route path="*" element={<Navigate to="/map" replace />} />
    </Routes>
  )
}

