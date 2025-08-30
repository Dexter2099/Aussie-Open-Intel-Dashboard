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

codex/add-/graph-route-and-graphpage-component
export interface GraphNode {
  id: string
  label: string
  kind: 'entity' | 'event'
}

export interface GraphLink {
  source: string
  target: string
  weight: number
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]

export interface TimelineEvent {
  id: string
  title: string
  event_type: EventType
  detected_at: string
main
}
