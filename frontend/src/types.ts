export type EventType = 'cyber' | 'bushfire' | 'maritime' | 'weather' | 'news'

// Subset of event types rendered on the map
export const MAP_EVENT_TYPES = ['bushfire', 'weather', 'maritime'] as const
export type MapEventType = (typeof MAP_EVENT_TYPES)[number]

export interface Event {
  id: string
  title: string
  type: EventType
  time: string // ISO
  location?: { lat: number; lon: number } | null
  entities: string[]
  source: string
}

export interface GraphNode {
  id: string
  label: string
  kind: 'entity' | 'event'
  type?: string
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
}

export interface GraphData {
  nodes: GraphNode[]
codex/add-event-drawer-component
  links: GraphLink[]

  edges: GraphEdge[]
main
}

export interface TimelineEvent {
  id: string
  title: string
  event_type: EventType
  detected_at: string
}

codex/add-event-drawer-component

export interface NotebookItem {
  id: string
  notebook_id: string
  kind: 'event' | 'entity'
  ref_id: string
  note?: string | null
  created_at?: string
  title?: string
}

export interface Notebook {
  id: string
  created_by: string
  title: string
  created_at?: string
  items?: NotebookItem[]
}

main
