/* ============================================================
   ui.js — panels, lists, legend, info card, bottom bar
   ============================================================ */

import { GROUP_COLORS } from './data.js';

const ROW_H = 26;          // px — must match .row height in app.css
const OVERSCAN = 8;

export class UI {
  constructor(app) {
    this.app = app;
    this.data = null;

    this.$ = (id) => document.getElementById(id);

    /* parts list state */
    this.filtered = [];
    this.query = '';
    this.fGroup = '';
    this.fCollection = '';
    this.fModule = '';
    this.fState = '';
    this._renderQueued = false;

    /* harness / hose switch state */
    this.harnessOn = new Map();
    this.hoseOn = new Map();
    this.moduleOn = new Map();

    this._bind();
  }

  /* ============================================================
     Bind static controls
     ============================================================ */
  _bind() {
    const $ = this.$;

    /* tabs */
    document.querySelectorAll('.tab').forEach((t) => {
      t.addEventListener('click', () => this.setTab(t.dataset.tab));
    });

    /* parts filters */
    $('part-search').addEventListener('input', (e) => {
      this.query = e.target.value.trim().toLowerCase();
      this.refreshParts();
    });
    $('filter-group').addEventListener('change', (e) => { this.fGroup = e.target.value; this.refreshParts(); });
    $('filter-collection').addEventListener('change', (e) => { this.fCollection = e.target.value; this.refreshParts(); });
    $('filter-module').addEventListener('change', (e) => { this.fModule = e.target.value; this.refreshParts(); });
    $('filter-state').addEventListener('change', (e) => { this.fState = e.target.value; this.refreshParts(); });

    $('btn-show-all').addEventListener('click', () => { this.app.viewer.showAll(); this.refreshParts(); this.refreshHarnesses(); this.refreshModules(); });
    $('btn-hide-all').addEventListener('click', () => { this.app.viewer.hideAll(); this.refreshParts(); });

    /* virtual list scroll */
    $('part-list-scroll').addEventListener('scroll', () => this._queueRender());

    /* harness bulk */
    $('btn-harness-all').addEventListener('click', () => this._bulkHarness(true));
    $('btn-harness-none').addEventListener('click', () => this._bulkHarness(false));
    $('btn-hose-all').addEventListener('click', () => this._bulkHose(true));
    $('btn-hose-none').addEventListener('click', () => this._bulkHose(false));
    $('btn-module-all').addEventListener('click', () => this._bulkModule(true));

    /* info card */
    $('info-close').addEventListener('click', () => this.app.viewer.select(null));
    $('btn-eject').addEventListener('click', () => this.app.ejectSelected());
    $('btn-hide').addEventListener('click', () => this.app.hideSelected());
    $('btn-isolate').addEventListener('click', () => this.app.isolateSelected());
    $('btn-trace').addEventListener('click', () => this.app.runTraceOnSelected());

    /* view toggles */
    $('btn-live-trace').addEventListener('click', (e) => {
      const on = !this.app.viewer.liveTrace;
      this.app.viewer.liveTrace = on;
      e.currentTarget.classList.toggle('on', on);
      if (!on) this.app.viewer.trace.clearAll();
    });
    $('btn-wireframe').addEventListener('click', (e) => {
      const on = !this.app.viewer.wireframe;
      this.app.viewer.setWireframe(on);
      e.currentTarget.classList.toggle('on', on);
    });
    $('btn-xray').addEventListener('click', (e) => {
      const on = !this.app.viewer.xray;
      this.app.viewer.setXray(on);
      e.currentTarget.classList.toggle('on', on);
    });
    $('btn-fit').addEventListener('click', () => this.app.viewer.fit());
    $('btn-spin').addEventListener('click', (e) => {
      const on = !this.app.viewer.controls.autoRotate;
      this.app.viewer.setSpin(on);
      e.currentTarget.classList.toggle('on', on);
    });

    /* legend */
    $('btn-legend').addEventListener('click', (e) => {
      const body = $('legend-body');
      const hidden = body.classList.toggle('hidden');
      e.currentTarget.textContent = hidden ? 'show' : 'hide';
    });

    /* bottom bar */
    $('explode-slider').addEventListener('input', (e) => {
      this.app.setExplode(Number(e.target.value) / 100);
    });
    $('step-slider').addEventListener('input', (e) => {
      this.app.setStep(Number(e.target.value));
    });
    $('btn-reset').addEventListener('click', () => this.app.resetView());
    $('btn-play').addEventListener('click', () => this.app.togglePlay());
    $('anim-scrub').addEventListener('input', (e) => {
      this.app.scrub(Number(e.target.value) / 1000);
    });
    $('anim-speed').addEventListener('change', (e) => {
      this.app.viewer.speed = Number(e.target.value);
    });
    $('btn-loop').addEventListener('click', (e) => {
      const on = !this.app.viewer.loop;
      this.app.viewer.loop = on;
      e.currentTarget.classList.toggle('on', on);
    });

    /* help */
    $('btn-help').addEventListener('click', () => { $('help-modal').hidden = false; });
    $('help-close').addEventListener('click', () => { $('help-modal').hidden = true; });
    $('help-modal').addEventListener('click', (e) => {
      if (e.target.id === 'help-modal') $('help-modal').hidden = true;
    });

    /* source picker */
    $('source-select').addEventListener('change', (e) => this.app.changeSource(e.target.value));
  }

