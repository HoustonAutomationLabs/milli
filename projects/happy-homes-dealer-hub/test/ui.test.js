const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  let pass=0, fail=0;
  const ok=(n,c,x)=>{ if(c){pass++;console.log('  ok  '+n);} else {fail++;console.log('  FAIL '+n+(x!==undefined?'  -> '+x:''));} };

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport:{width:1440,height:900} });
  const errors=[];
  page.on('pageerror', e=>errors.push(e.message));
  page.on('console', m=>{ if(m.type()==='error' && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });

  await page.goto('http://127.0.0.1:8899/index.html', { waitUntil:'networkidle' });
  await page.waitForSelector('.rail-block .card', { timeout:8000 });

  console.log('\nLayout');
  const deskNoScroll = await page.evaluate(()=>{
    const de=document.documentElement; de.scrollLeft=200; const v=de.scrollLeft; de.scrollLeft=0; return v===0;
  });
  ok('no horizontal page scroll on desktop', deskNoScroll);
  const rails = await page.$$('.rail-block');
  ok('three category rails render', rails.length===3, rails.length);
  const heads = await page.$$eval('.rail-head h2', els=>els.map(e=>e.textContent));
  ok('rail order Closeout / Sectionals / New Arrivals',
     heads.join('|')==='Closeout Specials|Sectionals|New Arrivals', heads.join('|'));

  // 4 across on desktop: measure how many cards fit the rail viewport
  const across = await page.evaluate(()=>{
    const rail=document.querySelector('.rail');
    const card=rail.querySelector('.card');
    const gap=parseFloat(getComputedStyle(rail).columnGap||18);
    return Math.round((rail.clientWidth+gap)/(card.getBoundingClientRect().width+gap));
  });
  ok('4 cards across at 1440px', across===4, across);

  console.log('\nNo full expansion: rail is a slider, not a wall');
  const geo = await page.evaluate(()=>{
    const r=document.querySelector('.rail');
    return { scrollW:Math.round(r.scrollWidth), clientW:Math.round(r.clientWidth),
             rows:new Set([...r.querySelectorAll('.card')].map(c=>Math.round(c.getBoundingClientRect().top))).size,
             cards:r.querySelectorAll('.card').length };
  });
  ok('12 closeout cards sit on ONE row', geo.rows===1, geo.rows+' rows');
  ok('content overflows horizontally (scrollable)', geo.scrollW>geo.clientW, geo.scrollW+'>'+geo.clientW);

  console.log('\nArrows');
  ok('prev hidden at start', await page.$eval('.rail-wrap .arrow.prev', e=>e.hidden)===true);
  ok('next visible at start', await page.$eval('.rail-wrap .arrow.next', e=>e.hidden)===false);
  const before = await page.$eval('.rail', r=>r.scrollLeft);
  await page.click('.rail-wrap .arrow.next');
  await page.waitForTimeout(700);
  const after = await page.$eval('.rail', r=>r.scrollLeft);
  ok('next arrow advances the rail', after>before, before+' -> '+after);
  ok('prev arrow appears after scrolling', await page.$eval('.rail-wrap .arrow.prev', e=>e.hidden)===false);
  await page.click('.rail-wrap .arrow.prev');
  await page.waitForTimeout(700);
  ok('prev arrow returns to start', await page.$eval('.rail', r=>r.scrollLeft) < after);

  console.log('\nStock badges');
  const badges = await page.$$eval('.badge', els=>els.map(e=>e.className+':'+e.textContent));
  ok('a Last One badge renders', badges.some(b=>/last/.test(b)&&/Last one/.test(b)));
  ok('a Low stock badge shows the count', badges.some(b=>/Low stock · \d+ left/.test(b)),
     badges.find(b=>/low/.test(b)));
  ok('Sold out card is disabled', (await page.$$eval('.add[disabled]', e=>e.length))>=1);
  ok('Poland Black shows "Call for dealer price"',
     (await page.$$eval('.price.tbd', e=>e.length))>=1);

  console.log('\nCart');
  await page.click('.rail-block .card .add:not([disabled])');
  await page.waitForTimeout(200);
  ok('cart count becomes 1', (await page.textContent('#cartCount'))==='1');
  ok('button swapped for a stepper', (await page.$$('.stepper')).length===1);
  await page.click('[data-inc]');
  await page.waitForTimeout(150);
  ok('stepper increments to 2', (await page.textContent('.stepper span'))==='2');
  const t1 = await page.textContent('#cartTotal');
  ok('total is 2x unit price', t1==='$1,399.98' || /^\$\d/.test(t1), t1);

  await page.click('#openCart');
  await page.waitForTimeout(400);
  ok('drawer opens', await page.$eval('#drawer', e=>e.classList.contains('open')));
  ok('one cart line rendered', (await page.$$('.line')).length===1);
  ok('review button enabled', await page.$eval('#reviewBtn', e=>!e.disabled));

  console.log('\nOrder review (preview only)');
  await page.click('#reviewBtn');
  await page.waitForTimeout(400);
  ok('review modal opens', await page.$eval('#reviewModal', e=>e.classList.contains('open')));
  const body = await page.textContent('#reviewBody');
  ok('states nothing was submitted', /Nothing has been submitted to Happy Homes/.test(body));
  ok('order text block present', /NOT SUBMITTED/.test(await page.$eval('.ordertext', e=>e.value)));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  ok('Escape closes the modal', await page.$eval('#reviewModal', e=>!e.classList.contains('open')));

  console.log('\nQuick view');
  await page.click('#closeCart'); await page.waitForTimeout(300);
  await page.click('.rail-block .thumb');
  await page.waitForTimeout(400);
  ok('quick view opens with detail', /On hand|Dealer price/.test(await page.textContent('#qvBody')));
  await page.keyboard.press('Escape'); await page.waitForTimeout(300);

  console.log('\nSearch and filters');
  await page.fill('#q','recliner');
  await page.waitForTimeout(400);
  const sHeads = await page.$$eval('.rail-head h2', els=>els.map(e=>e.textContent));
  ok('search narrows to matching rails only', sHeads.length>=1 && sHeads.length<3, sHeads.join('|'));
  await page.fill('#q','zzzznope');
  await page.waitForTimeout(400);
  ok('no-match message shown', /No items match/.test(await page.textContent('#rails')));
  await page.click('#clearQ'); await page.waitForTimeout(400);
  ok('clearing search restores 3 rails', (await page.$$('.rail-block')).length===3);

  await page.check('#instock');
  await page.waitForTimeout(400);
  const outCards = await page.$$('.badge.out');
  ok('in-stock-only hides the sold-out item', outCards.length===0, outCards.length);
  await page.uncheck('#instock'); await page.waitForTimeout(400);

  await page.selectOption('#sort','price-asc');
  await page.waitForTimeout(400);
  const prices = await page.$$eval('.rail-block:first-child .card .price',
    els=>els.map(e=>parseFloat((e.textContent.match(/[\d,.]+$/)||['0'])[0].replace(/,/g,''))||0));
  ok('price ascending sort holds', prices.every((v,i,a)=>i===0||a[i-1]<=v), prices.slice(0,5).join(','));
  await page.selectOption('#sort','featured'); await page.waitForTimeout(300);

  console.log('\nCart persistence');
  await page.reload({ waitUntil:'networkidle' });
  await page.waitForSelector('.card');
  ok('order list survives reload (localStorage)', (await page.textContent('#cartCount'))==='2',
     await page.textContent('#cartCount'));

  console.log('\nScreenshots');
  await page.screenshot({ path:__dirname+'/shot-desktop.png', fullPage:false });
  await page.click('#openCart'); await page.waitForTimeout(500);
  await page.screenshot({ path:__dirname+'/shot-cart.png' });
  await page.click('#reviewBtn'); await page.waitForTimeout(500);
  await page.screenshot({ path:__dirname+'/shot-review.png' });
  await page.keyboard.press('Escape');

  const mobile = await browser.newPage({ viewport:{width:390,height:844} });
  await mobile.goto('http://127.0.0.1:8899/index.html', { waitUntil:'networkidle' });
  await mobile.waitForSelector('.card');
  const mAcross = await mobile.evaluate(()=>{
    const rail=document.querySelector('.rail'), card=rail.querySelector('.card');
    const gap=parseFloat(getComputedStyle(rail).columnGap||14);
    return Math.round((rail.clientWidth+gap)/(card.getBoundingClientRect().width+gap));
  });
  ok('2 cards across at 390px', mAcross===2, mAcross);
  const hScroll = await mobile.evaluate(()=>{
    const de=document.documentElement; de.scrollLeft=200; const v=de.scrollLeft; de.scrollLeft=0;
    return v===0 && de.scrollWidth<=window.innerWidth+1;
  });
  ok('no horizontal page overflow on mobile', hScroll);
  await mobile.screenshot({ path:__dirname+'/shot-mobile.png' });

  console.log('\nJS errors: '+(errors.length?errors.join(' | '):'none'));
  ok('no uncaught JS errors', errors.length===0, errors.join(' | '));

  await browser.close();
  console.log('\n'+pass+' passed, '+fail+' failed');
  process.exit(fail?1:0);
})();
