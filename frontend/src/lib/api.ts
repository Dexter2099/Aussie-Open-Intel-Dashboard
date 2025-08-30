import axios from 'axios'

import type { Event, GraphData, TimelineEvent } from '../types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
})

export function fetchEvents(types: string) {
  const typeParam = types ? `&type=${types}` : ''
  return api.get<Event[]>(`/events?since=48h${typeParam}`)
}

export function fetchGraph(entityId: string) {
  const param = entityId ? `?entity_id=${entityId}` : ''
  return api.get<GraphData>(`/graph${param}`)
}

interface TimelineQuery {
  cursor?: string
  limit?: number
  types?: string
  since?: string
}

export async function fetchTimelineEvents({
  cursor,
  limit = 50,
  types,
  since,
}: TimelineQuery) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  if (since) params.set('since', since)
  if (types) params.set('type', types)
  const res = await api.get<TimelineEvent[]>(`/events?${params.toString()}`)
  return {
    events: res.data,
    nextCursor: res.headers['x-next-cursor'] as string | undefined,
  }
}

