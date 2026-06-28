const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 768, height: 1024 } });
  const errors = [];
  page.on('pageerror', (err) => errors.push(err.message));

  const filePath = 'file://' + path.resolve(__dirname, '..', 'dashboard.html');
  await page.goto(filePath);
  await page.waitForTimeout(300);
  await page.screenshot({ path: __dirname + '/screenshot_tablet.png', fullPage: false });
  console.log(errors.length ? JSON.stringify(errors) : 'NO ERRORS (tablet load)');

  // Now test sorting only on a desktop-width viewport (>800px, where thead is visible)
  await page.setViewportSize({ width: 1024, height: 800 });
  await page.waitForTimeout(200);
  const sortKeys = ['candidate_id', 'title', 'yoe', 'location', 'score'];
  for (const key of sortKeys) {
    await page.click('th[data-key="' + key + '"]');
    await page.waitForTimeout(100);
    const rowCount = await page.locator('tbody tr.row').count();
    console.log('Sorted by', key, '-> rows:', rowCount);
  }

  await page.focus('#searchInput');
  const focused = await page.evaluate(() => document.activeElement.id);
  console.log('Focused element:', focused);

  await browser.close();
})();
