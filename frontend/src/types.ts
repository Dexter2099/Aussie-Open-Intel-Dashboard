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
