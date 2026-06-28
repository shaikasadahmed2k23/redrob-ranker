const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push('CONSOLE ERROR: ' + msg.text());
  });
  page.on('pageerror', (err) => {
    errors.push('PAGE ERROR: ' + err.message);
  });

  const filePath = 'file://' + path.resolve(__dirname, '..', 'dashboard.html');
  await page.goto(filePath);
  await page.waitForTimeout(500);

  // Check basic structure rendered
  const rowCount = await page.locator('tbody tr.row').count();
  const statCount = await page.locator('.stat-card').count();
  console.log('Row count:', rowCount);
  console.log('Stat card count:', statCount);

  await page.screenshot({ path: __dirname + '/screenshot_initial.png', fullPage: false });

  // Test clicking a row to expand
  await page.locator('tbody tr.row').first().click();
  await page.waitForTimeout(300);
  const detailVisible = await page.locator('.detail-panel').count();
  console.log('Detail panels visible after click:', detailVisible);
  await page.screenshot({ path: __dirname + '/screenshot_expanded.png', fullPage: false });

  // Test search
  await page.fill('#searchInput', 'Search Engineer');
  await page.waitForTimeout(300);
  const filteredCount = await page.locator('tbody tr.row').count();
  console.log('Rows after searching "Search Engineer":', filteredCount);
  await page.screenshot({ path: __dirname + '/screenshot_search.png', fullPage: false });

  // Clear search, test country filter
  await page.fill('#searchInput', '');
  await page.selectOption('#countryFilter', 'India');
  await page.waitForTimeout(300);
  const indiaCount = await page.locator('tbody tr.row').count();
  console.log('Rows after filtering India:', indiaCount);

  // Reset, test sort
  await page.selectOption('#countryFilter', '');
  await page.click('th[data-key="yoe"]');
  await page.waitForTimeout(300);
  console.log('Sorted by yoe, no crash');

  if (errors.length) {
    console.log('\n=== ERRORS FOUND ===');
    errors.forEach(e => console.log(e));
    process.exit(1);
  } else {
    console.log('\n=== NO ERRORS ===');
  }

  await browser.close();
})();
