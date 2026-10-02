/* ============================================================
   app.js — wires the data layer, the viewer and the UI together
   ============================================================ */

import { loadAsset, SOURCES, MODULE_KEYS } from './data.js';
import { Viewer } from './viewer.js';
import { UI } from './ui.js';

class App {
  constructor() {
    this.viewer = new Viewer(document.getElementById('view'));
    this.ui = new UI(this);
    this.data = null;
    this.sourceKey = 'local';

    this.viewer.onSelect = (name) => this._onSelect(name);
    this.viewer.onHover = (name) => this.ui.setHover(name);
    this.viewer.onStatus = (s) => this.ui.setStatus(s);

    this._bindKeys();
    this._bindSourcePicker();
    this._startFpsLoop();
  }

  /* ============================================================
     Boot
     ============================================================ */
  async boot(sourceKey = 'local') {
    this.sourceKey = sourceKey;
    const loading = document.getElementById('loading');
    const bar = document.getElementById('loading-bar');
    const text = document.getElementById('loading-text');
    const errBox = document.getElementById('error-box');

    loading.classList.remove('done');
    errBox.hidden = true;

    const setProgress = (label, p) => {
      text.textContent = `${label}…`;
      bar.style.width = `${Math.round(p * 100)}%`;
    };

    try {
      setProgress('Loading manifest', 0.02);
      const data = await loadAsset(sourceKey, setProgress);
      this.data = data;
      this.viewer.data = data;

      this.ui.populate(data);
      this.ui.setStatus('manifest loaded');

      setProgress('Loading model', 0.45);
      const src = SOURCES[sourceKey];
      const info = await this.viewer.load(src.glb, (p) => {
        setProgress('Loading model', 0.45 + p * 0.5);
      });

      setProgress('Ready', 1);
      this.ui.setStatus(`loaded ${info.nodes} parts · ${info.clips} clips`);

      /* expose for headless verification */
      window.__ALTIMA__ = {
        app: this,
        data,
        viewer: this.viewer,
        info,
        ready: true,
      };

      setTimeout(() => loading.classList.add('done'), 260);
      this.ui.setAnimUI(0, this.viewer.animDuration, false);
    } catch (err) {
      console.error(err);
      loading.classList.add('done');
      errBox.hidden = false;
      document.getElementById('error-text').textContent = String(err && err.message ? err.message : err);
      this.ui.setStatus('load failed');
      window.__ALTIMA__ = { app: this, ready: false, error: String(err) };
    }
  }

  async changeSource(key) {
    if (key === this.sourceKey) return;
    // tear the old model out of the scene before loading the new one
    if (this.viewer.root) {
      this.viewer.scene.remove(this.viewer.root);
      this.viewer.root = null;
      this.viewer.parts.clear();
      this.viewer.traceMeshes.length = 0;
      this.viewer.traceByName.clear();
      this.viewer.stepEmpties.length = 0;
      this.viewer.trace = new (this.viewer.trace.constructor)();
    }
    await this.boot(key);
  }

  _bindSourcePicker() {
    const sel = document.getElementById('source-select');
    sel.innerHTML = Object.entries(SOURCES)
      .map(([k, v]) => `<option value="${k}">${v.label}</option>`)
      .join('');
    sel.value = this.sourceKey;
  }

  /* ============================================================
     Selection
     ============================================================ */
  _onSelect(name) {
    this.ui.showInfo(name);
    this.ui.refreshParts();
    if (name) {
      const mesh = this.viewer.parts.get(name);
      if (mesh && mesh.userData.isTrace) this.viewer.trace.pin(mesh);
      this.ui.setStatus(`selected ${name}`);
    } else {
      this.ui.setStatus('selection cleared');
    }
  }

  selectPart(name, { focus = false } = {}) {
    this.viewer.select(name);
    if (focus) this.viewer.focusOn(name);
  }

  ejectSelected() {
    const n = this.viewer.selected;
    if (!n) return;
    if (this.viewer.eject(n)) this.ui.setStatus(`pulled off ${n}`);
  }

  hideSelected() {
    const n = this.viewer.selected;
    if (!n) return;
    this.viewer.setVisible(n, false);
    this.ui.refreshParts();
    this.ui.setStatus(`hid ${n}`);
  }

  isolateSelected() {
    const n = this.viewer.selected;
    if (!n) return;
    this.viewer.isolate([n]);
    this.ui.setStatus(`isolated ${n}`);
  }

