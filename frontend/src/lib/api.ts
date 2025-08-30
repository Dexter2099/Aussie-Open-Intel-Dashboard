import axios from 'axios'

codex/add-event-drawer-component
import type { Event, GraphData, TimelineEvent } from '../types'

import type {
  Event,
  GraphData,
  TimelineEvent,
  Notebook,
  NotebookItem,
} from '../types'
main

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
})

export function fetchEvents(types: string) {
  const typeParam = types ? `&type=${types}` : ''
  return api.get<Event[]>(`/events?since=48h${typeParam}`)
}

export function fetchEvent(id: string) {
  return api.get<Event>(`/events/${id}`)
}

export function fetchGraph(entityId: string) {
  const param = entityId ? `?entity_id=${entityId}` : ''
  return api.get<GraphData>(`/graph${param}`)
}
 codex/add-event-drawer-component

export async function fetchTimelineEvents(cursor?: string, limit = 50) {
  const url = `/events?limit=${limit}${cursor ? `&cursor=${cursor}` : ''}`
  const res = await api.get<TimelineEvent[]>(url)
  return {
    events: res.data,
    nextCursor: res.headers['x-next-cursor'] as string | undefined,
  }
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

export async function fetchNotebooks() {
  const res = await api.get<Notebook[]>('/notebooks')
  return res.data
}

export async function createNotebook(title: string) {
  const res = await api.post<Notebook>('/notebooks', { title })
  return res.data
}

export async function fetchNotebook(id: string) {
  const res = await api.get<Notebook>(`/notebooks/${id}`)
  return res.data
}

export async function addNotebookItem(
  notebookId: string,
  payload: { kind: 'event' | 'entity'; ref_id: string; note?: string }
) {
  const res = await api.post<NotebookItem>(`/notebooks/${notebookId}/items`, payload)
  return res.data
}

export async function removeNotebookItem(notebookId: string, itemId: string) {
  await api.delete(`/notebooks/${notebookId}/items/${itemId}`)
}

export async function fetchEntity(id: string) {
  const res = await api.get(`/entities/${id}`)
  return res.data as any
}

main
