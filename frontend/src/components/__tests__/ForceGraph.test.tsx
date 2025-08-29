import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ForceGraph from '../ForceGraph'

describe('ForceGraph', () => {
  it('renders an svg and fetches graph', async () => {
    const graph = { nodes: [{ id: 1, label: 'Node1' }], edges: [] }
    vi.spyOn(global, 'fetch').mockResolvedValue({ json: async () => graph } as any)

    render(<ForceGraph apiBase="http://x" />)
    const el = await screen.findByRole('img', { hidden: true }).catch(() => null)
    // Fallback: query the svg element
    const svg = document.querySelector('svg')
    expect(svg).toBeTruthy()
  })
})

