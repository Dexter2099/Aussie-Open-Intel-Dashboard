import { test, expect } from '@playwright/test';

const mockEvent = {
  id: 1,
  title: 'Test Event',
  event_type: 'Other',
  source_name: 'Test Source',
  detected_at: '2024-01-01T00:00:00Z',
  lon: 151,
  lat: -33
};

const mockGeoJSON = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [mockEvent.lon, mockEvent.lat] },
      properties: { id: mockEvent.id, title: mockEvent.title, event_type: mockEvent.event_type, detected_at: mockEvent.detected_at }
    }
  ],
  count: 1
};

test('page loads and refresh populates results', async ({ page }) => {
  await page.route(/\/sources/, route => route.fulfill({ json: { results: [{id:1,name:'Test Source'}] } }));
  await page.route(/\/events\/geojson/, route => route.fulfill({ json: mockGeoJSON }));
  await page.route(/\/search/, route => route.fulfill({ json: { results: [mockEvent] } }));

  await page.goto('/');

  await expect(page.getByText('Aussie Open Intel')).toBeVisible();
  await expect(page.locator('canvas')).toBeVisible();

  await page.getByRole('button', { name: 'Refresh' }).click();
  await expect(page.getByText('Test Event')).toBeVisible();
});
