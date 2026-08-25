/**
 * Pulls the pure data-layer functions out of index.html so they can be
 * unit-tested in node without a DOM. Writes test/core.generated.js.
 */
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/g).pop()
                   .replace(/^<script>|<\/script>$/g, '');
const start = script.indexOf('var CONFIG = {');
const end = script.lastIndexOf('/* ---', script.indexOf('* State'));
if (start < 0 || end < 0) throw new Error('Could not locate the core block in index.html');
fs.writeFileSync(path.join(__dirname, 'core.generated.js'),
  script.slice(start, end) +
  '\nmodule.exports={normalizeFeed,normalizeRow,stock,thumb,money,toNumber,toInt,titleCase,CONFIG};\n');
console.log('core.generated.js written');
