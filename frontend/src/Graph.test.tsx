import { render, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import Graph from './Graph'

describe('Graph', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({
        nodes: [{ id: 'a' }, { id: 'b' }],
        links: [{ source: 'a', target: 'b' }]
      })
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  it('renders nodes', async () => {
    render(<Graph />)
    await waitFor(() => {
      expect(document.querySelectorAll('circle').length).toBe(2)
    })
  })
})
