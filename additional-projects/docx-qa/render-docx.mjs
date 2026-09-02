import { chromium } from 'playwright-core';

const browser = await chromium.launch({
  executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  headless: true,
  args: ['--no-sandbox', '--disable-gpu'],
});

try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  page.on('console', (message) => process.stderr.write(`console: ${message.text()}\n`));
  page.on('pageerror', (error) => process.stderr.write(`pageerror: ${error.message}\n`));
  page.on('requestfailed', (request) => process.stderr.write(`requestfailed: ${request.url()} ${request.failure()?.errorText}\n`));
  await page.goto('http://127.0.0.1:8011/render.html', { waitUntil: 'networkidle' });
  try {
    await page.waitForFunction(() => document.body.dataset.ready === 'true', null, { timeout: 30000 });
  } catch (error) {
    const status = await page.locator('#status').textContent().catch(() => 'missing status');
    process.stderr.write(`status: ${status}\n`);
    throw error;
  }
  const sections = await page.locator('section.docx').count();
  if (!sections) throw new Error('DOCX preview produced no pages');
  await page.pdf({
    path: 'C:\\Users\\user\\Documents\\Codex\\2026-08-26\\new-chat\\work\\earthcare-guide-render\\EarthCARE_Tracker_Calculations_and_Operations.pdf',
    width: '8.5in',
    height: '11in',
    printBackground: true,
    displayHeaderFooter: false,
    preferCSSPageSize: true,
    margin: { top: '0', right: '0', bottom: '0', left: '0' },
  });
  process.stdout.write(JSON.stringify({ pages: sections }));
} finally {
  await browser.close();
}
