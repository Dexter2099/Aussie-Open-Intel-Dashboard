import axios from 'axios'
import type { Event } from '../types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
})

export function fetchEvents(types: string) {
  const typeParam = types ? `&type=${types}` : ''
  return api.get<Event[]>(`/events?since=48h${typeParam}`)
}
