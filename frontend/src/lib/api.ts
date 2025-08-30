import axios from 'axios'
import type { Event, TimelineEvent } from '../types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
})

export function fetchEvents(types: string) {
  const typeParam = types ? `&type=${types}` : ''
  return api.get<Event[]>(`/events?since=48h${typeParam}`)
}

export async function fetchTimelineEvents(cursor?: string, limit = 50) {
  const url = `/events?limit=${limit}${cursor ? `&cursor=${cursor}` : ''}`
  const res = await api.get<TimelineEvent[]>(url)
  return { events: res.data, nextCursor: res.headers['x-next-cursor'] as string | undefined }
}
