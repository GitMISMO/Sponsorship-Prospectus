/* The browser's Back button on every prospectus (CN-033, November 25, 2026).

     node tools/back-check.js <sponsorship repo folder>

   Runs with the Playwright the Sponsorship Portal's checks install (sponsorship/tests), in
   GitHub after every change (.github/workflows/checks.yml). The pages are served the way
   resources.mismo.org serves them, on practice data, and /assets/back.js is the live shared
   copy, as Summit HQ's check 31 does. Nothing reaches a real address.

   For each page: two menu jumps and Back returns to the first, Forward goes again; a
   Contents row is a Back step; the page a reader stops scrolling on is where Back returns
   to; the address never changes; no page errors. (The prospectus has no right-hand panels
   or drawers, so there is nothing for Back to close first.) */
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');

const PROS = path.resolve(__dirname, '..');
const PORTAL = path.resolve(process.argv[2] || path.join(PROS, '..', 'sponsorship'));
const { chromium } = require(require.resolve('playwright', { paths: [path.join(PORTAL, 'tests'), PROS] }));

function live(url) {
  return new Promise((ok, bad) => https.get(url, r => {
    if (r.statusCode !== 200) return bad(new Error(url + ' answered ' + r.statusCode));
    let b = ''; r.setEncoding('utf8'); r.on('data', d => b += d); r.on('end', () => ok(b));
  }).on('error', bad));
}

const ROOTS = { '/Sponsorship-Prospectus/': PROS + '/', '/sponsorship/': PORTAL + '/' };
let BACK = '';
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/assets/back.js') { res.writeHead(200, { 'Content-Type': 'text/javascript' }); return res.end(BACK); }
  if (p.endsWith('/')) p += 'index.html';
  let f = null;
  for (const k in ROOTS) if (p.startsWith(k)) f = ROOTS[k] + p.slice(k.length);
  if (!f || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  const t = { '.js': 'text/javascript', '.json': 'application/json', '.html': 'text/html' }[path.extname(f)] || 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': t + '; charset=utf-8' });
  fs.createReadStream(f).pipe(res);
});

const results = [];
async function check(name, fn) {
  try { await fn(); results.push({ ok: true, name }); console.log('  ✓ ' + name); }
  catch (e) { results.push({ ok: false, name, why: e.message || String(e) }); console.log('  ✗ ' + name + '\n      ' + (e.message || e)); }
}
function expect(c, msg) { if (!c) throw new Error(msg); }

(async () => {
  BACK = await live('https://resources.mismo.org/assets/back.js');
  await new Promise(r => server.listen(0, r));
  const ORIGIN = 'http://localhost:' + server.address().port;
  const browser = await chromium.launch();
  const PAGES = [['2027 Series and Winter', '/Sponsorship-Prospectus/'], ['Spring 2027', '/Sponsorship-Prospectus/spring-2027/'],
    ['Fall 2027', '/Sponsorship-Prospectus/fall-2027/'], ['Spring & Fall 2027', '/Sponsorship-Prospectus/spring-fall-2027/']];
  console.log('\nBack button (CN-033)');
  for (const [name, url] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    await ctx.route(u => !u.href.startsWith(ORIGIN), r => r.abort());
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e).split('\n')[0]));
    await page.goto(ORIGIN + url + '?practice', { waitUntil: 'load' });
    await page.waitForTimeout(2000);
    const lit = () => page.evaluate(() => { const b = document.querySelector('nav button[data-hq][aria-current]'); return b ? b.dataset.hq : ''; });
    const at = id => page.evaluate(id => Math.abs(document.getElementById(id).getBoundingClientRect().top) < 160, id);
    const nav = async id => { await page.click('nav button[data-hq="' + id + '"]'); await page.waitForTimeout(2400); };
    const back = async () => { await page.evaluate(() => history.back()); await page.waitForTimeout(2400); };
    const fwd = async () => { await page.evaluate(() => history.forward()); await page.waitForTimeout(2400); };
    const start = page.url();

    await check(name + ': Back returns to the last page from the menu, and Forward goes again', async () => {
      expect(await page.evaluate(() => !!window.MismoBack), 'back.js did not load');
      await nav('about'); await nav('reserve');
      expect(await lit() === 'reserve' && await at('reserve'), 'the menu did not go to Reserve');
      await back();
      expect(await lit() === 'about' && await at('about'), 'Back went to "' + await lit() + '", not About the Summits');
      await fwd();
      expect(await lit() === 'reserve' && await at('reserve'), 'Forward went to "' + await lit() + '", not Reserve');
    });
    await check(name + ': a Contents row is a Back step', async () => {
      await nav('toc');
      await page.click('a.toc-row[href="#why"]'); await page.waitForTimeout(2400);
      expect(await lit() === 'why', 'the Contents row did not go to Why Sponsor');
      await back();
      expect(await lit() === 'toc' && await at('toc'), 'Back went to "' + await lit() + '", not Contents');
    });
    await check(name + ': Back returns to the page the reader scrolled to', async () => {
      await page.waitForTimeout(2600);   // long enough that the scroll isn't part of the last click
      await page.mouse.move(700, 500);
      const y = await page.evaluate(() => { const e = document.getElementById('availability'); return e.getBoundingClientRect().top + window.pageYOffset - 80; });
      await page.mouse.wheel(0, y - await page.evaluate(() => window.pageYOffset));
      await page.waitForTimeout(1200);
      const stopped = await lit();
      await nav('contract');
      await back();
      expect(await lit() === stopped, 'Back went to "' + await lit() + '", not "' + stopped + '" where the scrolling stopped');
    });
    await check(name + ': the address never changes and there are no page errors', async () => {
      expect(page.url() === start, 'the address changed to ' + page.url());
      expect(!errors.length, 'page errors: ' + errors.join(' | '));
    });
    await ctx.close();
  }
  await browser.close();
  server.close();
  const bad = results.filter(r => !r.ok);
  console.log('\n' + (bad.length ? bad.length + ' of ' + results.length + ' checks FAILED' : 'All ' + results.length + ' checks passed'));
  if (process.env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, '### Back button checks\n\n' + results.map(r =>
      (r.ok ? '- ✅ ' : '- ❌ ') + r.name + (r.ok ? '' : ' — ' + r.why)).join('\n') + '\n');
  }
  process.exit(bad.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
