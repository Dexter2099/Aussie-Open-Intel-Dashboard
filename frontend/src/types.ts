export interface Event {
  id: number
  lat: number
  lon: number
  title?: string
  [key: string]: unknown
}
