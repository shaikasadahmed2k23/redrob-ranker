const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', (err) => errors.push(err.message));

  const filePath = 'file://' + path.resolve(__dirname, '..', 'dashboard.html');
  await page.goto(filePath);
  await page.waitForTimeout(300);

  // Expand a row first
  await page.locator('tbody tr.row').first().click();
  await page.waitForTimeout(200);

  // Now type in search -- focus should stay in the search box, not jump to a row
  await page.click('#searchInput');
  await page.keyboard.type('Search Engineer', { delay: 20 });
  await page.waitForTimeout(200);

  const activeId = await page.evaluate(() => document.activeElement.id);
  console.log('Active element after typing in search (should be searchInput):', activeId);

  const searchValue = await page.inputValue('#searchInput');
  console.log('Search input value (should be full string):', searchValue);

  const rowCount = await page.locator('tbody tr.row').count();
  console.log('Filtered rows:', rowCount);

  console.log(errors.length ? 'ERRORS: ' + JSON.stringify(errors) : 'NO ERRORS');
  await browser.close();
})();
