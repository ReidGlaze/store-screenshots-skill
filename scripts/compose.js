#!/usr/bin/env node
// Compose store screenshots: background + caption + framed phone (+ optional callout),
// and the Google Play feature graphic. Draws everything as an HTML/CSS page and
// screenshots it with Playwright (headless Chrome).
//
//   node compose.js <config.json> [name-filter]
//
// See templates/config.example.json and SKILL.md for the config format.
// Phone frames: if a set has "framedDir" (transparent PNGs rendered by Rotato),
// those are used. Otherwise a plain frame is drawn in CSS around the raw capture.
const fs = require('fs');
const path = require('path');

function loadPlaywright() {
  const tries = [
    'playwright',
    path.join(process.env.HOME, '.claude/skills/playwright-skill/node_modules/playwright'),
    path.join(process.env.HOME, '.claude/skills/playwright/node_modules/playwright'),
  ];
  try {
    const globalRoot = require('child_process').execSync('npm root -g', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
    if (globalRoot) tries.push(path.join(globalRoot, 'playwright'));
  } catch (e) { /* npm not on PATH */ }
  for (const t of tries) { try { return require(t); } catch (e) { /* next */ } }
  console.error('Playwright not found. Run: npm install -g playwright');
  process.exit(1);
}

const dataUrl = (file) => {
  const ext = path.extname(file).slice(1).toLowerCase();
  const mime = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'webp' ? 'image/webp' : 'image/png';
  return `data:${mime};base64,${fs.readFileSync(file).toString('base64')}`;
};

(async () => {
  const cfgPath = process.argv[2];
  if (!cfgPath) { console.error('usage: node compose.js <config.json> [name-filter]'); process.exit(1); }
  const only = process.argv[3];
  const base = path.dirname(path.resolve(cfgPath));
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const rel = (p) => (path.isAbsolute(p) ? p : path.join(base, p));
  const look = {
    accent: cfg.accent || '#00838F',
    text: cfg.text || '#141414',
    background: cfg.background || 'linear-gradient(160deg,#f7f7f7 0%,#ececec 55%,#e2e2e2 100%)',
    font: cfg.font || 'Montserrat',
  };
  const outRoot = rel(cfg.out || 'store-screenshots');
  const template = 'file://' + path.join(__dirname, '..', 'templates', 'page.html');

  const { chromium } = loadPlaywright();
  let browser;
  try { browser = await chromium.launch({ channel: 'chrome' }); } catch (e) { browser = await chromium.launch(); }

  async function draw(width, height, payload, outFile) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    await page.goto(template);
    // Web font: Google Fonts when online; falls back to system fonts when not.
    if (cfg.fontUrl !== false) {
      const url = cfg.fontUrl || `https://fonts.googleapis.com/css2?family=${encodeURIComponent(look.font)}:wght@400;500;700;800&display=swap`;
      await page.addStyleTag({ url }).catch(() => console.warn(`  (could not load ${look.font}; using a system font)`));
    }
    await page.evaluate((p) => render(p), payload);
    await page.waitForTimeout(300);
    fs.mkdirSync(path.dirname(outFile), { recursive: true });
    await page.screenshot({ path: outFile, omitBackground: false });
    await page.close();
    console.log(`${path.relative(base, outFile)}  ${width}x${height}`);
  }

  const sourceFiles = (set, source) => {
    const raw = path.join(rel(set.rawDir), source + '.png');
    if (!fs.existsSync(raw)) throw new Error(`missing raw capture: ${raw}`);
    let framed = null;
    if (set.framedDir) {
      for (const n of [`${source}.png`, `phone-${source}.png`]) {
        const f = path.join(rel(set.framedDir), n);
        if (fs.existsSync(f)) { framed = f; break; }
      }
      if (!framed) console.warn(`  (no framed render for "${source}" in ${set.framedDir}; drawing a plain frame)`);
    }
    return { raw, framed };
  };

  for (const set of cfg.sets || []) {
    for (const shot of cfg.shots || []) {
      if (only && !shot.name.includes(only)) continue;
      const { raw, framed } = sourceFiles(set, shot.source);
      await draw(set.width, set.height, {
        mode: 'shot', ...look,
        caption: shot.caption,
        raw: dataUrl(raw), framed: framed ? dataUrl(framed) : null,
        captionHeight: set.captionHeight || 0.215,
        fontSize: set.fontSize || 0.08,
        callout: (set.callouts || {})[shot.name] || null,
        screenInset: set.screenInset || null,
      }, path.join(outRoot, set.dir, shot.name + '.png'));
    }
  }

  if (cfg.feature && !only) {
    const f = cfg.feature;
    const set = (cfg.sets || []).find((s) => s.dir === f.set) || cfg.sets[0];
    const { raw, framed } = sourceFiles(set, f.source);
    await draw(1024, 500, {
      mode: 'feature', ...look,
      caption: f.headline, appName: f.appName,
      icon: f.icon ? dataUrl(rel(f.icon)) : null,
      raw: dataUrl(raw), framed: framed ? dataUrl(framed) : null,
      screenInset: set.screenInset || null,
    }, path.join(outRoot, f.out || 'feature-graphic-1024x500.png'));
  }
  await browser.close();
})().catch((e) => { console.error(e.message || e); process.exit(1); });
