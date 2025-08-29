import { test, expect } from '@playwright/test';

test('smoke test', async ({ page }) => {
  await page.route('**/sources', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ results: [{ id: 1, name: 'Mock Source' }] })
  }));
  await page.route('**/events/geojson*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      type: 'FeatureCollection',
      features: [{
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [150, -33] },
        properties: { id: 1 }
      }],
      count: 1
    })
  }));
  await page.route('**/search*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      results: [{
        id: 1,
        title: 'Event 1',
        event_type: 'fire',
        source_name: 'Mock Source',
        detected_at: '2024-01-01T00:00:00Z',
        lon: 150,
        lat: -33
      }]
    })
  }));

  await page.goto('/');
  await page.waitForSelector('.maplibregl-canvas');

  await page.getByRole('button', { name: 'Refresh' }).click();
  await expect(page.getByText('Results (1)')).toBeVisible();

  const canvas = page.locator('.maplibregl-canvas');
  const before = await canvas.evaluate(el => (el as HTMLCanvasElement).style.transform);

  await page.getByText('Event 1').click();
  await page.waitForTimeout(500);

  const after = await canvas.evaluate(el => (el as HTMLCanvasElement).style.transform);
  expect(after).not.toBe(before);
});
