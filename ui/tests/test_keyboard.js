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

  // Tab to first row and press Enter to expand
  await page.locator('tbody tr.row').first().focus();
  await page.keyboard.press('Enter');
  await page.waitForTimeout(200);
  let detailCount = await page.locator('.detail-panel').count();
  console.log('Detail panel after Enter on focused row:', detailCount);
  await page.screenshot({ path: __dirname + '/screenshot_keyboard_focus.png', fullPage: false });

  // Press Enter again to collapse
  await page.keyboard.press('Enter');
  await page.waitForTimeout(200);
  detailCount = await page.locator('.detail-panel').count();
  console.log('Detail panel after second Enter (collapse):', detailCount);

  // Tab to a sortable header and press Space to sort
  await page.locator('th[data-key="yoe"]').focus();
  await page.keyboard.press(' ');
  await page.waitForTimeout(200);
  const rowCount = await page.locator('tbody tr.row').count();
  console.log('Rows after Space-sorting by yoe:', rowCount);

  console.log(errors.length ? 'ERRORS: ' + JSON.stringify(errors) : 'NO ERRORS');
  await browser.close();
})();
