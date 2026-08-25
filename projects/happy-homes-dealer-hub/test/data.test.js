const A = require('./core.generated.js');
let pass=0, fail=0;
function ok(name, cond, extra){ if(cond){pass++; console.log('  ok  '+name);} else {fail++; console.log('  FAIL '+name+(extra?'  -> '+extra:''));} }

// --- real rows lifted from the three sheet tabs, including the awkward ones ---
const sectionals = [
 {SKU:'Rocket Onyx','Product Name':'Rocket Onyx Reversible Sectional (Black)',Category:'Stationary Sectionals',Collection:'Rocket',Color:'Black',Warehouse:'Houston',Inventory:'4',Status:'In Stock','Wholesale Price':'',MSRP:'369.99','Image URL':'https://www.happyhomesindustries.com/uploads/x_w1100.jpeg',Description:'Cord fabric.',ETA:''},
 {SKU:'POLAND BLACK','Product Name':'Poland Black Reversible Sectional With Pull-Out Bed',Category:'Stationary Sectionals',Collection:'Poland',Color:'Black',Warehouse:'Houston',Inventory:'0',Status:'Sold Out','Wholesale Price':'',MSRP:'','Image URL':'https://www.happyhomesindustries.com/uploads/y_w6979.jpeg',Description:'Pull-out bed.',ETA:'9/7'},
 {SKU:'ARIA BLACK','Product Name':'Aria Black Sectional',Category:'Stationary Sectionals',Collection:'Aria',Color:'Black',Warehouse:'Houston',Inventory:'3',Status:'In Stock','Wholesale Price':'',MSRP:'$499.99','Image URL':'https://www.happyhomesindustries.com/uploads/z_w6003.jpeg',Description:'',ETA:''}
];
const arrivals = [
 {SKU:'517','Product Name':'517 - Reversible Sectional',Category:'New Arrivals',Collection:'',Color:'Chocolate',Warehouse:'Houston',Inventory:'4',Status:'In Stock','Wholesale Price':'',MSRP:'499.99','Image URL':'http://www.happyhomesindustries.com/uploads/a_w6629.jpeg?width=2560',Description:'Reversible.',ETA:''},
 {SKU:'U107','Product Name':'Ashley U107 - Modular Sectional',Category:'New Arrivals',Collection:'',Color:'',Warehouse:'Houston',Inventory:'2',Status:'Low Stock','Wholesale Price':'',MSRP:'3599.99','Image URL':'https://x/b.jpeg?width=2560',Description:'6-piece.',ETA:''}
];
const closeouts = [
 {SKU:'A8010236','Product Name':'Ashley A8010236 - Accent Mirror',Category:'Closeout Specials',Collection:'',Color:'Antique White',Warehouse:'Houston',Inventory:'1',Status:'Last One','Wholesale Price':'',MSRP:'9.99','Image URL':'https://x/c.jpeg',Description:'4-digit code note.',ETA:''},
 {SKU:'310-04','Product Name':'Ashley 310-04 Sectional',Category:'Closeout Specials',Collection:'',Color:'Pebble',Warehouse:'Houston',Inventory:'4',Status:'In Stock','Wholesale Price':'',MSRP:'699.99','Image URL':'https://x/d.jpeg',Description:'',ETA:''},
 {SKU:'310-04','Product Name':'Ashley 310-04 Sofa & Loveseat',Category:'Closeout Specials',Collection:'',Color:'Pebble',Warehouse:'Houston',Inventory:'9',Status:'In Stock','Wholesale Price':'',MSRP:'649.99','Image URL':'https://x/e.jpeg',Description:'',ETA:''}
];

console.log('\nShape 1: {categories:[{name,items}]} (the new Code.gs contract)');
let g = A.normalizeFeed({categories:[
  {name:'closeout specials', items:closeouts},
  {name:'sectionals', items:sectionals},
  {name:'new arrivals', items:arrivals}]});