  runTraceOnSelected() {
    const n = this.viewer.selected;
    if (!n) return;
    const mesh = this.viewer.traceByName.get(n);
    if (!mesh) { this.ui.setStatus(`${n} has no trace run`); return; }
    this.viewer.trace.run(mesh);
    this.ui.setStatus(`tracing ${n}`);
  }

  isolateHarness(name) {
    this.viewer.isolateHarness(name);
    this.ui.setStatus(`isolated harness ${name}`);
  }

  isolateModule(key) {
    this.viewer.isolateModule(key);
    this.ui.refreshModules();
    this.ui.setStatus(`isolated module ${key}`);
  }

  /* ============================================================
     Sequence / animation
     ============================================================ */
  setExplode(amount) {
    this.viewer.setExplode(amount, this.viewer.stepLimit);
    this.ui.setExplodeUI(amount, this.viewer.stepLimit);
    this.ui.setStatus(`explode ${Math.round(amount * 100)}%`);
  }

  setStep(step) {
    this.viewer.stepLimit = step;
    const amount = step === 0 ? 0 : Math.max(this.viewer.explodeAmount, 0.35);
    this.viewer.setExplode(amount, step);
    this.ui.setExplodeUI(amount, step);
    const s = this.data.steps.find((x) => x.step === step);
    this.ui.setStatus(step === 0 ? 'assembled' : `step ${step}: ${s ? s.title : ''}`);
  }

  resetView() {
    this.viewer.setExplode(0, 0);
    this.viewer.clearEjections();
    this.viewer.showAll();
    this.viewer.trace.clearAll();
    this.viewer.select(null);
    this.viewer.setAnimTime(0);
    this.viewer.pause();
    this.ui.setExplodeUI(0, 0);
    this.ui.setAnimUI(0, this.viewer.animDuration, false);
    this.ui.refreshParts();
    this.ui.refreshHarnesses();
    this.ui.refreshModules();
    this.ui.setStatus('reset');
  }

  togglePlay() {
    this.viewer.togglePlay();
    this.ui.setAnimUI(this.viewer.animTime, this.viewer.animDuration, this.viewer.playing);
  }

  scrub(fraction) {
    this.viewer.pause();
    this.viewer.setAnimTime(fraction * this.viewer.animDuration);
    this.ui.setAnimUI(this.viewer.animTime, this.viewer.animDuration, false);
  }

  setStatus(s) { this.ui.setStatus(s); }

  /* ============================================================
     Keyboard
     ============================================================ */
  _bindKeys() {
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      const v = this.viewer;
      switch (e.key.toLowerCase()) {
        case ' ':
          e.preventDefault(); this.togglePlay(); break;
        case 'f': v.fit(); break;
        case 'r': {
          const on = !v.controls.autoRotate;
          v.setSpin(on);
          document.getElementById('btn-spin').classList.toggle('on', on);
          break;
        }
        case 'w': {
          const on = !v.wireframe;
          v.setWireframe(on);
          document.getElementById('btn-wireframe').classList.toggle('on', on);
          break;
        }
        case 'x': {
          const on = !v.xray;
          v.setXray(on);
          document.getElementById('btn-xray').classList.toggle('on', on);
          break;
        }
        case 't': {
          const on = !v.liveTrace;
          v.liveTrace = on;
          document.getElementById('btn-live-trace').classList.toggle('on', on);
          if (!on) v.trace.clearAll();
          break;
        }
        case 'h': this.hideSelected(); break;
        case 'escape':
          v.select(null);
          document.getElementById('help-modal').hidden = true;
          break;
        case '1': this.ui.setTab('parts'); break;
        case '2': this.ui.setTab('harnesses'); break;
        case '3': this.ui.setTab('modules'); break;
      }
    });
  }

  /* ============================================================
     FPS readout
     ============================================================ */
  _startFpsLoop() {
    setInterval(() => {
      this.ui.setFps(this.viewer.fps);
      if (this.viewer.playing) {
        this.ui.setAnimUI(this.viewer.animTime, this.viewer.animDuration, true);
      }
    }, 500);
  }
}

/* ---------- go ---------- */
const app = new App();
window.__APP__ = app;

/* Prefer the local repo copy; fall back to the published GitHub copy
   automatically when the page is served without the assets next to it
   (e.g. GitHub Pages, where the LFS binaries live on media.githubusercontent). */
(async () => {
  const params = new URLSearchParams(location.search);
  const forced = params.get('source');
  if (forced && SOURCES[forced]) { await app.boot(forced); return; }

  const isPages = /github\.io$/i.test(location.hostname);
  await app.boot(isPages ? 'github' : 'local');
})();
