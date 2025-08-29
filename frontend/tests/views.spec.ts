import { test, expect } from '@playwright/test'

test('navigate to timeline and graph', async ({ page }) => {
  await page.route('**/sources', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ results: [{ id: 1, name: 'Mock Source' }] })
  }))
  await page.route('**/events/geojson*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ type: 'FeatureCollection', features: [], count: 0 })
  }))
  await page.route('**/search*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ results: [{ id: 1, title: 'Timeline Item', detected_at: '2024-01-01T00:00:00Z', source_name: 'S' }] })
  }))
  await page.route('**/graph*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ nodes: [{ id: 1, label: 'Node1' }], edges: [] })
  }))

  await page.goto('/')

  await page.getByRole('button', { name: 'Timeline view' }).click()
  await expect(page.getByText('Timeline')).toBeVisible()
  await expect(page.getByText('Timeline Item')).toBeVisible()

  await page.getByRole('button', { name: 'Graph view' }).click()
  await expect(page.getByText('Graph')).toBeVisible()
})

