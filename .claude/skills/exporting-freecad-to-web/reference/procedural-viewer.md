# Procedural Parametric Viewer

Second viewer architecture for this skill. Instead of exporting baked glTF
geometry, the page builds every part directly in Three.js from a single
parameter object. Use it when the deliverable is a **configurator**: sliders
change dimensions, the model rebuilds live, and engineering readouts update
alongside.

FreeCAD remains the CAD source of record. The JS geometry mirrors a single
shared parameter dict: define the parameters ONCE (names, defaults, units) and
mirror that dict across the FreeCAD build script and the JS `PARAMS` object.
When a dimension changes in one place, change it in both.

## When to Choose Procedural over glTF Export

Choose procedural when ALL of these hold:

- **Small part count, primitive-composable geometry**: boxes, cylinders,
  extruded 2D shapes (including arcs and holes), lathe profiles. A dozen or
  two parts, not hundreds.
- **Live parameters are the point**: the user wants sliders / toggles that
  reshape the model in the browser (a configurator, a sizing exploration tool).
- **Tiny self-contained payload**: no exports/ directory, no .gltf/.bin files,
  just one HTML file plus vendored three and a sky HDR.

Choose the glTF pipeline (main SKILL.md steps) when the geometry is organic,
Boolean-heavy, or too numerous to re-derive by hand, or when no interactivity
beyond orbiting is needed.

## Template Reuse Map

Start from `reference/index.html` (the glTF viewer template). Keep and drop:

| Piece | Action |
|-------|--------|
| Import map (three + three/addons/) | **Keep** (point at vendored three or CDN) |
| Renderer config (pixelRatio cap, shadows, tone mapping, sRGB) | **Keep** |
| HemisphereLight + DirectionalLight sun + shadow setup | **Keep** (fixed sun position is fine; solar slider optional) |
| HDR env: RGBELoader + PMREMGenerator + `scene.environment` | **Keep** |
| ShadowMaterial ground catcher | **Keep** |
| OrbitControls + damping | **Keep** |
| `GLTFLoader` import and the whole model-load block | **Drop** |
| `BufferGeometryUtils` (if present) | **Drop** (it is a GLTFLoader-only dependency) |
| `findModelSrc()`, export-info.json fetch, exports/ dir | **Drop** |

Vendoring three: copy `three.module.min.js` (+ `three.core.min.js`, which the
module build imports internally) into `public/vendor/three/build/`, and only
the addons actually imported (`controls/OrbitControls.js`,
`loaders/RGBELoader.js`) into `public/vendor/three/examples/jsm/`. Point the
import map at `./vendor/three/...`.

**Deploy script pitfall**: if you copy an existing `sync-to-s3.sh`, DELETE its
exports/ upload block. A procedural viewer has no `public/exports/` directory,
and `aws s3 cp --recursive` on a missing directory exits non-zero, which under
`set -euo pipefail` aborts the whole deploy. Upload `index.html` (no-cache),
`vendor/` and `assets/` (long cache), nothing else.

## Core Architecture

Four rules. Everything else is decoration.

**1. Single `PARAMS` object** (all lengths in one unit, mm recommended):

```js
const PARAMS = {
  span: 1000, plate_t: 6, arm_len: 240, hole_d: 12,
  variant: 'B', braces: false, labels: true,
};
```

**2. One delegated `input` listener** on the control container. Every control
carries `data-param="<key>"`; the listener writes into PARAMS then rebuilds.
No per-control handlers.

```js
ui.addEventListener('input', (e) => {
  const el = e.target;
  const p = el.dataset.param;
  if (!p) return;
  if (el.type === 'checkbox')   PARAMS[p] = el.checked;
  else if (el.type === 'radio') PARAMS[p] = el.value;
  else { PARAMS[p] = parseFloat(el.value); updateReadout(el); }
  saveConfig();
  if (p === 'labels') return;          // overlay-only params skip the rebuild
  rebuild();
});
```

**3. `rebuild()` disposes then reconstructs** the parts group. Three.js does
not garbage-collect GPU resources; skipping disposal leaks VRAM on every
slider tick.

```js
let partsGroup = null;
function disposeGroup(group) {
  group.traverse(node => {
    if (!node.isMesh) return;
    node.geometry.dispose();
    if (Array.isArray(node.material)) node.material.forEach(m => m.dispose());
    else node.material.dispose();
  });
}
function rebuild() {
  if (partsGroup) { assembly.remove(partsGroup); disposeGroup(partsGroup); }
  partsGroup = buildParts(PARAMS);
  assembly.add(partsGroup);
  renderResults();                     // live readouts (see below)
}
```

**4. Static context geometry** (surroundings, scale figure, floor) is built
ONCE into a separate group and toggled with `.visible`, never rebuilt:

```js
const contextGroup = buildContext();   // built once at startup
assembly.add(contextGroup);
// on toggle: contextGroup.visible = PARAMS.showContext;
```