ok('three rails', g.length===3, JSON.stringify(g.map(x=>x.name)));
ok('order is Closeout, Sectionals, New Arrivals',
   g.map(x=>x.name).join('|')==='Closeout Specials|Sectionals|New Arrivals', g.map(x=>x.name).join('|'));
ok('counts 3/3/2', g[0].items.length===3&&g[1].items.length===3&&g[2].items.length===2);

console.log('\nShape 2: {tabs:{name:[rows]}} (keyed object)');
let g2 = A.normalizeFeed({tabs:{'sectionals':sectionals,'closeout specials':closeouts,'new arrivals':arrivals}});
ok('three rails', g2.length===3, JSON.stringify(g2.map(x=>x.name)));
ok('sorted to configured order', g2[0].name==='Closeout Specials');

console.log('\nShape 3: bare flat array (no tab names at all)');
let g3 = A.normalizeFeed(sectionals.concat(arrivals, closeouts));
ok('splits by Category column into 3 rails', g3.length===3, JSON.stringify(g3.map(x=>x.name)));
ok('"Stationary Sectionals" aliased to "Sectionals"',
   g3.some(x=>x.name==='Sectionals'), JSON.stringify(g3.map(x=>x.name)));

console.log('\nShape 4: {data:[rows]}');
let g4 = A.normalizeFeed({data: closeouts});
ok('one rail, 3 items', g4.length===1 && g4[0].items.length===3);

console.log('\nHeader rows and blanks are dropped');
let g5 = A.normalizeFeed({categories:[{name:'sectionals', items:[
  {SKU:'SKU','Product Name':'Product Name',Category:'Category'},
  {SKU:'',  'Product Name':'', Category:''},
].concat(sectionals)}]});
ok('3 real rows survive', g5[0].items.length===3, String(g5[0].items.length));

console.log('\nField parsing');
const poland = g[1].items.find(i=>i.sku==='POLAND BLACK');
const aria   = g[1].items.find(i=>i.sku==='ARIA BLACK');
ok('MSRP maps to dealer price', g[1].items[0].price===369.99, String(g[1].items[0].price));
ok('"$499.99" string parses', aria.price===499.99, String(aria.price));
ok('blank MSRP -> null (no fabricated price)', poland.price===null, String(poland.price));
ok('Inventory parses to int', poland.inventory===0, String(poland.inventory));

console.log('\nStock model');
ok('Sold Out + inventory 0 -> unavailable, ETA shown',
   A.stock(poland).avail===false && A.stock(poland).label.includes('9/7'), A.stock(poland).label);
ok('Last One -> last', A.stock(g[0].items[0]).k==='last', A.stock(g[0].items[0]).k);
ok('inventory 2 -> low', A.stock(g[2].items[1]).k==='low', A.stock(g[2].items[1]).label);
ok('inventory 4 -> ok', A.stock(g[0].items[1]).k==='ok', A.stock(g[0].items[1]).label);

console.log('\nDuplicate SKUs must stay distinct line items');
const dup = g[0].items.filter(i=>i.sku==='310-04');
ok('both 310-04 rows kept', dup.length===2);
ok('their uids differ (cart keys apart)', dup[0].uid!==dup[1].uid, dup[0].uid+' vs '+dup[1].uid);

console.log('\nImage handling');
ok('http upgraded to https and width replaced',
   A.thumb('http://www.happyhomesindustries.com/uploads/a.jpeg?width=2560',480)
   ==='https://www.happyhomesindustries.com/uploads/a.jpeg?width=480',
   A.thumb('http://www.happyhomesindustries.com/uploads/a.jpeg?width=2560',480));
ok('plain url gets width appended once',
   A.thumb('https://x/c.jpeg',480)==='https://x/c.jpeg?width=480');
ok('empty url stays empty', A.thumb('',480)==='');

console.log('\nMoney formatting');
ok('thousands separator', A.money(3599.99)==='$3,599.99', A.money(3599.99));
ok('null price -> null', A.money(null)===null);

console.log('\n'+pass+' passed, '+fail+' failed');
process.exit(fail?1:0);
