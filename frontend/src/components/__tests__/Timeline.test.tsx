import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Timeline from '../Timeline'

describe('Timeline', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders items from search', async () => {
    const results = {
      results: [
        { id: 2, title: 'Later Event', detected_at: '2024-01-02T00:00:00Z', event_type: 'Other', source_name: 'S' },
        { id: 1, title: 'Early Event', detected_at: '2024-01-01T00:00:00Z', event_type: 'Other', source_name: 'S' }
      ]
    }
    vi.spyOn(global, 'fetch').mockResolvedValue({ json: async () => results } as any)

    render(<Timeline apiBase="http://x" />)
    await waitFor(() => expect(screen.getByText('Early Event')).toBeInTheDocument())
    expect(screen.getByText('Later Event')).toBeInTheDocument()
  })
})

