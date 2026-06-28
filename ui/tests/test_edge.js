const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', (err) => errors.push(err.message));
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });

  const filePath = 'file://' + path.resolve(__dirname, '..', 'dashboard.html');
  await page.goto(filePath);
  await page.waitForTimeout(300);

  // Empty search test
  await page.fill('#searchInput', 'zzzznonexistent');
  await page.waitForTimeout(300);
  const emptyVisible = await page.locator('#emptyState').isVisible();
  console.log('Empty state visible for no-match search:', emptyVisible);
  await page.screenshot({ path: __dirname + '/screenshot_empty.png', fullPage: false });
  await page.fill('#searchInput', '');

  // Click multiple rows in sequence (expand/collapse correctness)
  await page.locator('tbody tr.row').nth(0).click();
  await page.waitForTimeout(150);
  await page.locator('tbody tr.row').nth(0).click(); // collapse same row
  await page.waitForTimeout(150);
  let detailCount = await page.locator('.detail-panel').count();
  console.log('Detail panels after expand+collapse same row:', detailCount);

  await page.locator('tbody tr.row').nth(2).click();
  await page.waitForTimeout(150);
  await page.locator('tbody tr.row').nth(5).click();
  await page.waitForTimeout(150);
  detailCount = await page.locator('.detail-panel').count();
  console.log('Detail panels after expanding two different rows in sequence:', detailCount);

  // Mobile viewport test
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: __dirname + '/screenshot_mobile.png', fullPage: false });

  console.log(errors.length ? 'ERRORS: ' + JSON.stringify(errors) : 'NO ERRORS');
  await browser.close();
})();
