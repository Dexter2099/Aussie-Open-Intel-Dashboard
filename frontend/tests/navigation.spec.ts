import { test, expect } from '@playwright/test'

test('navigate between views', async ({ page }) => {
  await page.route('**/sources', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ results: [] })
  }))
  await page.route('**/events/geojson*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ type: 'FeatureCollection', features: [], count: 0 })
  }))
  await page.route('**/search*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      results: [{ id: 1, title: 'Event 1', detected_at: '2024-01-01T00:00:00Z' }]
    })
  }))
  await page.route('**/graph', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      nodes: [{ id: 'a' }, { id: 'b' }],
      links: [{ source: 'a', target: 'b' }]
    })
  }))

  await page.goto('/')
  await page.waitForSelector('.maplibregl-canvas')

  await page.getByRole('button', { name: 'Timeline' }).click()
  await expect(page.getByText('Event 1')).toBeVisible()

  await page.getByRole('button', { name: 'Graph' }).click()
  await page.waitForSelector('svg circle')

  await page.getByRole('button', { name: 'Map' }).click()
  await expect(page.locator('.maplibregl-canvas')).toBeVisible()
})
