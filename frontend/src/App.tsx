import { Routes, Route, Navigate } from 'react-router-dom'

import MapPage from './pages/MapPage'
import GraphPage from './pages/GraphPage'
import TimelinePage from './pages/TimelinePage'
codex/add-get-/graph-api-and-frontend-integration

codex/add-crud-functionality-for-notebooks
import NotebooksPage from './pages/NotebooksPage'

main
main

export default function App() {
  return (
    <Routes>
codex/add-crud-functionality-for-notebooks
        <Route path="/map" element={<MapPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/timeline" element={<TimelinePage />} />
        <Route path="/notebooks" element={<NotebooksPage />} />
        <Route path="*" element={<Navigate to="/map" replace />} />

      <Route path="/map" element={<MapPage />} />
      <Route path="/graph" element={<GraphPage />} />
      <Route path="/timeline" element={<TimelinePage />} />
      <Route path="*" element={<Navigate to="/map" replace />} />
main
    </Routes>
  )
}

