import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import Timeline from './Timeline'

describe('Timeline', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({
        results: [{ id: 1, title: 'Event', detected_at: '2024-01-01T00:00:00Z' }]
      })
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  it('renders events', async () => {
    render(<Timeline />)
    await screen.findByText('Event')
    const items = screen.getAllByRole('listitem')
    expect(items.length).toBe(1)
  })
})
