# CAD Tooling Source Reference (ezdxf + QCAD)

Source for the candidate **2D permit-drawing stack** (ezdxf authoring + QCAD companion), cloned
locally under `vendor/` (gitignored), mirroring the FreeCAD vendoring. Set up / refresh with:

```bash
./scripts/setup-cad-sources.sh
```

Versions pinned in `.EZDXF_VERSION` (`v1.4.4` — the version the workflow research tested) and
`.QCAD_VERSION` (`default` = community master). GitHub fallback if `vendor/` is absent:
`https://github.com/mozman/ezdxf` · `https://github.com/qcad/qcad`.

Role split: ezdxf = code-authored DXF/PDF, QCAD = DWG base-map import + headless `dwg2pdf`. The
geometry comes from the FreeCAD model via `vendor/FreeCAD` APIs — see "The FreeCAD bridge" below.
Any live permit case using this stack is tracked in that document's `.designs/` entry (local only).

---

## ezdxf — `vendor/ezdxf/src/ezdxf/`  (pure Python, very readable)

| Path | What's there |
|------|-------------|
| `entities/` | One module per DXF entity: `line.py`, `arc.py`, `lwpolyline.py`, `hatch.py`, `mtext.py`, `text.py`, `dimension.py`, `insert.py` (block refs), `dimstyle.py` |
| `entities/dimstyle.py` | **DIMSTYLE** — the `dimscale`/`dimtxt`/arrow-size knobs behind the "giant text" gotcha |
| `render/` | Dimension + annotation rendering: `dim_base.py`, `dim_linear.py`, `dim_curved.py`, `arrows.py` |
| `addons/drawing/` | The render-and-look loop: `frontend.py`, `matplotlib.py` (PNG), `pymupdf.py` (**vector PDF**), `config.py`, `json.py` |
| `layouts/` | Modelspace / **paperspace** / layout = A3 sheet + viewport scale (the 1:200 question) |
| `colors.py` | **ACI colors** (the "yellow dimensions = ACI 2" gotcha) |
| `units.py`, `enums.py` | Drawing units (mm vs m), insert-units, enums |
| `math/`, `path/` | Geometry math, path objects (offset, projection helpers) |
| `graphicsfactory.py` | `add_line/add_lwpolyline/add_hatch/add_aligned_dim/...` — the authoring API surface |
| `tools/standards.py` | Built-in linetypes / text styles / dimstyles (templates to copy) |

**Common lookups**
```bash
grep -n "def add_" vendor/ezdxf/src/ezdxf/graphicsfactory.py        # authoring API
grep -rn "dimscale\|dimtxt\|dimasz" vendor/ezdxf/src/ezdxf/entities/dimstyle.py
sed -n '1,80p' vendor/ezdxf/src/ezdxf/addons/drawing/pymupdf.py      # how PDF export works
grep -rn "set_pos\|viewport\|scale" vendor/ezdxf/src/ezdxf/layouts/  # paperspace + scale
```

---

## QCAD — `vendor/qcad/`  (C++ core + ECMAScript app scripts)

QCAD's CLI tools (`dwg2pdf`, `dwg2svg`, `dwg2dwg`) are thin shell wrappers that run the **qcad binary
headless** against an app script. The real logic lives in the ECMAScript under `scripts/`, on top of
the C++ core in `src/`.

| Path | What's there |
|------|-------------|
| `scripts/File/Print/Print.js` | **Printing / PDF plot logic** — what `dwg2pdf` drives (page setup, scale, fit) |
| `scripts/Edit/DrawingPreferences/PageSettings/PageSettings.js` | Page/scale settings model |
| `scripts/ImportExport/` | DXF/DWG **import + export** (the DWG base-map → DXF path QCAD earns its place for) |
| `src/core/` | `RDocument`, `RS`, `RSettings`, units/colors/linetypes core |
| `src/io/` (+ `src/dxf`, dwg plugin) | File readers/writers (dxflib for DXF; DWG support) |
| `src/scripting/ecmaapi/` | C++↔ECMAScript binding (`RScriptHandlerEcma.cpp`) |
| `qcad.1`, `README.md`, root `CLAUDE.md` | QCAD's own usage notes (incl. a vendored CLAUDE.md) |

**Headless note (from the research, source-checkable):** the bundled CLI hardcodes `-platform xcb`
and crashes without an X server. Run the **Community** build with:
`dwg2pdf -platform offscreen -style plastique -a -o out.pdf in.dxf`. (The Pro *trial* injects a
15-second nag — use Community.)

```bash
grep -rn "QPrinter\|PdfFormat\|setPageSize\|exportFile" vendor/qcad/scripts/File/Print/Print.js
grep -rln "dwg\|DWG" vendor/qcad/scripts/ImportExport/ | head
```

---

## The FreeCAD bridge (where the geometry comes from)

ezdxf is a *drafting* engine — it does not project or section. The 2D line-work is produced in
FreeCAD (headless, no TechDraw page → no hang) and handed over as data:

- **Plans:** walk `obj.Shape.Wires`, drop Z, mm→m → polylines (the research's `extract.py`).
- **Sections:** `obj.Shape.section(plane)` → exact cut curves (you choose what to draw beyond = composition control).
- **Elevations:** `TechDraw.projectEx(shape, direction)` → **visible + hidden 2D edges** as geometry
  (the HLR engine `Draft Shape2DView` uses internally; runs headless without a page). See
  `vendor/FreeCAD/src/Mod/TechDraw/App/ProjectionAlgos.cpp` and
  `vendor/FreeCAD/src/Mod/Draft/draftobjects/shape2dview.py`.

So the pipeline is: FreeCAD (`projectEx` / `section` / wire-walk) → JSON edges by layer → ezdxf
(layers, lineweights, hatch, dims, title block, scale bar) → vector PDF (ezdxf `pymupdf` backend or
QCAD `dwg2pdf`). Avoid FreeCAD's Draft **DXF exporter** entirely (it explodes blocks / mangles layers).

---

## How subagents should use this

Dispatch source-reading subagents (read-only, cite `file:line`) for deep questions like: the exact
DIMSTYLE knobs for metre-unit text, the `pymupdf` PDF export options, paperspace viewport scale,
hatch boundary-path construction, or QCAD's print scale handling. Pin claims to the vendored source,
not memory. Same discipline as `freecad-source.md`.
