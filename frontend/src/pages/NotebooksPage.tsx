import { useEffect, useState } from 'react'
import { fetchNotebooks, createNotebook, fetchNotebook, removeNotebookItem, api } from '../lib/api'
import type { Notebook, NotebookItem } from '../types'

export default function NotebooksPage() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([])
  const [newTitle, setNewTitle] = useState('')
  const [selected, setSelected] = useState<Notebook | null>(null)

  useEffect(() => {
    load()
  }, [])

  async function load() {
    const data = await fetchNotebooks()
    setNotebooks(data)
  }

  async function create() {
    if (!newTitle.trim()) return
    const nb = await createNotebook(newTitle.trim())
    setNotebooks([nb, ...notebooks])
    setNewTitle('')
  }

  async function open(id: string) {
    let nb = await fetchNotebook(id)
    const items = nb.items || []
    const withTitles: NotebookItem[] = await Promise.all(
      items.map(async (it) => {
        if (it.kind === 'event') {
          const res = await api.get(`/events/${it.ref_id}`)
          return { ...it, title: res.data.title }
        }
        if (it.kind === 'entity') {
          const res = await api.get(`/entities/${it.ref_id}`)
          return { ...it, title: res.data.name }
        }
        return it
      })
    )
    nb.items = withTitles
    setSelected(nb)
  }

  async function remove(itemId: string) {
    if (!selected) return
    await removeNotebookItem(selected.id, itemId)
    setSelected({
      ...selected,
      items: (selected.items || []).filter((i) => i.id !== itemId),
    })
  }

  return (
    <div className="p-4">
      <h1>Notebooks</h1>
      <div>
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="New notebook title"
        />
        <button onClick={create}>Create</button>
      </div>
      <ul>
        {notebooks.map((nb) => (
          <li key={nb.id}>
            <button onClick={() => open(nb.id)}>{nb.title}</button>
          </li>
        ))}
      </ul>
      {selected && (
        <div className="mt-4">
          <h2>{selected.title}</h2>
          <ul>
            {(selected.items || []).map((item) => (
              <li key={item.id}>
                <span style={{ marginRight: '0.5rem' }}>{item.title || item.ref_id}</span>
                <span
                  style={{
                    border: '1px solid #ccc',
                    padding: '0 4px',
                    marginRight: '0.5rem',
                  }}
                >
                  {item.kind}
                </span>
                <button onClick={() => remove(item.id)}>remove</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