A convenient wrapper group maps CAD coordinates to Three.js in one place
(model Z-up mm -> viewer Y-up meters), so `buildParts()` works in native CAD
coordinates:

```js
const assembly = new THREE.Group();
assembly.rotation.x = -Math.PI / 2;
assembly.scale.setScalar(0.001);
scene.add(assembly);
```

## Techniques

### ExtrudeGeometry from 2D Shapes with arc segments

For plates that meet cylinders (exact curved cutouts), build a `THREE.Shape`
with lines plus `absarc`, then extrude. Compute the arc endpoints from the
cylinder radius so the cutout is exact at any parameter value:

```js
function plateGeo(P) {
  const R = P.boss_d / 2;                       // cylinder the plate meets
  const yIn = P.width / 2 - P.plate_t, yOut = P.width / 2;
  const xIn = Math.sqrt(R * R - yIn * yIn);     // arc endpoints on the circle
  const xOut = Math.sqrt(R * R - yOut * yOut);
  const s = new THREE.Shape();
  s.moveTo(P.span / 2, yIn);
  s.lineTo(P.span / 2, yOut);
  s.lineTo(xOut, yOut);
  s.absarc(0, 0, R, Math.atan2(yOut, xOut), Math.atan2(yIn, xIn), true);
  s.closePath();
  const geo = new THREE.ExtrudeGeometry(s, {
    depth: P.plate_h, bevelEnabled: false, curveSegments: 16,
  });
  geo.translate(0, 0, -P.plate_h / 2);          // center on the mid-plane
  return geo;
}
```

Holes: push a `THREE.Path` with a reversed `absarc` into `shape.holes`. An
annulus (ring/pipe cross-section) is just a full-circle shape with a
full-circle hole, extruded.

### LatheGeometry from a measured point table

Revolved organic shapes (a flared hood, a vase profile) come out well from a
`[height, radius]` table measured off a drawing or photo:

```js
const PROFILE = [[0, 220], [40, 210], [90, 180], /* ... */ [400, 60]];
const pts = PROFILE.map(([h, r]) => new THREE.Vector2(r, h));
const geo = new THREE.LatheGeometry(pts, 64);
geo.rotateX(Math.PI / 2);          // lathe axis Y -> model Z-up
```

Rescale the table's height column with a single multiplier if the real object
height differs from the table span. Add an explicit vertical brim segment
(two points at the same radius) where the profile starts with a flat rim.

### Screen-projected HTML annotation labels (no CSS2DRenderer)

Absolutely-positioned divs over the canvas, repositioned each frame. No extra
renderer, no vendor additions. Key points, all load-bearing:

- Create the label divs ONCE at startup; each frame only repositions and
  toggles them. Rebuilds then cannot leak DOM nodes, and dynamic pill text is
  a cheap `textContent` update.
- Project after `renderer.render()` so camera and group matrices are current.
- Anchor is a `Vector3` in model coordinates; transform with the wrapper
  group's world matrix, then project.
- Hide when `ndc.z` is outside [-1, 1] (behind the camera / outside depth).
- Clamp to the viewport and flip the pill to the other side of its dot near
  the right edge, so no pill ever overflows.

```js
const _v = new THREE.Vector3();
function updateLabels() {
  for (const L of labels) {
    let show = PARAMS.labels;
    if (show) {
      _v.copy(L.anchor).applyMatrix4(assembly.matrixWorld).project(camera);
      if (_v.z > 1 || _v.z < -1) show = false;
      else {
        let x = ( _v.x * 0.5 + 0.5) * window.innerWidth;
        let y = (-_v.y * 0.5 + 0.5) * window.innerHeight;
        const pw = L.pill.offsetWidth, ph = L.pill.offsetHeight;
        const flip = x + 7 + pw > window.innerWidth - 6;
        L.el.classList.toggle('flip', flip);
        x = Math.max(Math.min(x, window.innerWidth - 6), flip ? pw + 14 : 6);
        y = Math.min(Math.max(y, ph + 14), window.innerHeight - 6);
        L.el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
      }
    }
    L.el.style.display = show ? '' : 'none';
  }
}
// render loop: renderer.render(scene, camera); updateLabels();
```

CSS: a `.lbl` wrapper at `left:0; top:0` moved via `transform`, containing a
small `.dot` span and a `.pill` span offset from it; a `.flip .pill` rule
mirrors the pill to the left side. Optionally hide a label whose screen
anchor falls inside an open UI panel's `getBoundingClientRect()`.

### Live engineering readouts

Compute mass, section modulus, stress, deflection, safety factors
analytically from PARAMS in a pure `computeResults(P)` function, and render
them into the control panel on every rebuild. The sliders then double as an
exploration tool. Color-code verdict spans with three classes
(`ok` / `warn` / `bad`) driven by utilization thresholds; a thin bar whose
width and color track utilization reads well. Port the formulas from the same
Python sizing script that drives the FreeCAD model, so both agree.