  setTab(name) {
    document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
    document.querySelectorAll('.panel').forEach((p) => p.classList.toggle('active', p.id === `panel-${name}`));
  }

  /* ============================================================
     Populate from data
     ============================================================ */
  populate(data) {
    this.data = data;
    const $ = this.$;

    /* header stats */
    const s = data.stats();
    $('stat-parts').textContent = s.parts.toLocaleString();
    $('stat-steps').textContent = s.steps;
    $('stat-harness').textContent = s.harnesses;
    $('stat-modules').textContent = s.modules;
    $('stat-wires').textContent = s.wires;

    /* filter dropdowns */
    const fg = $('filter-group');
    fg.innerHTML = '<option value="">All groups</option>' +
      data.groupList.map((g) => `<option value="${g}">${esc(data.groupLabel(g))}</option>`).join('');

    const fc = $('filter-collection');
    fc.innerHTML = '<option value="">All collections</option>' +
      data.collectionList.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join('');

    const fm = $('filter-module');
    fm.innerHTML = '<option value="">All modules</option>' +
      data.moduleList.map((m) => `<option value="${m.key}">${cap(m.key)} (${m.partCount})</option>`).join('');

    /* step slider */
    const ss = $('step-slider');
    ss.max = String(data.stepCount);
    ss.value = '0';

    /* legend */
    this._buildLegend();

    /* lists */
    this.refreshParts();
    this.refreshHarnesses();
    this.refreshModules();
  }

  _buildLegend() {
    const data = this.data;
    const counts = new Map();
    for (const p of data.parts) counts.set(p.group, (counts.get(p.group) || 0) + 1);

    const rows = [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([code, n]) => {
        const col = GROUP_COLORS[code] || '#8a97a8';
        const doc = data.groupDocs[code] || '';
        return `<div class="lg"><i style="background:${col}"></i>${esc(code)} · ${esc(doc)} <span style="margin-left:auto;color:#66748a">${n}</span></div>`;
      })
      .join('');

    const extra = `
      <div class="lg" style="margin-top:6px;border-top:1px solid #262e3c;padding-top:6px">
        <i style="background:#ffc247"></i>wire / hose trace
      </div>`;

    this.$('legend-body').innerHTML = rows + extra;
  }

