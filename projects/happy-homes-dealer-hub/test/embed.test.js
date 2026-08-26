/**
 * Simulates how Assembly's auto-sizing embed hosts the portal: an iframe whose
 * height is repeatedly set to the measured content height. Verifies the height
 * converges instead of collapsing or running away, and that the drawer and
 * modal stay inside the visible frame.
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  let pass = 0, fail = 0;
  const ok = (n, c, x) => { if (c) { pass++; console.log('  ok  ' + n); }
                            else { fail++; console.log('  FAIL ' + n + (x !== undefined ? '  -> ' + x : '')); } };

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto('http://127.0.0.1:8899/test/host.html', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);

  // One auto-size pass = measure content, apply as iframe height.
  async function autoSizePass() {
    return page.evaluate(() => {
      const f = document.getElementById('frame');
      const h = f.contentDocument.documentElement.scrollHeight;
      f.style.height = h + 'px';
      return h;
    });
  }

  console.log('\nAuto-size convergence (starting from a 300px frame)');
  const heights = [];
  for (let i = 0; i < 6; i++) { heights.push(await autoSizePass()); await page.waitForTimeout(250); }
  console.log('    heights: ' + heights.join(' -> '));
  ok('height settles instead of growing every pass',
     heights[3] === heights[4] && heights[4] === heights[5], heights.join(','));
  ok('settles at the 720px floor, not a collapsed frame',
     heights[5] >= 720, heights[5]);
  ok('does not run away to a huge frame', heights[5] <= 2000, heights[5]);

  console.log('\nDesktop layout inside the auto-sized frame');
  const across = await page.evaluate(() => {
    const d = document.getElementById('frame').contentDocument;
    const rail = d.querySelector('.rail'), card = rail.querySelector('.card');
    const gap = parseFloat(d.defaultView.getComputedStyle(rail).columnGap || 18);
    return Math.round((rail.clientWidth + gap) / (card.getBoundingClientRect().width + gap));
  });
  ok('4 cards across at 1440px wide (not the mobile 2-up)', across === 4, across);

  console.log('\nDrawer and modal stay inside the visible frame');
  await page.evaluate(() => {
    const d = document.getElementById('frame').contentDocument;
    d.getElementById('openCart').click();
  });
  await page.waitForTimeout(500);
  const drawer = await page.evaluate(() => {
    const f = document.getElementById('frame');
    const d = f.contentDocument;
    const b = d.getElementById('drawer').getBoundingClientRect();
    const vh = d.documentElement.clientHeight, vw = d.documentElement.clientWidth;
    return { top: Math.round(b.top), bottom: Math.round(b.bottom), right: Math.round(b.right),
             vh, vw, frameH: Math.round(f.getBoundingClientRect().height) };
  });
  console.log('    drawer: ' + JSON.stringify(drawer));
  ok('drawer starts at the top of the frame', drawer.top >= -1 && drawer.top <= 2, drawer.top);
  ok('drawer bottom is within the frame', drawer.bottom <= drawer.vh + 2, drawer.bottom + ' vs ' + drawer.vh);
  ok('drawer is flush to the right edge', Math.abs(drawer.right - drawer.vw) <= 2,
     drawer.right + ' vs ' + drawer.vw);

  await page.evaluate(() => {
    const d = document.getElementById('frame').contentDocument;
    d.getElementById('closeCart').click();
  });
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    const d = document.getElementById('frame').contentDocument;
    d.querySelector('.rail-block .card .add:not([disabled])').click();
    d.getElementById('openCart').click();
  });
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    document.getElementById('frame').contentDocument.getElementById('reviewBtn').click();
  });
  await page.waitForTimeout(500);
  const modal = await page.evaluate(() => {
    const d = document.getElementById('frame').contentDocument;
    const b = d.querySelector('#reviewModal .sheet').getBoundingClientRect();
    return { top: Math.round(b.top), bottom: Math.round(b.bottom),
             vh: d.documentElement.clientHeight };
  });
  console.log('    modal sheet: ' + JSON.stringify(modal));
  ok('review modal is fully visible in the frame',
     modal.top >= -1 && modal.bottom <= modal.vh + 2, JSON.stringify(modal));

  await page.screenshot({ path: __dirname + '/shot-embedded.png' });

  console.log('\nNarrow frame (what you saw with auto-size OFF)');
  await page.setViewportSize({ width: 700, height: 900 });
  await page.waitForTimeout(500);
  const narrowAcross = await page.evaluate(() => {
    const d = document.getElementById('frame').contentDocument;
    const rail = d.querySelector('.rail'), card = rail.querySelector('.card');
    const gap = parseFloat(d.defaultView.getComputedStyle(rail).columnGap || 14);
    return Math.round((rail.clientWidth + gap) / (card.getBoundingClientRect().width + gap));
  });
  ok('a narrow frame really does give the 2-up mobile layout', narrowAcross === 2, narrowAcross);

  await browser.close();
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
