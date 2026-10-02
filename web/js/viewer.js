/* ============================================================
   viewer.js — three.js scene, picking, explode, animation
   ============================================================ */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import {
  buildTraceAttribute,
  buildTraceAttributeFromGeometry,
  polylineToLocal,
  makeTraceMaterial,
  TraceController,
} from './trace.js';

const TRACE_GLOW = 0xffc247;

export class Viewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.data = null;

    /* ---------- renderer ---------- */
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      powerPreference: 'high-performance',
      preserveDrawingBuffer: true,
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.45;

    /* ---------- scene ---------- */
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0d131c);
    this.scene.fog = new THREE.Fog(0x0d131c, 22, 60);

    /* ---------- camera ---------- */
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.05, 300);
    this.camera.position.set(5.2, 3.0, 5.6);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.075;
    this.controls.minDistance = 0.6;
    this.controls.maxDistance = 40;
    this.controls.maxPolarAngle = Math.PI * 0.495;
    this.controls.target.set(0, 0.7, 0);

    this._setupLights();
    this._setupGround();

    /* ---------- state ---------- */
    this.root = null;
    this.mixer = null;
    this.actions = [];
    this.clips = [];
    this.animTime = 0;
    this.animDuration = 1;
    this.playing = false;
    this.speed = 1;
    this.loop = true;

    this.parts = new Map();        // name -> Mesh
    this.traceMeshes = [];         // wires + hoses + straps
    this.traceByName = new Map();  // name -> Mesh
    this.stepEmpties = [];         // {step, obj, base, dir, distance}
    this.ejected = new Map();      // name -> offset Vector3
    this.hidden = new Set();       // names explicitly hidden
    this.isolated = null;          // Set of names, or null
    this.selected = null;

    this.explodeAmount = 0;
    this.stepLimit = 0;
    this.manualMode = true;

    this.trace = new TraceController({ duration: 1.5, hold: 1.0 });
    this.liveTrace = true;

    this.xray = false;
    this.wireframe = false;

    this._origMaterials = new Map();
    this._raycaster = new THREE.Raycaster();
    this._pointer = new THREE.Vector2();
    this._hoverThrottle = 0;
    this._hovered = null;

    this._clock = new THREE.Clock();
    this._fpsAcc = 0;
    this._fpsFrames = 0;
    this.fps = 0;

    this.onSelect = () => {};
    this.onHover = () => {};
    this.onStatus = () => {};

    this._resize();
    window.addEventListener('resize', () => this._resize());
    this._bindPointer();
    this._loop();
  }

  /* ============================================================
     Scene furniture
     ============================================================ */
  _setupLights() {
    this.scene.add(new THREE.HemisphereLight(0xc8d8ee, 0x2a3038, 1.9));

    const key = new THREE.DirectionalLight(0xfff4e2, 3.0);
    key.position.set(6, 9, 5);
    this.scene.add(key);

    const fill = new THREE.DirectionalLight(0xbcd6ff, 1.5);
    fill.position.set(-7, 4, -5);
    this.scene.add(fill);

    const rim = new THREE.DirectionalLight(0xffe0b0, 1.2);
    rim.position.set(-3, 2.5, 8);
    this.scene.add(rim);

    /* Bounce light from below so the underside of the car is not a black
       silhouette in the default three-quarter view. */
    const bounce = new THREE.DirectionalLight(0xdfe8f5, 0.6);
    bounce.position.set(0, -6, 2);
    this.scene.add(bounce);

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.45));
  }

  _setupGround() {
    const grid = new THREE.GridHelper(40, 80, 0x1d2634, 0x141a24);
    grid.position.y = 0;
    grid.material.transparent = true;
    grid.material.opacity = 0.55;
    this.scene.add(grid);
    this.ground = grid;

    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(60, 60),
      new THREE.MeshStandardMaterial({
        color: 0x0a0d12, roughness: 0.95, metalness: 0.0,
      })
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = -0.002;
    plane.receiveShadow = true;
    this.scene.add(plane);
  }

  _resize() {
    const w = this.canvas.clientWidth || 1;
    const h = this.canvas.clientHeight || 1;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  /* ============================================================
     Load
     ============================================================ */
  async load(url, onProgress = () => {}) {
    const loader = new GLTFLoader();

    const gltf = await new Promise((resolve, reject) => {
      loader.load(
        url,
        resolve,
        (e) => {
          if (e.lengthComputable) onProgress(e.loaded / e.total);
        },
        (err) => reject(err)
      );
    });

    this.root = gltf.scene;
    this.scene.add(this.root);

    this.clips = gltf.animations || [];
    this._index();
    this._applyTraceMaterials();
    this._setupAnimation();
    this.fit();

    return {
      nodes: this.parts.size,
      clips: this.clips.length,
      traceMeshes: this.traceMeshes.length,
    };
  }

  /* ============================================================
     Index the scene graph
     ============================================================ */
  _index() {
    const data = this.data;
    const partNames = data ? data.partsByName : null;

    this.root.traverse((o) => {
      if (!o.name) return;

      if (o.isMesh) {
        if (partNames && partNames.has(o.name)) {
          this.parts.set(o.name, o);
          o.userData.partName = o.name;
        }
        // wires / hoses / tie straps are all trace-capable
        if (data && data.traceNames && data.traceNames.has(o.name)) {
          this.traceMeshes.push(o);
          this.traceByName.set(o.name, o);
          o.userData.isTrace = true;
        }
      }

      if (o.name.startsWith('ALTIMA2000_SEQ_Step')) {
        this.stepEmpties.push({
          name: o.name,
          obj: o,
          base: o.position.clone(),
          dir: new THREE.Vector3(0, 0, 1),
          distance: 0,
        });
      }
    });

    /* attach the manifest's explode direction/distance to each step empty */
    if (data) {
      for (const se of this.stepEmpties) {
        const step = data.steps.find((s) => s.empty === se.name);
        if (step) {
          se.step = step.step;
          se.title = step.title;
          se.dir.set(step.dir[0], step.dir[1], step.dir[2]);
          if (se.dir.lengthSq() < 1e-9) se.dir.set(0, 0, 1);
          se.dir.normalize();
          se.distance = step.distance;
        }
      }
      this.stepEmpties.sort((a, b) => (a.step || 0) - (b.step || 0));
    }

    /* remember original materials for x-ray / wireframe toggles */
    for (const [, mesh] of this.parts) {
      if (mesh.material) this._origMaterials.set(mesh.uuid, mesh.material);
    }

    /* Parts that exist in the manifest but carry no mesh in the glTF
       export (the four roof bows are authored as non-mesh objects).
       They stay listed and searchable, and the info card says so. */
    this.noGeometry = new Set();
    if (data) {
      for (const p of data.parts) {
        if (!this.parts.has(p.name)) this.noGeometry.add(p.name);
      }
    }
  }

  /* ============================================================
     Trace materials on wires / hoses / straps
     ============================================================ */
  _applyTraceMaterials() {
    const data = this.data;
    if (!data) return;

    const geomOwner = new Map();   // geometry.uuid -> mesh that already claimed it

    // world matrices must be current before converting world-space
    // manifest polylines into each mesh's local frame
    this.root.updateMatrixWorld(true);

    for (const mesh of this.traceMeshes) {
      const polyWorld = data.tracePolylines.get(mesh.name);
      const poly = polyWorld ? polylineToLocal(polyWorld, mesh.matrixWorld) : null;

      // geometry may be shared between instances — clone before adding
      // a per-wire attribute so each wire gets its own arc length
      let geom = mesh.geometry;
      if (geomOwner.has(geom.uuid)) {
        geom = geom.clone();
        mesh.geometry = geom;
      }
      geomOwner.set(geom.uuid, mesh);

      // A clone inherits the source's attributes, so drop any inherited
      // aTraceT and always recompute for THIS mesh's own run — otherwise
      // every instance of a shared tube would reuse the first one's trace.
      if (geom.getAttribute('aTraceT')) geom.deleteAttribute('aTraceT');

      // wires + hoses have a manifest polyline; tie straps do not, so
      // fall back to a geometry-derived arc length along their long axis
      const arr = poly
        ? buildTraceAttribute(geom, poly)
        : buildTraceAttributeFromGeometry(geom);
      geom.setAttribute('aTraceT', new THREE.BufferAttribute(arr, 1));

      // base colour from the exported material, so wires keep their
      // red / black / white circuit coding
      let base = 0x2a2f38;
      const om = mesh.material;
      if (om && om.color) base = om.color.clone();

      const mat = makeTraceMaterial(base, {
        glowColor: TRACE_GLOW,
        width: 0.05,
        trail: 0.6,
      });
      mesh.material = mat;
      mesh.userData.traceMaterial = mat;
      this.trace.register(mesh, mat);
    }
  }

  /* ============================================================
     Animation
     ============================================================ */
  _setupAnimation() {
    if (!this.clips.length) return;

    this.mixer = new THREE.AnimationMixer(this.root);

    let maxT = 0;
    for (const clip of this.clips) {
      const action = this.mixer.clipAction(clip);
      action.play();
      // NOTE: do NOT pause the actions. AnimationMixer.setTime() drives the
      // mixer clock, and a paused action ignores it — pausing here would
      // freeze both playback and scrubbing. Playback is controlled by
      // advancing `animTime` ourselves and calling setTime().
      this.actions.push(action);
      maxT = Math.max(maxT, clip.duration);
    }
    this.animDuration = maxT || 1;
    this.mixer.setTime(0);
  }

  setAnimTime(t) {
    if (!this.mixer) return;
    this.animTime = Math.max(0, Math.min(this.animDuration, t));
    this.mixer.setTime(this.animTime);
  }

  play() {
    if (!this.mixer) return;
    this.playing = true;
    this.manualMode = false;
    this.onStatus(this.playing ? 'playing' : 'paused');
  }

  pause() {
    this.playing = false;
    this.onStatus('paused');
  }

  togglePlay() { this.playing ? this.pause() : this.play(); }

  /* ============================================================
     Explode
     ============================================================ */
  setExplode(amount, stepLimit) {
    this.explodeAmount = amount;
    // `stepLimit` is optional: the explode slider drives the whole car,
    // the step slider narrows it to the first N steps.
    if (stepLimit !== undefined) this.stepLimit = stepLimit;
    this.manualMode = true;
    this.playing = false;

    // reset the mixer to the assembled pose, then push the manual offsets
    if (this.mixer) this.mixer.setTime(0);

    for (const se of this.stepEmpties) {
      const included = (se.step || 0) <= this.stepLimit ? 1 : 0;
      const f = amount * included;
      se.obj.position.copy(se.base).addScaledVector(se.dir, se.distance * f);
    }
    this._applyEjections();
  }

  /** Pull a single part off the car. */
  eject(name, distance = 0.55) {
    const mesh = this.parts.get(name);
    if (!mesh) return false;
    const dir = new THREE.Vector3(0, 1, 0);
    // bias the direction away from the car centre so it reads as "removed"
    const wp = new THREE.Vector3();
    mesh.getWorldPosition(wp);
    const away = wp.clone().setY(0);
    if (away.lengthSq() > 1e-6) dir.copy(away.normalize()).add(new THREE.Vector3(0, 0.85, 0)).normalize();
    this.ejected.set(name, dir.multiplyScalar(distance));
    this._applyEjections();
    return true;
  }

  uneject(name) {
    this.ejected.delete(name);
    this._applyEjections();
  }

  clearEjections() {
    this.ejected.clear();
    this._applyEjections();
  }

  _applyEjections() {
    // reset any previously ejected part to its authored local position
    for (const [name, mesh] of this.parts) {
      if (!this.ejected.has(name) && mesh.userData._ejectApplied) {
        mesh.position.copy(mesh.userData._basePos);
        mesh.userData._ejectApplied = false;
      }
    }
    for (const [name, off] of this.ejected) {
      const mesh = this.parts.get(name);
      if (!mesh) continue;
      if (!mesh.userData._basePos) mesh.userData._basePos = mesh.position.clone();
      mesh.position.copy(mesh.userData._basePos).add(off);
      mesh.userData._ejectApplied = true;
    }
  }

  /* ============================================================
     Visibility
     ============================================================ */
  setVisible(name, visible) {
    const mesh = this.parts.get(name);
    if (!mesh) return;
    if (visible) this.hidden.delete(name);
    else this.hidden.add(name);
    this._refreshVisibility();
  }

  showAll() {
    this.hidden.clear();
    this.isolated = null;
    this._refreshVisibility();
  }

  hideAll() {
    for (const [name] of this.parts) this.hidden.add(name);
    this.isolated = null;
    this._refreshVisibility();
  }

  isolate(names) {
    this.isolated = new Set(names);
    this._refreshVisibility();
  }

  clearIsolate() {
    this.isolated = null;
    this._refreshVisibility();
  }

  _refreshVisibility() {
    for (const [name, mesh] of this.parts) {
      let vis = !this.hidden.has(name);
      if (vis && this.isolated) vis = this.isolated.has(name);
      mesh.visible = vis;
    }
    // step empties stay visible; their children carry the flags
    this.onStatus('visibility updated');
  }

  /** Show only the wires of one harness (plus optionally the car). */
  isolateHarness(harnessName) {
    const data = this.data;
    if (!data) return;
    const h = data.harnesses.get(harnessName);
    if (!h) return;
    const names = new Set(h.wires.map((w) => w.name));
    this.isolate(names);
  }

  setHarnessVisible(harnessName, visible) {
    const data = this.data;
    if (!data) return;
    const h = data.harnesses.get(harnessName);
    if (!h) return;
    for (const w of h.wires) {
      if (visible) this.hidden.delete(w.name);
      else this.hidden.add(w.name);
    }
    this._refreshVisibility();
  }

  setHoseSystemVisible(sysName, visible) {
    const data = this.data;
    if (!data) return;
    const s = data.hoseSystems.get(sysName);
    if (!s) return;
    for (const h of s.hoses) {
      if (visible) this.hidden.delete(h.name); else this.hidden.add(h.name);
    }
    for (const t of s.straps) {
      if (visible) this.hidden.delete(t.name); else this.hidden.add(t.name);
    }
    this._refreshVisibility();
  }

  setModuleVisible(key, visible) {
    const data = this.data;
    if (!data) return;
    const m = data.modules[key];
    if (!m) return;
    for (const n of m.parts || []) {
      if (visible) this.hidden.delete(n); else this.hidden.add(n);
    }
    this._refreshVisibility();
  }

  isolateModule(key) {
    const data = this.data;
    if (!data) return;
    const m = data.modules[key];
    if (!m) return;
    this.isolate(new Set(m.parts || []));
  }

  /* ============================================================
     Display modes
     ============================================================ */
  setXray(on) {
    this.xray = on;
    for (const [name, mesh] of this.parts) {
      if (mesh.userData.isTrace) continue;
      if (on) {
        const orig = this._origMaterials.get(mesh.uuid);
        if (!orig) continue;
        if (!mesh.userData._xrayMat) {
          const m = orig.clone();
          m.transparent = true;
          m.opacity = 0.13;
          m.depthWrite = false;
          mesh.userData._xrayMat = m;
        }
        mesh.material = mesh.userData._xrayMat;
      } else {
        const orig = this._origMaterials.get(mesh.uuid);
        if (orig) mesh.material = orig;
      }
    }
  }

  setWireframe(on) {
    this.wireframe = on;
    for (const [, mesh] of this.parts) {
      if (mesh.userData.isTrace) continue;
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of mats) if (m) m.wireframe = on;
    }
  }

  setSpin(on) { this.controls.autoRotate = on; this.controls.autoRotateSpeed = 0.9; }

  /** Ease the orbit target onto a single part. */
  focusOn(name) {
    const mesh = this.parts.get(name);
    if (!mesh) return;
    const wp = new THREE.Vector3();
    mesh.getWorldPosition(wp);
    this.controls.target.lerp(wp, 0.65);
    this.controls.update();
  }

  fit() {
    if (!this.root) return;
    const box = new THREE.Box3().setFromObject(this.root);
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3());
    const centre = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const dist = maxDim / (2 * Math.tan((this.camera.fov * Math.PI) / 360)) * 1.5;

    this.controls.target.copy(centre);
    const dir = new THREE.Vector3(0.72, 0.42, 0.78).normalize();
    this.camera.position.copy(centre).addScaledVector(dir, dist);
    this.camera.near = Math.max(0.02, dist / 500);
    this.camera.far = dist * 12;
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  /* ============================================================
     Picking
     ============================================================ */
  _bindPointer() {
    const c = this.canvas;

    c.addEventListener('pointermove', (e) => {
      const r = c.getBoundingClientRect();
      this._pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
      this._pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
      this._pointerPx = { x: e.clientX - r.left, y: e.clientY - r.top };
    });

    c.addEventListener('pointerleave', () => {
      if (this._hovered) {
        this.trace.release(this._hovered);
        this._hovered = null;
        this.onHover(null);
      }
    });

    // click = select (ignore drags)
    let down = null;
    c.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; });
    c.addEventListener('pointerup', (e) => {
      if (!down) return;
      const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
      down = null;
      if (moved > 4) return;                 // it was an orbit drag
      const hit = this.pick();
      this.select(hit ? hit.name : null);
    });
  }

  /** Raycast against every visible part. Returns {name, mesh} or null. */
  pick() {
    this._raycaster.setFromCamera(this._pointer, this.camera);
    const targets = [];
    for (const [, mesh] of this.parts) if (mesh.visible) targets.push(mesh);
    const hits = this._raycaster.intersectObjects(targets, false);
    if (!hits.length) return null;
    const mesh = hits[0].object;
    return { name: mesh.userData.partName || mesh.name, mesh };
  }

  /** Raycast only the trace meshes (cheap — used for hover). */
  pickTrace() {
    this._raycaster.setFromCamera(this._pointer, this.camera);
    const targets = this.traceMeshes.filter((m) => m.visible);
    const hits = this._raycaster.intersectObjects(targets, false);
    if (!hits.length) return null;
    return hits[0].object;
  }

  select(name) {
    this.selected = name;
    this.onSelect(name);
  }

  /* ============================================================
     Render loop
     ============================================================ */

  /**
   * Schedule the next frame.
   *
   * requestAnimationFrame is the right primitive in a real browser, but in a
   * headless/offscreen context (no compositor) it can fire only a handful of
   * times per second — or not at all — which would freeze the animation, the
   * trace sweep and the hover picking.
   *
   * So: always ask rAF, and arm a watchdog that re-ticks if rAF has not
   * answered within 100 ms. A real browser always answers first (smooth,
   * vsync-aligned); a headless context falls back to the watchdog. The
   * watchdog is deliberately slow — a fast timer would saturate a software
   * renderer and starve the page.
   */
  _schedule(tick) {
    let done = false;
    const fire = () => {
      if (done) return;
      done = true;
      this._watchdog = null;
      tick();
    };
    requestAnimationFrame(fire);
    this._watchdog = setTimeout(fire, 100);
  }

  _loop() {
    const tick = () => {
      this._schedule(tick);
      const dt = Math.min(this._clock.getDelta(), 0.1);

      /* fps */
      this._fpsAcc += dt;
      this._fpsFrames += 1;
      if (this._fpsAcc >= 0.5) {
        this.fps = Math.round(this._fpsFrames / this._fpsAcc);
        this._fpsAcc = 0;
        this._fpsFrames = 0;
      }

      /* animation playback */
      if (this.playing && this.mixer) {
        this.animTime += dt * this.speed;
        if (this.animTime >= this.animDuration) {
          if (this.loop) this.animTime = 0;
          else { this.animTime = this.animDuration; this.playing = false; }
        }
        this.mixer.setTime(this.animTime);
        this.onStatus('playing');
      }

      /* hover trace (throttled) */
      this._hoverThrottle += dt;
      if (this.liveTrace && this._hoverThrottle > 0.05 && this._pointerPx) {
        this._hoverThrottle = 0;
        const hit = this.pickTrace();
        if (hit !== this._hovered) {
          if (this._hovered) this.trace.release(this._hovered);
          this._hovered = hit;
          if (hit) this.trace.run(hit);
          this.onHover(hit ? hit.name : null);
        }
      }

      this.trace.update(dt);
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    };
    tick();
  }
}
