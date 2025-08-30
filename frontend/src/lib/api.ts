import axios from 'axios'
codex/add-get-/graph-api-and-frontend-integration
import type { Event, GraphData, TimelineEvent } from '../types'

 codex/add-crud-functionality-for-notebooks
import type { Event, GraphData, TimelineEvent, Notebook, NotebookItem } from '../types'


import type { Event, GraphData, TimelineEvent } from '../types'
main
 main

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
})

export function fetchEvents(types: string) {
  const typeParam = types ? `&type=${types}` : ''
  return api.get<Event[]>(`/events?since=48h${typeParam}`)
}

codex/add-get-/graph-api-and-frontend-integration

 codex/add-crud-functionality-for-notebooks

export function fetchEvent(id: string) {
  return api.get<Event>(`/events/${id}`)
}

 main
main
export function fetchGraph(entityId: string) {
  const param = entityId ? `?entity_id=${entityId}` : ''
  return api.get<GraphData>(`/graph${param}`)
}

export async function fetchTimelineEvents(cursor?: string, limit = 50) {
  const url = `/events?limit=${limit}${cursor ? `&cursor=${cursor}` : ''}`
  const res = await api.get<TimelineEvent[]>(url)codex/add-get-/graph-api-and-frontend-integration

codex/add-crud-functionality-for-notebooks
  return { events: res.data, nextCursor: res.headers['x-next-cursor'] as string | undefined }
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

export async function fetchEvent(id: string) {
  const res = await api.get<Event>(`/events/${id}`)
  return res.data
}

export async function fetchEntity(id: string) {
  const res = await api.get(`/entities/${id}`)
  return res.data as any

main
  return {
    events: res.data,
    nextCursor: res.headers['x-next-cursor'] as string | undefined,
  }
codex/add-get-/graph-api-and-frontend-integration

main
main
}

