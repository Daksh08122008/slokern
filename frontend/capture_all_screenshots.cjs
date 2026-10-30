const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const TARGET_DIR = path.resolve(__dirname, '..', 'artifacts', 'screenshots');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function captureAll() {
  if (!fs.existsSync(TARGET_DIR)) {
    fs.mkdirSync(TARGET_DIR, { recursive: true });
  }

  console.log('[Capture] Launching Edge headless at 1920x1080...');
  const browser = await puppeteer.launch({
    executablePath: EDGE_PATH,
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--window-size=1920,1080',
    ],
    defaultViewport: {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
    },
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  page.on('console', (msg) => {
    const text = msg.text();
    if (!text.includes('[vite]') && !text.includes('React DevTools')) {
      console.log('  [Browser]', text);
    }
  });

  console.log('[Capture] Loading http://127.0.0.1:5173...');
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle0', timeout: 20000 });
  await sleep(2500); // Allow full hydration of experiments and smoke tests

  // 1. Overview Live
  console.log('[Capture] Capturing 01-overview-live.png...');
  const path01 = path.join(TARGET_DIR, '01-overview-live.png');
  await page.screenshot({ path: path01, fullPage: false });
  console.log('  ✓ Saved:', path01);

  // 2. Runtime Profile Modal
  console.log('[Capture] Opening Runtime Profile modal...');
  const runtimeBtn = await page.$('button[title*="Inspect active serving runtime"]');
  if (runtimeBtn) {
    await runtimeBtn.click();
    await sleep(800);
    const path02 = path.join(TARGET_DIR, '02-runtime-profile.png');
    await page.screenshot({ path: path02, fullPage: false });
    console.log('  ✓ Saved 02-runtime-profile.png');
    // Close modal by clicking backdrop or pressing Escape
    await page.keyboard.press('Escape');
    await sleep(500);
  } else {
    console.warn('  ⚠️ Runtime profile button not found');
  }

  // 3. Optimization Demo (Tuning Lab)
  console.log('[Capture] Navigating to Tuning Lab...');
  const tuningBtn = await page.$('button[title*="Tuning Lab"]');
  if (tuningBtn) {
    await tuningBtn.click();
    await sleep(1500);
    const path03 = path.join(TARGET_DIR, '03-optimization-demo.png');
    await page.screenshot({ path: path03, fullPage: false });
    console.log('  ✓ Saved 03-optimization-demo.png');
  } else {
    console.warn('  ⚠️ Tuning Lab button not found');
  }

  // 4. Experiment Details
  console.log('[Capture] Navigating to Experiments View...');
  const expBtn = await page.$('button[title*="Experiments"]');
  if (expBtn) {
    await expBtn.click();
    await sleep(1500);

    // Open first row or drawer
    const row = await page.$('.experiment-row, tr[role="button"], tr, table tbody tr');
    if (row) {
      await row.click();
      await sleep(1000);
    }
    const path04 = path.join(TARGET_DIR, '04-experiment-details.png');
    await page.screenshot({ path: path04, fullPage: false });
    console.log('  ✓ Saved 04-experiment-details.png');

    // Close drawer if open
    await page.keyboard.press('Escape');
    await sleep(400);
  } else {
    console.warn('  ⚠️ Experiments button not found');
  }

  // 5. Telemetry
  console.log('[Capture] Capturing 05-telemetry.png...');
  // Ensure we are in Experiments view and scroll TelemetryScrubber into view
  const scrubber = await page.$('.telemetry-scrubber, [class*="telemetry"]');
  if (scrubber) {
    await scrubber.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }));
    await sleep(800);
  }
  const path05 = path.join(TARGET_DIR, '05-telemetry.png');
  await page.screenshot({ path: path05, fullPage: false });
  console.log('  ✓ Saved 05-telemetry.png');

  // 6. Verification
  console.log('[Capture] Navigating to Verification...');
  const verifyBtn = await page.$('button[title*="Verification"]');
  if (verifyBtn) {
    await verifyBtn.click();
    await sleep(1500);
    const path06 = path.join(TARGET_DIR, '06-verification.png');
    await page.screenshot({ path: path06, fullPage: false });
    console.log('  ✓ Saved 06-verification.png');
  } else {
    console.warn('  ⚠️ Verification button not found');
  }

  // 7. Reports
  console.log('[Capture] Navigating to Reports...');
  const reportsBtn = await page.$('button[title*="Reports"]');
  if (reportsBtn) {
    await reportsBtn.click();
    await sleep(1800);
    const path07 = path.join(TARGET_DIR, '07-reports.png');
    await page.screenshot({ path: path07, fullPage: false });
    console.log('  ✓ Saved 07-reports.png');
  } else {
    console.warn('  ⚠️ Reports button not found');
  }

  await browser.close();
  console.log('[Capture] All 7 screenshots successfully captured!');
}

captureAll().catch((err) => {
  console.error('[Capture] Error:', err);
  process.exit(1);
});

