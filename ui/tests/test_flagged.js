const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('pageerror', (err) => console.log('PAGE ERROR:', err.message));

  const filePath = 'file://' + path.resolve(__dirname, '..', 'dashboard.html');
  await page.goto(filePath);
  await page.waitForTimeout(300);

  // filter to flagged candidates and expand the first one
  await page.selectOption('#flagFilter', 'flagged');
  await page.waitForTimeout(300);
  const flaggedCount = await page.locator('tbody tr.row').count();
  console.log('Flagged candidates:', flaggedCount);

  await page.locator('tbody tr.row').first().click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: __dirname + '/screenshot_flagged.png', fullPage: false });

  await browser.close();
})();
