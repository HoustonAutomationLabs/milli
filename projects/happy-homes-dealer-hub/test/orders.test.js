/**
 * End-to-end for the Orders page: submits real orders through the dealer
 * portal, then works them in orders.html. Runs against serve.js, which
 * executes the real function handlers over an in-memory orders store.
 */
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  let pass = 0, fail = 0;
  const ok = (n, c, x) => { if (c) { pass++; console.log('  ok  ' + n); }
                            else { fail++; console.log('  FAIL ' + n + (x !== undefined ? '  -> ' + x : '')); } };

  const browser = await chromium.launch();
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });

  // Other suites in the same run submit orders; start from a known-empty store.
  await page.goto('http://127.0.0.1:8899/orders.html', { waitUntil: 'networkidle' });
  await page.evaluate(() => fetch('/__reset'));

  console.log('\nEmpty state before any order exists');
  await page.goto('http://127.0.0.1:8899/orders.html', { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  ok('says there are no orders yet', /No orders yet/.test(await page.textContent('#state')));
  ok('needs-action tile reads 0', (await page.textContent('.tile.new .n')) === '0');

  console.log('\nSubmit two orders from the dealer portal');
  const shop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  async function placeOrder(nItems, note) {
    await shop.goto('http://127.0.0.1:8899/index.html', { waitUntil: 'networkidle' });
    await shop.waitForSelector('.rail-block .card');
    await shop.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
    await shop.reload({ waitUntil: 'networkidle' });
    await shop.waitForSelector('.rail-block .card');
    const buttons = await shop.$$('.rail-block .card .add:not([disabled])');
    for (let i = 0; i < nItems; i++) { await buttons[i].click(); await shop.waitForTimeout(120); }
    await shop.click('#openCart'); await shop.waitForTimeout(350);
    await shop.click('#reviewBtn'); await shop.waitForTimeout(350);
    if (note) await shop.fill('#orderNotes', note);
    await shop.click('#submitBtn');
    await shop.waitForSelector('#reviewBody h3', { timeout: 8000 });
    return (await shop.textContent('#reviewBody')).match(/HH-\d{8}-\d{4}/)[0];
  }
  const ref1 = await placeOrder(2, 'PO 90210');
  const ref2 = await placeOrder(3, '');
  ok('two orders submitted with distinct references', ref1 !== ref2, ref1 + ' / ' + ref2);

  console.log('\nOrders page picks them up');
  await page.click('#refresh');
  await page.waitForTimeout(700);
  ok('two order rows render', (await page.$$('.order')).length === 2, (await page.$$('.order')).length);
  ok('newest order is listed first', (await page.textContent('.order .ref')) === ref2,
     await page.textContent('.order .ref'));
  ok('needs-action tile now reads 2', (await page.textContent('.tile.new .n')) === '2');
  ok('open value is not zero', (await page.textContent('.tile.value .n')) !== '$0.00',
     await page.textContent('.tile.value .n'));
  ok('both start as New', (await page.$$('.pill.New')).length === 2);

  console.log('\nExpanding an order shows its line items');
  await page.click('.order .order-head');
  await page.waitForTimeout(300);
  ok('row expands', await page.$eval('.order', e => e.classList.contains('open')));
  const rows = await page.$$eval('.order.open table.lines tbody tr', els => els.length);
  ok('three line items for the 3-item order', rows === 3, rows);
  ok('line table shows a dealer price',
     /\$\d/.test(await page.textContent('.order.open table.lines')));
  const first = await page.$$('.order');
  ok('the other order stays collapsed',
     !(await first[1].evaluate(e => e.classList.contains('open'))));

  console.log('\nDealer note is surfaced');
  await page.click('.order:nth-child(2) .order-head');
  await page.waitForTimeout(300);
  ok('PO note shown on the order that carried one',
     /PO 90210/.test(await page.textContent('.order:nth-child(2) .order-body')));

  console.log('\nWorking an order through the workflow');
  await page.click('.order.open [data-status="Confirmed"]');
  await page.waitForTimeout(800);
  const pills = await page.$$eval('.pill', els => els.map(e => e.textContent));
  ok('status pill flips to Confirmed', pills.indexOf('Confirmed') !== -1, pills.join(','));
  ok('needs-action tile drops to 1', (await page.textContent('.tile.new .n')) === '1');
  ok('row stayed expanded through the update',
     (await page.$$('.order.open')).length >= 1);

  console.log('\nThe change actually persisted, not just in the DOM');
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(700);
  ok('still Confirmed after a full reload',
     (await page.$$eval('.pill', els => els.map(e => e.textContent))).indexOf('Confirmed') !== -1);
  const api = await page.evaluate(() => fetch('/api/orders').then(r => r.json()));
  ok('the orders API agrees', api.orders.some(o => o.status === 'Confirmed'));

  console.log('\nFilters and search');
  await page.click('[data-filter="Confirmed"]');
  await page.waitForTimeout(350);
  ok('Confirmed filter shows one order', (await page.$$('.order')).length === 1);
  await page.click('[data-filter="All"]');
  await page.waitForTimeout(350);
  await page.fill('#q', 'zzzznope');
  await page.waitForTimeout(400);
  ok('no-match message for a bad search', /Nothing matches/.test(await page.textContent('#list')));
  await page.fill('#q', ref1);
  await page.waitForTimeout(400);
  ok('searching a reference finds exactly that order', (await page.$$('.order')).length === 1,
     (await page.$$('.order')).length);
  await page.fill('#q', '');
  await page.waitForTimeout(400);

  console.log('\nA rejected status change leaves the order alone');
  await page.route('**/api/order-status', r => r.fulfill({
    status: 502, contentType: 'application/json',
    body: JSON.stringify({ ok: false, error: 'Sheet is locked' }) }));
  await page.click('.order .order-head');
  await page.waitForTimeout(300);
  const before = await page.textContent('.order.open .pill');
  await page.click('.order.open [data-status="Shipped"]');
  await page.waitForSelector('.order.open .err', { timeout: 8000 });
  ok('error explains what happened', /Sheet is locked/.test(await page.textContent('.order.open .err')));
  ok('status pill unchanged', (await page.textContent('.order.open .pill')) === before, before);
  ok('buttons re-enabled for a retry',
     await page.$eval('.order.open [data-status="Shipped"]', e => !e.disabled));
  await page.unroute('**/api/order-status');

  console.log('\nThe demo loop: Orders -> Dealer Home -> order -> back');
  ok('order desk has a link back to Dealer Home', (await page.$('#toHome')) !== null);
  await page.click('#toHome');
  await page.waitForSelector('.rail-block .card', { timeout: 8000 });
  ok('landing on Dealer Home shows the catalogue', (await page.$$('.rail-block')).length === 3,
     (await page.$$('.rail-block')).length);
  ok('Dealer Home has a link out to the order desk', (await page.$('#toOrders')) !== null);

  await page.click('.rail-block .card .add:not([disabled])');
  await page.waitForTimeout(200);
  await page.click('#openCart'); await page.waitForTimeout(350);
  await page.click('#reviewBtn'); await page.waitForTimeout(350);
  await page.click('#submitBtn');
  await page.waitForSelector('#reviewBody h3', { timeout: 8000 });
  ok('confirmation offers the way back', (await page.textContent('#keepShoppingBtn')) === 'Back to catalogue',
     await page.textContent('#keepShoppingBtn'));
  await page.click('#keepShoppingBtn');
  await page.waitForTimeout(350);
  ok('back on the catalogue with the cart emptied',
     (await page.$$('.rail-block')).length === 3 && (await page.textContent('#cartCount')) === '0',
     await page.textContent('#cartCount'));

  await page.click('#toOrders');
  await page.waitForSelector('.order', { timeout: 8000 });
  ok('the new order is waiting on the desk', (await page.$$('.order')).length >= 1,
     (await page.$$('.order')).length);
  ok('and it is flagged as needing action',
     Number(await page.textContent('.tile.new .n')) >= 1, await page.textContent('.tile.new .n'));

  console.log('\nEmbed shape matches the dealer portal');
  const shell = await page.evaluate(() => {
    const de = document.documentElement;
    de.scrollLeft = 200; const canScroll = de.scrollLeft; de.scrollLeft = 0;
    const app = getComputedStyle(document.getElementById('app'));
    return { canScroll, position: app.position, overflow: app.overflow,
             minHeight: app.minHeight };
  });
  ok('no horizontal page scroll', shell.canScroll === 0);
  ok('#app is the positioned, clipped shell',
     shell.position === 'relative' && shell.overflow === 'hidden', JSON.stringify(shell));
  ok('720px floor for auto-sizing hosts', shell.minHeight === '720px', shell.minHeight);

  await page.screenshot({ path: __dirname + '/shot-orders.png' });

  ok('no uncaught JS errors', errors.length === 0, errors.join(' | '));
  await browser.close();
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
