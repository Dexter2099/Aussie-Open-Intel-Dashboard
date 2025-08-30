export type EventType = 'cyber' | 'bushfire' | 'maritime' | 'weather' | 'news'

export interface Event {
  id: string
  title: string
  type: EventType
  time: string // ISO
  location?: { lat: number; lon: number } | null
  entities: string[]
  source: string
}