### localStorage persistence

Order of operations matters:

1. **Freeze defaults BEFORE merging storage**:
   `const DEFAULTS = Object.freeze(structuredClone(PARAMS));`
2. **Whitelist keys**: separate lists of stored numeric / boolean / enum keys.
   Never `Object.assign` raw parsed JSON into PARAMS.
3. **Clamp numerics against the DOM control** (its min/max/step is the single
   source of truth), snapping to step:

```js
function clampToControl(el, v) {
  if (typeof v !== 'number' || !Number.isFinite(v)) return null;
  const min = parseFloat(el.min), max = parseFloat(el.max);
  const step = parseFloat(el.step) || 1;
  let x = Math.min(max, Math.max(min, v));
  x = min + Math.round((x - min) / step) * step;
  return Math.min(max, Math.max(min, x));
}
```

4. **`syncControlsFromParams()`** pushes the restored state into every slider,
   radio, and checkbox (plus readout text) before the first rebuild.
5. **try/catch every storage access** (private mode throws); degrade silently.
6. **Reset button**: remove the storage key, `Object.assign(PARAMS,
   structuredClone(DEFAULTS))`, sync controls, rebuild.

Save on every param change (`saveConfig()` inside the delegated listener).
Do not persist UI-chrome state like panel collapse.

### CanvasTexture for patterned materials

For a simple patterned material (fabric print, speckle), draw random blobs on
an offscreen canvas instead of shipping an image asset:

```js
const c = document.createElement('canvas'); c.width = c.height = 256;
const ctx = c.getContext('2d');
// fill base color, loop: translate/rotate to random spots, draw ellipses
const tex = new THREE.CanvasTexture(c);
tex.colorSpace = THREE.SRGBColorSpace;
tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85 });
```

### Camera presets and recenter

Store one preset (position + target) per view mode:

```js
const CAM_PRESETS = {
  overview: { pos: [7.2, 0, 11.2], target: [0, -2.6, 0] },
  detail:   { pos: [3.3, 1.5, 3.7], target: [0, 0.3, 0] },
};
function resetCamera() {
  const p = CAM_PRESETS[currentMode()];
  camera.position.set(...p.pos);
  controls.target.set(...p.target);
  controls.update();
}
```

To derive a preset that fits an extent E (largest model dimension in viewer
units): required camera distance is roughly `(E / 2) / tan(fovDeg / 2 * PI/180)`
plus a margin; place the camera on a pleasant diagonal at that distance from
the target. A small fixed recenter button (bottom corner fab) calls
`resetCamera()` for the CURRENT mode. When a mode toggle changes what is
visible, apply that mode's preset as part of the toggle handler.

### Mobile layout

Verified pitfalls from a real build:

- **Control rows as CSS grid** with a reserved value column:
  `grid-template-columns: minmax(0, auto) minmax(70px, 1fr) 3.9rem;`
  (label / flexible slider / value). Fixed-width sliders WILL push the value
  text off-screen inside a max-width pill. On very narrow screens, move the
  label to its own row with `.param-row:has(.param-slider)`.
- **Cap panel width against the viewport**:
  `max-width: min(calc(100vw - 3.2rem), 26rem);` so padding can never
  overflow.
- **Collapsible panels with an always-visible reopen affordance**: a collapse
  button inside the panel plus a fixed fab button that appears when the panel
  is hidden. Start collapsed below ~640px.
- **`100dvh` over `100vh`** for panel max-height caps (excludes mobile
  browser chrome); declare the `vh` fallback first, `dvh` second.
- Scrollable panels need `-webkit-overflow-scrolling: touch` and
  `overscroll-behavior: contain`.

### Copy-to-clipboard config summary

A "copy configuration" button serializes PARAMS + computed results into plain
text. Use `navigator.clipboard.writeText` with a hidden-textarea
`document.execCommand('copy')` fallback (clipboard API requires a secure
context). Include `location.origin + location.pathname` in the text as a
self-adapting share link (works unchanged on localhost, LAN, and the deployed
URL). Flash the button label briefly to confirm.

## Verification

- Every slider tick rebuilds without console errors and without growing GPU
  memory (check `renderer.info.memory.geometries` stays flat across many
  rebuilds).
- Reload restores the last configuration; the reset button returns exact
  factory defaults; a corrupt or out-of-range stored value falls back cleanly.
- Labels stay pinned to their parts while orbiting, never overflow the
  viewport, and disappear when their anchor is behind the camera.
- On a phone-width viewport: no horizontal overflow, value texts visible,
  panels collapsible and reopenable.
- Deploy script runs green with no exports/ directory present.
- Parameter names and defaults match the FreeCAD build script's dict exactly.
