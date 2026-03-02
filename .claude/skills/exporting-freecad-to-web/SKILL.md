---
name: exporting-freecad-to-web
description: Sets up an interactive Three.js web viewer for any FreeCAD document. Covers
  the export pipeline (FreeCAD -> glTF cleanup), viewer customization (title, solar
  coordinates, model orientation offset), and local serving over the network.
  Works with any document where objects are tagged MCP_Role=Final.
---

# Exporting a FreeCAD Document to a Web Viewer

## When to Use

When the user wants to publish a FreeCAD 3D model as an interactive browser-based
viewer with realistic sun lighting and a time-of-day slider. Invoke at the start of
a new web-export setup, or when resuming an existing one for a different document.

## Prerequisites

- FreeCAD is running with the MCP addon active and connected (port 9875)
- All objects to export are tagged `MCP_Role = Final`. If not, run `tag_all_objects()`
  then `show_by_role(doc, ["Final"])` before exporting (see CLAUDE.md).
- `uv` is available in PATH (`uv --version`)
- Node.js / npx available (`npx --version`)

## Steps

### 1. Create the directory structure

`.designs/<doc-name>/` is gitignored (local only). Create the web-export folder there:

```bash
# Run from the repo root
SKILL=".claude/skills/exporting-freecad-to-web"
DEST=".designs/<doc-name>/web-export"   # replace <doc-name> with FreeCAD doc name

mkdir -p "$DEST/assets" "$DEST/exports"
cp "$SKILL/scripts/export_glb.py"  "$DEST/"
cp "$SKILL/reference/index.html"   "$DEST/"
cp "$SKILL/reference/package.json" "$DEST/"
cd "$DEST"
```

All remaining steps assume you are inside `web-export/`.

Final structure (before first export):
```
web-export/
  assets/          # sky.hdr goes here (Step 2)
  exports/         # written by export script (Step 4)
  export_glb.py
  index.html
  package.json
```

### 2. Obtain a sky HDR file

The viewer requires an equirectangular HDR environment map at `assets/sky.hdr`.