  /* ============================================================
     Parts list (virtualised)
     ============================================================ */
  refreshParts() {
    const data = this.data;
    if (!data) return;

    const q = this.query;
    const modParts = this.fModule ? new Set(data.modules[this.fModule]?.parts || []) : null;
    const v = this.app.viewer;

    this.filtered = data.parts.filter((p) => {
      if (this.fGroup && p.group !== this.fGroup) return false;
      if (this.fCollection && p.collection !== this.fCollection) return false;
      if (modParts && !modParts.has(p.name)) return false;
      if (this.fState === 'hidden' && !v.hidden.has(p.name)) return false;
      if (this.fState === 'visible' && v.hidden.has(p.name)) return false;
      if (this.fState === 'selected' && v.selected !== p.name) return false;
      if (q) {
        const hay = `${p.name} ${p.group} ${p.collection} ${p.sub} ${p.part} ${p.material_key || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    this.$('part-count').textContent =
      `${this.filtered.length.toLocaleString()} / ${data.partCount.toLocaleString()}`;

    const scroll = this.$('part-list-scroll');
    scroll.scrollTop = 0;
    this._renderParts();
  }

  _queueRender() {
    if (this._renderQueued) return;
    this._renderQueued = true;
    requestAnimationFrame(() => { this._renderQueued = false; this._renderParts(); });
  }

  _renderParts() {
    const scroll = this.$('part-list-scroll');
    const inner = this.$('part-list-inner');
    const total = this.filtered.length;

    inner.style.height = `${total * ROW_H}px`;
    inner.style.position = 'relative';

    const top = scroll.scrollTop;
    const h = scroll.clientHeight || 400;
    const start = Math.max(0, Math.floor(top / ROW_H) - OVERSCAN);
    const end = Math.min(total, Math.ceil((top + h) / ROW_H) + OVERSCAN);

    const v = this.app.viewer;
    const frag = document.createDocumentFragment();

    for (let i = start; i < end; i++) {
      const p = this.filtered[i];
      const row = document.createElement('div');
      row.className = 'row';
      row.style.position = 'absolute';
      row.style.top = `${i * ROW_H}px`;
      row.style.left = '0';
      row.style.right = '0';
      row.style.height = `${ROW_H}px`;
      if (v.selected === p.name) row.classList.add('selected');
      if (v.hidden.has(p.name)) row.classList.add('hidden-part');
      row.dataset.name = p.name;

      const col = GROUP_COLORS[p.group] || '#8a97a8';
      row.innerHTML =
        `<i class="swatch" style="background:${col}"></i>` +
        `<span class="rname" title="${esc(p.name)}">${esc(p.name)}</span>` +
        `<span class="rmeta">${esc(p.group)}</span>` +
        `<button class="eye" title="toggle visibility">${v.hidden.has(p.name) ? '◌' : '●'}</button>`;

      row.addEventListener('click', (e) => {
        if (e.target.classList.contains('eye')) {
          const nowHidden = v.hidden.has(p.name);
          v.setVisible(p.name, nowHidden);
          this.refreshParts();
          return;
        }
        this.app.selectPart(p.name, { focus: true });
      });

      frag.appendChild(row);
    }

    inner.replaceChildren(frag);
  }

  /* ============================================================
     Harnesses
     ============================================================ */
  refreshHarnesses() {
    const data = this.data;
    if (!data) return;
    const v = this.app.viewer;

    this.$('harness-count').textContent = data.harnessList.length;
    this.$('hose-count').textContent = data.hoseSystemList.length;

    /* --- wire harnesses --- */
    const hl = this.$('harness-list');
    hl.replaceChildren();
    for (const h of data.harnessList) {
      const on = !h.wires.every((w) => v.hidden.has(w.name));
      this.harnessOn.set(h.name, on);

      const row = document.createElement('div');
      row.className = 'hrow';
      row.innerHTML =
        `<span class="switch ${on ? 'on' : ''}"></span>` +
        `<span class="hname">${esc(h.name)}</span>` +
        `<span class="hcount">${h.count}w · ${h.length.toFixed(1)}m</span>`;

      row.querySelector('.switch').addEventListener('click', (e) => {
        e.stopPropagation();
        const now = !this.harnessOn.get(h.name);
        this.harnessOn.set(h.name, now);
        v.setHarnessVisible(h.name, now);
        this.refreshHarnesses();
      });
      row.addEventListener('click', () => {
        this.app.isolateHarness(h.name);
      });
      hl.appendChild(row);
    }

    /* --- hoses + straps --- */
    const ol = this.$('hose-list');
    ol.replaceChildren();
    for (const s of data.hoseSystemList) {
      const all = [...s.hoses, ...s.straps];
      const on = !all.every((x) => v.hidden.has(x.name));
      this.hoseOn.set(s.name, on);

      const row = document.createElement('div');
      row.className = 'hrow';
      row.innerHTML =
        `<span class="switch ${on ? 'on' : ''}"></span>` +
        `<span class="hname">${esc(s.name)}</span>` +
        `<span class="hcount">${s.hoses.length}h · ${s.straps.length}s</span>`;

      row.querySelector('.switch').addEventListener('click', (e) => {
        e.stopPropagation();
        const now = !this.hoseOn.get(s.name);
        this.hoseOn.set(s.name, now);
        v.setHoseSystemVisible(s.name, now);
        this.refreshHarnesses();
      });
      row.addEventListener('click', () => {
        const names = new Set(all.map((x) => x.name));
        v.isolate(names);
        this.app.setStatus(`isolated hose system ${s.name}`);
      });
      ol.appendChild(row);
    }
  }

  _bulkHarness(on) {
    const v = this.app.viewer;
    for (const h of this.data.harnessList) v.setHarnessVisible(h.name, on);
    this.refreshHarnesses();
  }

  _bulkHose(on) {
    const v = this.app.viewer;
    for (const s of this.data.hoseSystemList) v.setHoseSystemVisible(s.name, on);
    this.refreshHarnesses();
  }

  /* ============================================================
     Modules
     ============================================================ */
  refreshModules() {
    const data = this.data;
    if (!data) return;
    const v = this.app.viewer;

    this.$('module-count').textContent = data.moduleList.length;

    const ml = this.$('module-list');
    ml.replaceChildren();

    for (const m of data.moduleList) {
      const on = !m.parts.every((n) => v.hidden.has(n));
      this.moduleOn.set(m.key, on);

      const card = document.createElement('div');
      card.className = 'mcard';
      if (v.isolated && m.parts.length && v.isolated.has(m.parts[0])) card.classList.add('isolated');

      card.innerHTML =
        `<h4>${cap(m.key)}</h4>` +
        `<div class="mfile">${esc(m.file)}</div>` +
        `<div class="mstats"><span>${m.partCount} parts</span><span>${m.collections.length} collections</span></div>` +
        `<div class="mcols">${m.collections.map(esc).join(' · ')}</div>`;

      card.addEventListener('click', () => this.app.isolateModule(m.key));
      ml.appendChild(card);
    }
  }

  _bulkModule(on) {
    const v = this.app.viewer;
    for (const m of this.data.moduleList) v.setModuleVisible(m.key, on);
    this.refreshModules();
  }

  /* ============================================================
     Info card
     ============================================================ */
  showInfo(name) {
    const card = this.$('info-card');
    if (!name) { card.hidden = true; return; }

    const data = this.data;
    const p = data.part(name);
    card.hidden = false;

    this.$('info-name').textContent = name;

    if (!p) {
      this.$('info-group').textContent = '—';
      this.$('info-sub').textContent = '—';
      this.$('info-collection').textContent = '—';
      this.$('info-module').textContent = '—';
      this.$('info-material').textContent = '—';
      this.$('info-step').textContent = '—';
      this.$('info-notes').textContent = 'Not a manifest part (scene helper or sequence empty).';
      return;
    }

    const mod = data.moduleFor(name);
    const step = data.stepFor(name);

    this.$('info-group').textContent = data.groupLabel(p.group);
    this.$('info-sub').textContent = p.sub || '—';
    this.$('info-collection').textContent = p.collection || '—';
    this.$('info-module').textContent = mod ? cap(mod.key) : '—';
    this.$('info-material').textContent = p.material_key || p.material || '—';
    this.$('info-step').textContent = step ? `${step.step}. ${step.title}` : '—';
    const noGeo = this.app.viewer.noGeometry && this.app.viewer.noGeometry.has(name);
    this.$('info-notes').textContent = noGeo
      ? 'Listed in the manifest but exported without mesh geometry (non-mesh object in the .blend).'
      : (p.notes || '');
  }

  /* ============================================================
     Bottom bar
     ============================================================ */
  setExplodeUI(amount, stepLimit) {
    this.$('explode-slider').value = String(Math.round(amount * 100));
    this.$('explode-val').textContent = `${Math.round(amount * 100)}%`;
    this.$('step-slider').value = String(stepLimit);
    this.$('step-val').textContent = stepLimit === 0 ? 'assembled' : `step ${stepLimit}`;
  }

  setAnimUI(t, duration, playing) {
    this.$('anim-scrub').value = String(Math.round((t / (duration || 1)) * 1000));
    this.$('anim-time').textContent = `${t.toFixed(2)}s / ${duration.toFixed(2)}s`;
    const b = this.$('btn-play');
    b.textContent = playing ? '❚❚' : '▶';
    b.classList.toggle('playing', playing);
  }

  setStatus(text) { this.$('status-text').textContent = text; }
  setFps(n) { this.$('fps').textContent = `${n} fps`; }
  setHover(name) {
    const el = this.$('hover-readout');
    if (!name) { el.hidden = true; return; }
    el.hidden = false;
    el.textContent = name;
  }
}

/* ---------- helpers ---------- */
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function cap(s) { return String(s).charAt(0).toUpperCase() + String(s).slice(1); }
