/* ============================================================
   Headless verification of the ALTIMA2000 web frontend.

   Usage:
     cd web && python3 -m http.server 8099 &
     npm i puppeteer-core
     CHROME=/path/to/chrome node verify_frontend.js

   Env:
     URL     page to test        (default http://127.0.0.1:8099/index.html)
     CHROME  chromium executable (default: the Playwright headless shell)
     OUT     screenshot dir      (default ./verify_shots)
   ============================================================ */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const EXE = process.env.CHROME
  || '/root/.cache/ms-playwright/chromium_headless_shell-1181/chrome-linux/headless_shell';
const URL = process.env.URL || 'http://127.0.0.1:8099/index.html';
const OUT = process.env.OUT || path.join(__dirname, 'verify_shots');

const results = [];
function check(name, ok, detail) {
  results.push({ name, ok: !!ok, detail: detail === undefined ? '' : String(detail) });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail !== undefined ? '  :: ' + detail : ''}`);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: EXE,
    headless: true,
    protocolTimeout: 180000,
    args: [
      '--no-sandbox', '--disable-setuid-sandbox',
      '--enable-unsafe-swiftshader',
      '--use-gl=angle', '--use-angle=swiftshader',
      '--window-size=1600,1000',
      '--disable-dev-shm-usage',
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 1 });

  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => pageErrors.push(String(e)));

  console.log('--- loading', URL);
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });

  /* wait for the app to report ready */
  let ready = false;
  try {
    await page.waitForFunction('window.__ALTIMA__ && window.__ALTIMA__.ready === true', { timeout: 120000 });
    ready = true;
  } catch (e) {
    const st = await page.evaluate(() => (window.__ALTIMA__ ? JSON.stringify(window.__ALTIMA__.error || 'not ready') : 'no __ALTIMA__'));
    check('app boots and reports ready', false, st);
  }
  if (ready) check('app boots and reports ready', true);

  /* ---------- WebGL context ---------- */
  const gl = await page.evaluate(() => {
    const c = document.getElementById('view');
    const ctx = c.getContext('webgl2') || c.getContext('webgl');
    if (!ctx) return null;
    const dbg = ctx.getExtension('WEBGL_debug_renderer_info');
    return { renderer: dbg ? ctx.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'unknown' };
  });
  check('WebGL context created', !!gl, gl ? gl.renderer : 'none');

  /* ---------- model + manifest ---------- */
  const info = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    if (!A || !A.ready) return null;
    return {
      nodes: A.info.nodes,
      clips: A.info.clips,
      traceMeshes: A.info.traceMeshes,
      manifestParts: A.data.partCount,
      manifestPartsArr: A.data.parts.length,
      harnesses: A.data.harnessList.length,
      modules: A.data.moduleList.length,
      steps: A.data.stepCount,
      wires: A.data.wiring.wire_segment_count,
      hoses: A.data.hoses.hose_segment_count,
      straps: A.data.hoses.tie_strap_count,
      sceneChildren: A.viewer.scene.children.length,
      rootChildren: A.viewer.root ? A.viewer.root.children.length : 0,
      animDuration: A.viewer.animDuration,
      stepEmpties: A.viewer.stepEmpties.length,
      noGeometry: A.viewer.noGeometry ? A.viewer.noGeometry.size : -1,
      noGeometryNames: A.viewer.noGeometry ? [...A.viewer.noGeometry] : [],
    };
  });
  console.log('info:', JSON.stringify(info, null, 1));

  check('model loaded (parts indexed)', info && info.nodes > 2000, info && info.nodes);
  check('part count matches manifest (minus non-mesh parts)',
        info && info.nodes === info.manifestParts - info.noGeometry,
        info ? `${info.nodes} meshes + ${info.noGeometry} non-mesh = ${info.manifestParts}` : '');
  check('27 animation clips present', info && info.clips === 27, info && info.clips);
  check('trace meshes registered (wires+hoses+straps)',
        info && info.traceMeshes === (info.wires + info.hoses + info.straps),
        info ? `${info.traceMeshes} vs ${info.wires}+${info.hoses}+${info.straps}` : '');
  check('31 harnesses', info && info.harnesses === 31, info && info.harnesses);
  check('7 modules', info && info.modules === 7, info && info.modules);
  check('27 sequence steps', info && info.steps === 27, info && info.steps);
  check('27 step empties in scene', info && info.stepEmpties === 27, info && info.stepEmpties);

  /* ---------- render actually produces pixels ---------- */
  await new Promise((r) => setTimeout(r, 1500));
  const shot1 = `${OUT}/01_assembled.png`;
  await page.screenshot({ path: shot1 });
  const px = await page.evaluate(() => {
    const c = document.getElementById('view');
    const gl = c.getContext('webgl2') || c.getContext('webgl');
    const w = c.width, h = c.height;
    const buf = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    let nonBg = 0, sum = 0;
    for (let i = 0; i < buf.length; i += 4) {
      const v = buf[i] + buf[i + 1] + buf[i + 2];
      sum += v;
      if (v > 40) nonBg++;
    }
    return { w, h, nonBg, total: w * h, avg: sum / (w * h * 3) };
  });
  check('viewport renders non-background pixels', px.nonBg > px.total * 0.01,
        `${px.nonBg}/${px.total} px, avg ${px.avg.toFixed(1)}`);

  /* ---------- picking returns real part names ---------- */
  const pick = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    const out = [];
    // sample a grid of screen points and collect distinct hits
    for (let x = 0.25; x <= 0.75; x += 0.1) {
      for (let y = 0.3; y <= 0.7; y += 0.1) {
        v._pointer.set(x * 2 - 1, -(y * 2 - 1));
        const hit = v.pick();
        if (hit) out.push(hit.name);
      }
    }
    const uniq = [...new Set(out)];
    const inManifest = uniq.filter((n) => A.data.partsByName.has(n));
    return { hits: out.length, uniq: uniq.length, inManifest: inManifest.length, sample: uniq.slice(0, 6) };
  });
  check('raycast picking returns parts', pick.hits > 0, `${pick.hits} hits, ${pick.uniq} unique`);
  check('picked names resolve in the manifest', pick.uniq > 0 && pick.inManifest === pick.uniq,
        `${pick.inManifest}/${pick.uniq} :: ${pick.sample.join(', ')}`);

  /* ---------- selection drives the info card ---------- */
  const sel = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const name = A.data.parts[500].name;
    A.app.selectPart(name);
    const card = document.getElementById('info-card');
    return {
      name,
      hidden: card.hidden,
      shown: document.getElementById('info-name').textContent,
      group: document.getElementById('info-group').textContent,
      collection: document.getElementById('info-collection').textContent,
      module: document.getElementById('info-module').textContent,
      step: document.getElementById('info-step').textContent,
    };
  });
  check('selecting a part fills the info card',
        !sel.hidden && sel.shown === sel.name,
        `${sel.shown} | ${sel.group} | ${sel.collection} | ${sel.module} | ${sel.step}`);

  /* ---------- harness toggle ---------- */
  const harn = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    const h = A.data.harnessList[0];
    const names = h.wires.map((w) => w.name);
    const before = names.filter((n) => v.parts.get(n) && v.parts.get(n).visible).length;
    v.setHarnessVisible(h.name, false);
    const afterOff = names.filter((n) => v.parts.get(n) && v.parts.get(n).visible).length;
    v.setHarnessVisible(h.name, true);
    const afterOn = names.filter((n) => v.parts.get(n) && v.parts.get(n).visible).length;
    return { harness: h.name, count: names.length, before, afterOff, afterOn };
  });
  check('per-harness visibility toggle works',
        harn.before > 0 && harn.afterOff === 0 && harn.afterOn === harn.before,
        `${harn.harness}: ${harn.before} -> ${harn.afterOff} -> ${harn.afterOn}`);

  /* ---------- isolate a harness ---------- */
  const iso = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    const h = A.data.harnessList[1];
    v.isolateHarness(h.name);
    const vis = [...v.parts.values()].filter((m) => m.visible).length;
    const expected = h.wires.length;
    v.clearIsolate();
    const visAfter = [...v.parts.values()].filter((m) => m.visible).length;
    return { harness: h.name, vis, expected, visAfter };
  });
  check('harness isolate shows only that harness',
        iso.vis === iso.expected && iso.visAfter > iso.expected,
        `${iso.harness}: ${iso.vis} visible (expected ${iso.expected}), restored ${iso.visAfter}`);

  /* ---------- trace shader ---------- */
  const trace = await page.evaluate(async () => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    const mesh = v.traceMeshes[0];
    const mat = mesh.userData.traceMaterial;
    const hasAttr = !!mesh.geometry.getAttribute('aTraceT');
    const attr = mesh.geometry.getAttribute('aTraceT');
    let min = 1, max = 0;
    if (attr) for (let i = 0; i < attr.count; i++) { const t = attr.getX(i); if (t < min) min = t; if (t > max) max = t; }
    v.trace.run(mesh);
    const p0 = mat.uniforms.uProgress.value;
    // Drive the controller directly: the software renderer in this headless
    // environment runs at a few fps, so wall-clock waits are unreliable.
    // Stepping update() proves the sweep advances and the glow ramps.
    for (let i = 0; i < 30; i++) v.trace.update(0.05);
    const p1 = mat.uniforms.uProgress.value;
    const g1 = mat.uniforms.uGlow.value;
    for (let i = 0; i < 30; i++) v.trace.update(0.05);
    const p2 = mat.uniforms.uProgress.value;
    return { name: mesh.name, hasAttr, min, max, p0, p1, p2, g1,
             uniforms: Object.keys(mat.uniforms) };
  });
  check('trace attribute baked per wire', trace.hasAttr && trace.max > 0.9 && trace.min < 0.1,
        `${trace.name}: t range ${trace.min.toFixed(3)}..${trace.max.toFixed(3)}`);
  check('trace progresses over time (end-to-end sweep)',
        trace.p1 > trace.p0 && trace.p2 > trace.p1,
        `progress ${trace.p0.toFixed(3)} -> ${trace.p1.toFixed(3)} -> ${trace.p2.toFixed(3)}`);
  check('trace glow ramps up', trace.g1 > 0.1, `glow ${trace.g1.toFixed(3)}`);

  /* ---------- live hover trace ---------- */
  const hover = await page.evaluate(async () => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    v.trace.clearAll();

    // Find a screen point that actually lands on a wire: scan a grid and
    // keep the first hit, then park the pointer there and let the render
    // loop's own hover logic (not a manual call) do the tracing.
    let found = null;
    outer:
    for (let x = 0.15; x <= 0.85; x += 0.1) {
      for (let y = 0.15; y <= 0.85; y += 0.1) {
        v._pointer.set(x * 2 - 1, -(y * 2 - 1));
        const hit = v.pickTrace();
        if (hit) { found = { x, y, name: hit.name }; break outer; }
      }
    }
    if (!found) return { lit: 0, liveTrace: v.liveTrace, hovered: null, found: null };

    v._pointer.set(found.x * 2 - 1, -(found.y * 2 - 1));
    v._pointerPx = { x: found.x * 100, y: found.y * 100 };
    v._hoverThrottle = 1;

    // let the loop run its own hover pass
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 50));
      if (v._hovered) break;
    }
    for (let i = 0; i < 20; i++) v.trace.update(0.05);
    const lit = [...v.trace.entries.values()].filter((e) => e.glow > 0.05).length;
    return { lit, liveTrace: v.liveTrace, hovered: v._hovered ? v._hovered.name : null, found };
  });
  check('live hover trace lights a wire', hover.lit > 0,
        `${hover.lit} lit, hovered=${hover.hovered}, liveTrace=${hover.liveTrace}`);

  /* ---------- explode ---------- */
  const exp = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    const se = v.stepEmpties[0];
    const base = se.base.clone();
    A.app.setStep(27);            // include every step
    A.app.setExplode(1.0);
    const moved = se.obj.position.distanceTo(base);
    A.app.setExplode(0);
    const back = se.obj.position.distanceTo(base);
    return { step: se.name, moved, back };
  });
  check('explode moves step groups and resets',
        exp.moved > 0.05 && exp.back < 1e-6,
        `${exp.step}: moved ${exp.moved.toFixed(3)}m, reset ${exp.back.toFixed(6)}`);

  /* ---------- step control ---------- */
  const stepCtl = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    A.app.setStep(5);
    const s1 = v.stepEmpties[0].obj.position.distanceTo(v.stepEmpties[0].base);
    const s6 = v.stepEmpties[6].obj.position.distanceTo(v.stepEmpties[6].base);
    A.app.setStep(0);
    return { s1, s6 };
  });
  check('step control explodes only up to the chosen step',
        stepCtl.s1 > 0.01 && stepCtl.s6 < 1e-6,
        `step1 moved ${stepCtl.s1.toFixed(3)}, step7 moved ${stepCtl.s6.toFixed(6)}`);

  /* ---------- eject a single part ---------- */
  const ej = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    const name = A.data.parts[800].name;
    const mesh = v.parts.get(name);
    const before = mesh.position.clone();
    A.app.selectPart(name);
    A.app.ejectSelected();
    const after = mesh.position.clone();
    const d = after.distanceTo(before);
    v.uneject(name);
    const restored = mesh.position.distanceTo(before);
    return { name, d, restored };
  });
  check('pull-this-part-off ejects and restores',
        ej.d > 0.1 && ej.restored < 1e-6,
        `${ej.name}: moved ${ej.d.toFixed(3)}m, restored ${ej.restored.toFixed(6)}`);

  /* ---------- module isolate ---------- */
  const mod = await page.evaluate(() => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    const m = A.data.moduleList[0];
    v.isolateModule(m.key);
    const vis = [...v.parts.values()].filter((x) => x.visible).length;
    v.clearIsolate();
    return { key: m.key, vis, expected: m.partCount };
  });
  check('module isolate shows only that module',
        mod.vis === mod.expected,
        `${mod.key}: ${mod.vis} visible (expected ${mod.expected})`);

  /* ---------- animation playback ---------- */
  const anim = await page.evaluate(async () => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    v.showAll();
    v.setAnimTime(0);
    const t0 = v.animTime;
    v.play();
    // advance the loop deterministically rather than waiting on wall clock
    for (let i = 0; i < 40; i++) { await new Promise((r) => setTimeout(r, 50)); if (v.animTime > 0.05) break; }
    const t1 = v.animTime;
    v.pause();
    const playing = v.playing;
    // scrub
    A.app.scrub(0.5);
    const t2 = v.animTime;
    const dur = v.animDuration;
    return { t0, t1, t2, dur, playing };
  });
  check('animation plays (time advances)', anim.t1 > anim.t0, `${anim.t0.toFixed(3)} -> ${anim.t1.toFixed(3)}`);
  check('animation pauses', anim.playing === false, `playing=${anim.playing}`);
  check('animation scrubs to 50%', Math.abs(anim.t2 - anim.dur * 0.5) < 0.02,
        `t=${anim.t2.toFixed(3)} of ${anim.dur.toFixed(3)}`);

  /* ---------- animation actually moves geometry ---------- */
  const animMove = await page.evaluate(async () => {
    const A = window.__ALTIMA__;
    const v = A.viewer;
    A.app.resetView();
    v.setAnimTime(0);
    const se = v.stepEmpties[0];
    const p0 = se.obj.position.clone();
    v.setAnimTime(v.animDuration);
    const p1 = se.obj.position.clone();
    v.setAnimTime(0);
    return { d: p0.distanceTo(p1) };
  });
  check('teardown animation moves the step groups', animMove.d > 0.05, `moved ${animMove.d.toFixed(3)}m`);

  /* ---------- parts list ---------- */
  const list = await page.evaluate(() => {
    const rows = document.querySelectorAll('#part-list-inner .row').length;
    const count = document.getElementById('part-count').textContent;
    return { rows, count };
  });
  check('parts list renders rows', list.rows > 0, `${list.rows} rows, "${list.count}"`);

  /* ---------- search filter ---------- */
  const search = await page.evaluate(async () => {
    const A = window.__ALTIMA__;
    const inp = document.getElementById('part-search');
    inp.value = 'Caliper';
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 200));
    const n = A.app.ui.filtered.length;
    const allMatch = A.app.ui.filtered.every((p) => p.name.toLowerCase().includes('caliper'));
    inp.value = '';
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 200));
    return { n, allMatch, restored: A.app.ui.filtered.length };
  });
  check('search filters the parts list', search.n > 0 && search.allMatch && search.restored > search.n,
        `${search.n} matches, restored ${search.restored}`);

  /* ---------- harness panel rendered ---------- */
  const panel = await page.evaluate(() => ({
    harnessRows: document.querySelectorAll('#harness-list .hrow').length,
    hoseRows: document.querySelectorAll('#hose-list .hrow').length,
    moduleCards: document.querySelectorAll('#module-list .mcard').length,
    legendRows: document.querySelectorAll('#legend-body .lg').length,
  }));
  check('harness panel lists 31 harnesses', panel.harnessRows === 31, panel.harnessRows);
  check('hose panel lists 15 systems', panel.hoseRows === 15, panel.hoseRows);
  check('module panel lists 7 modules', panel.moduleCards === 7, panel.moduleCards);
  check('legend rendered', panel.legendRows > 5, panel.legendRows);

  /* ---------- screenshots ---------- */
  await page.evaluate(() => { window.__ALTIMA__.app.resetView(); });
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: `${OUT}/01_assembled.png` });

  await page.evaluate(() => { window.__ALTIMA__.app.setExplode(1.0); });
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: `${OUT}/02_exploded.png` });

  /* Wiring mode: keep the whole car visible but x-rayed so the harnesses
     read as distinct tubes, then run the progressive trace on one wire.
     (Isolating a single harness is also exercised by the checks above, but
     it hides the car and makes for an unreadable screenshot.) */
  await page.evaluate(() => {
    const A = window.__ALTIMA__;
    A.app.resetView();
    A.app.ui.setTab('harnesses');
    A.viewer.setXray(true);
    const m = A.viewer.traceByName.get(A.data.harnessList[0].wires[0].name);
    if (m) A.viewer.trace.run(m);
  });
  await new Promise((r) => setTimeout(r, 900));
  await page.screenshot({ path: `${OUT}/03_wiring_trace.png` });

  /* Same view, but with one harness isolated — proves the per-harness
     isolate path visually as well. */
  await page.evaluate(() => {
    const A = window.__ALTIMA__;
    A.viewer.setXray(false);
    A.viewer.isolateHarness(A.data.harnessList[0].name);
  });
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: `${OUT}/03b_harness_isolated.png` });
  await page.evaluate(() => { window.__ALTIMA__.viewer.clearIsolate(); });

  await page.evaluate(() => {
    const A = window.__ALTIMA__;
    A.app.resetView();
    A.app.ui.setTab('modules');
    A.viewer.isolateModule('engine');
  });
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: `${OUT}/04_module_engine.png` });

  await page.evaluate(() => {
    const A = window.__ALTIMA__;
    A.app.resetView();
    A.viewer.setAnimTime(A.viewer.animDuration * 0.55);
  });
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: `${OUT}/05_anim_mid.png` });

  await page.evaluate(() => {
    const A = window.__ALTIMA__;
    A.app.resetView();
    A.app.ui.setTab('parts');
    A.app.selectPart(A.data.parts[500].name);
  });
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: `${OUT}/06_parts_selected.png` });

  /* ---------- console errors ---------- */
  const fatal = pageErrors.filter((e) => !/favicon/i.test(e));
  check('no uncaught page errors', fatal.length === 0, fatal.slice(0, 3).join(' | '));
  const cerr = consoleErrors.filter((e) => !/favicon|Failed to load resource.*favicon/i.test(e));
  check('no console errors', cerr.length === 0, cerr.slice(0, 3).join(' | '));

  await browser.close();

  const pass = results.filter((r) => r.ok).length;
  console.log(`\n===== ${pass}/${results.length} checks passed =====`);
  fs.writeFileSync('/tmp/webtest/results.json', JSON.stringify(results, null, 1));
  process.exit(pass === results.length ? 0 : 1);
})().catch((e) => { console.error('HARNESS ERROR', e); process.exit(2); });