- Download any 2k `.hdr` from [Polyhaven](https://polyhaven.com/hdris)
  (sky/overcast categories work best for outdoor architecture)
- Rename it to `sky.hdr` and place it in `web-export/assets/`
- File size ~1 MB for 2k resolution

### 3. Customize the viewer

Open `web-export/index.html`. All project-specific values are in the `CONFIG`
block near the top of the `<script type="module">` section.

**a. Title and UI strings**

Update both the `<title>` tag and the overlay `<h1>`/`<p class="subtitle">` in the
HTML, and the matching `CONFIG.title`, `CONFIG.subtitle`, `CONFIG.solarLabel`.

**b. Solar location**

Set `CONFIG.latitude`, `CONFIG.longitude`, `CONFIG.tzOffset` to the real site
coordinates and UTC offset (use summer time if the season is summer):

```js
latitude:  48.858,   // Paris example
longitude:  2.347,
tzOffset:   2,       // CEST (UTC+2)
```

**c. Date for sun trajectory**

Set `CONFIG.month` and `CONFIG.day` to a meaningful date (e.g. summer/winter
solstice for the most extreme sun angle, or a project-specific date):

```js
month: 6,
day:   21,   // summer solstice
```

**d. Slider range**

Set `CONFIG.sliderMin` / `CONFIG.sliderMax` to approximate sunrise/sunset for your
location and date (hours as float, e.g. 4.5 = 04:30). Use an online sun calculator
(e.g. timeanddate.com) if unsure.

**e. Locale**

Set `CONFIG.locale` (e.g. `'en-US'`, `'sv-SE'`, `'de-DE'`) for the export
timestamp display. Set `CONFIG.renderedAtLabel` to the local word for "Rendered".

### 4. Run the export

From inside `web-export/`:

```bash
uv run export_glb.py
```

The script:
1. Connects to FreeCAD via XML-RPC (port 9875)
2. Exports all visible `MCP_Role=Final` objects via `ImportGui.export()`
3. Applies cleanup: dedup root nodes, strip alpha-0, merge materials, fix Z-fighting
4. Centers the model at origin (X=0, Z=0, Y_min=0)
5. Writes `exports/<doc_name>.gltf` + `.bin` + `export-info.json`

On success:
```
Exported N objects | triangles: BEFORE -> AFTER | Written to exports/<doc_name>.gltf (XX KB)
```

Options:
- `--output PATH` — custom output path
- `--format glb` — single binary file instead of gltf+bin
- `--skip-export` — re-run cleanup on an existing file (no FreeCAD connection needed)

### 5. Serve locally

```bash
npm run serve            # serves on port 3001
```

For network access from phone/tablet (same Wi-Fi):

```bash
ipconfig getifaddr en0   # macOS local IP
# then visit http://<ip>:3001 on any device
```

Verify the model loads: overlay title appears, sun sphere is visible, slider works.

### 6. Calibrate the model orientation offset

The `CONFIG.modelNorthOffset` corrects for the model being rotated in FreeCAD
relative to true geographic North. Default is `0`.

**Calibration procedure:**

1. Find a time of day when you know exactly where the sun should be at the site
   (e.g. early morning when you were there, or from site photos with known time).
2. Move the slider to that time and observe the sun sphere's position.
3. Compare its direction to where the sun should actually be from the model's
   perspective (which wall faces North/South/East/West on the real building).
4. Each degree of clockwise rotation needed: add 1 to `modelNorthOffset`.
   Each degree counterclockwise: subtract 1.

**Shortcut for time-offset errors:** If the viewer's 14:00 looks like your 16:00
in real life, use `window.solarPos` (always exposed by the template) in the browser
console to compute the exact offset:

```js
// Example: viewer sun at 14:00 looks like real 16:00
const az14 = solarPos(CONFIG.latitude, CONFIG.longitude, CONFIG.year,
                       CONFIG.month, CONFIG.day, 14, CONFIG.tzOffset).azimuth;
const az16 = solarPos(CONFIG.latitude, CONFIG.longitude, CONFIG.year,
                       CONFIG.month, CONFIG.day, 16, CONFIG.tzOffset).azimuth;
console.log("Add to modelNorthOffset:", az16 - az14);
// Positive result → increase offset; negative → decrease
```

After updating `CONFIG.modelNorthOffset`, reload and verify.

### 7. Set the default camera position

On first load the camera auto-fits to the model center. After calibration, lock in
a preferred default view:

**a. Navigate to the desired view** in the browser.

**b. Expose camera state** — temporarily add inside the module, after `controls.update()`:

```js
window.__camera   = camera;
window.__controls = controls;
```

**c. Read the values** in the browser console (or via DevTools evaluate):

```js
JSON.stringify({
  pos: { x: window.__camera.position.x,
         y: window.__camera.position.y,
         z: window.__camera.position.z },
  tgt: { x: window.__controls.target.x,
         y: window.__controls.target.y,
         z: window.__controls.target.z }
})
```

**d. Hardcode the values** in `index.html` — update **both** lines:

```js
camera.position.set(X, Y, Z);       // update the TODO line (~line 202)
controls.target.set(TX, TY, TZ);    // update the TODO line (~line 213)
```

**e. Delete the auto-fit block** in the model load callback — find and remove:

```js
// DELETE THIS BLOCK (the auto-fit block in the load callback):
const size = box.getSize(new THREE.Vector3());
controls.target.set(
  modelSphere.center.x,
  box.min.y + size.y * 0.3,
  modelSphere.center.z
);
controls.update();
```

Replace it with just `controls.update();`. This is the critical step — until you
delete this block, the model load always overwrites your hardcoded target.

**f. Remove** the `window.__camera/controls` lines you added in step (b).

After these changes, the page opens at your calibrated view on every reload.

## Verification

- `exports/<doc_name>.gltf` exists with a non-zero `.bin` beside it
- `exports/export-info.json` contains a valid timestamp and `triangles > 0`
- Model loads in browser without "NO MODEL FOUND" / "ERROR LOADING MODEL"
- Sun sphere rises from the correct compass direction for the real site location
- Shadow direction is consistent with sun position at all slider times
- Slider moves sun smoothly through the sky without jumps
- Camera opens at the configured default view on hard reload
