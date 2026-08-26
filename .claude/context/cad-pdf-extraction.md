# Extracting Dimensions from PDF/DWG Technical Drawings

How to pull dimensions faithfully out of vendor, catalogue, and manufacturer technical
drawings (PDF, DWG, DXF) when modeling a real-world part. Every technique here was
verified in a real extraction where two independent methods cross-confirmed with zero
conflicts. The core rule: a number is not a dimension until you know which feature it
is attached to, and the text layer of a CAD-exported PDF can lie.

All examples use neutral placeholders. Never copy project names, manufacturer names,
model numbers, or session-specific dimensions into this file (see CLAUDE.md,
"Proprietary information stays in `.designs/`").

---

## Source Formats: Pick the Richest Input First

| Source | Fidelity | Path |
|--------|----------|------|
| DWG | Exact coordinates | ODA convert to DXF, read with ezdxf |
| DXF | Exact coordinates | Read with ezdxf directly |
| Vector PDF (CAD-exported) | Text layer + line geometry | pymupdf text/drawings, plus rendered-image vision |
| Scanned/raster PDF | Pixels only | Render at high dpi, vision path only |

If a DWG or DXF exists alongside the PDF, always process it too. Coordinates beat
pixel measurement every time.

---

## DWG Sources: ODA Convert, Then ezdxf

DWG is a closed format; convert to DXF first with the free ODA File Converter
(GUI app that also runs headless from the CLI):

```bash
# macOS. Args: <indir> <outdir> <out-version> <out-format> <recurse 0/1> <audit 0/1>
/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter \
  /path/to/dwg-dir /path/to/dxf-out ACAD2018 DXF 0 1
```

It converts every DWG in the input directory. Then dump the entities with ezdxf
(transient dep, per the uv rule):

```bash
uv run --with ezdxf python3 - <<'EOF'
import ezdxf
doc = ezdxf.readfile("/path/to/dxf-out/part_drawing.dxf")
msp = doc.modelspace()
print("INSUNITS:", doc.header.get("$INSUNITS", "unset"))
for e in msp:
    t = e.dxftype()
    if t == "LINE":
        print(t, e.dxf.start, e.dxf.end, "layer=", e.dxf.layer)
    elif t == "CIRCLE":
        print(t, "center=", e.dxf.center, "r=", e.dxf.radius)
    elif t == "ARC":
        print(t, "center=", e.dxf.center, "r=", e.dxf.radius,
              "angles=", e.dxf.start_angle, e.dxf.end_angle)
    elif t == "DIMENSION":
        print(t, "measurement=", e.get_measurement(), "text=", repr(e.dxf.text))
EOF
```

Two traps confirmed in practice:

- **DIMENSION entities can be degenerate**: `measurement` of `0.0` and text `'<>'`
  (the AutoCAD "use measured value" placeholder) with no usable geometry behind it.
  When that happens, ignore the DIMENSION entities and measure the LINE/CIRCLE/ARC
  coordinates directly; the drawn geometry in a DWG is usually exact.
- **`$INSUNITS` can lie.** Validate units against magnitudes: if a part you know is
  roughly hand-sized comes out 4 units long, the file is probably in metres or inches
  regardless of what the header says. Cross-check one known dimension before trusting
  the rest.

---

## PDF Rendering: Resolution and Rotation

Render pages at 300 dpi with pymupdf before any visual work:

```bash
uv run --with pymupdf --with pillow python3 - <<'EOF'
import fitz
from PIL import Image
doc = fitz.open("/path/to/vendor_drawing.pdf")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=300)
    pix.save(f"/tmp/page_{i}.png")
    # CAD PDFs are often rotated 90 deg on the page. Produce both rotations
    # and identify the upright one visually before doing anything else.
    img = Image.open(f"/tmp/page_{i}.png")
    img.rotate(90, expand=True).save(f"/tmp/page_{i}_rot90.png")
    img.rotate(-90, expand=True).save(f"/tmp/page_{i}_rot270.png")
EOF
```

Technical drawings are **frequently rotated 90 degrees** on the PDF page (landscape
sheet stored portrait). Do not attempt to read dimension labels from a sideways
render; pick the upright rotation first, then crop from that image.

---

## Vision Path: Crop and Magnify Every Label

Reading a full-page render at once produces misassigned dimensions. The reliable
procedure:

1. From the upright 300 dpi render, crop a region around **each** dimension label.
2. Magnify the crop 2x to 10x with `Image.resize(..., Image.LANCZOS)` until the
   digits, the leader line, and the extension lines are all unambiguous.
3. Only assign a number to a feature once you can see the **attachment points** of
   its extension/leader lines. A label floating near two candidate features is not
   assigned; crop tighter or wider until the lines settle it.

```python
crop = img.crop((x0, y0, x1, y1))
w, h = crop.size
crop.resize((w * 4, h * 4), Image.LANCZOS).save("/tmp/label_totalheight_4x.png")
```

Never assign a dimension you have not seen attached. This single rule prevents most
extraction errors.

---

## Vector-Text Path: Words, Bboxes, and Line Geometry

CAD-exported PDFs usually keep a real text layer plus vector line-work. That gives a
second, independent extraction channel:

```python
words = page.get_text("words")        # [(x0, y0, x1, y1, text, block, line, word), ...]
raw = page.get_text("rawdict")        # per-span font name, size, glyph bboxes
paths = page.get_drawings()           # dimension lines, extension lines, arrowheads
```

Method:

- Cluster the words spatially per drawing view (a sheet often carries several views;
  a label belongs to the view whose bbox contains it).
- From `get_drawings()`, collect line segments and the tiny filled triangles that are
  arrowheads. A dimension line is a segment terminated by two arrowheads with a text
  bbox near its midpoint.
- Pair each numeric label with its dimension line by proximity (nearest dimension-line
  midpoint to the label's bbox center), then map the extension-line endpoints back to
  the drawn feature. The endpoints give you pixel/point coordinates you can also use
  to verify the drawn length against the label.

This path yields coordinates, so it can measure undimensioned features the vision path
can only estimate.

---

## Danger: Cipher-Encoded Text Layers

Some CAD exporters embed **custom fonts whose glyph encoding is a shifted or permuted
alphabet**. Naive `get_text()` then returns strings that LOOK like plausible numbers
but are wrong; every digit may be off by a fixed shift. This is the most dangerous
failure mode in PDF extraction because nothing crashes and the output is well-formed.

Detection and decoding:

1. Suspect any nonstandard/embedded font name in `rawdict` spans, and any text-layer
   number that disagrees with the rendered image.
2. Derive the mapping **empirically**: find labels in the same font whose true value
   you can read visually on the render (title-block words, bilingual labels, a
   dimension you already confirmed), and align extracted glyphs to true characters.
3. In one observed case the mapping was: digit `d` encoded as `d+1`, with `9` wrapping
   to an apostrophe-like glyph; letters shifted with gaps; and an ordinary letter
   standing in for the diameter sign. Do not assume this exact cipher; re-derive it
   per document and per font.
4. Apply the decoded mapping to all spans in that font, then **visually confirm** a
   sample of decoded values against magnified crops.

Rule: never trust raw text-layer digits from an unknown CAD font until they are both
decoded and visually confirmed on the rendered drawing.

---

## Catalogue Drawings Are Often Not to Vertical Scale

Marketing/catalogue drawings exaggerate small members for legibility, usually on the
vertical axis, while the horizontal axis stays honest. Consequences:

- **Verify scale per segment**: for each labeled dimension, compute drawn length (in
  pixels or PDF points) divided by the label value. If the ratio is constant along one
  axis and wanders along the other, that other axis is distorted.
- **Labeled values always win.** Drawn geometry is only for shapes, proportions, and
  ratios of features that carry no label.
- When you must measure an undimensioned feature, prefer **horizontal** pixel
  measurements scaled by a horizontally-verified ratio.

---

## Sanity Closures: Dimension Chains Must Tile

Before accepting an extraction, check that the dimensions tile:

- Partial heights along one edge must sum to the labeled total height.
- A wall-offset plus a radius must equal the labeled depth to that feature's center.
- Left-to-right chained widths must sum to the overall width.

Run the arithmetic in a throwaway script, never in-head:

```bash
uv run python3 -c "parts=[120.0, 45.5, 34.5]; total=200.0; print(sum(parts), total, abs(sum(parts)-total) < 0.1)"
```

A chain that closes exactly is strong evidence the feature assignments are right. A
chain that misses by a member's thickness usually means a label was assigned to the
wrong edge (inside vs outside face); go back to the crop and re-check attachment.

---

## The Dual-Extractor Pattern (High-Stakes Extractions)

When the part will be manufactured or the model must match reality, do not rely on a
single reading. Dispatch **two independent subagents with deliberately different
methods**, then reconcile:

- **Agent A, vision-first**: renders, rotates, crops, magnifies; assigns every label
  by visible attachment; never reads the text layer.
- **Agent B, vector-first**: reads `get_text` words and `get_drawings` geometry (or
  DXF entities), pairs labels to dimension lines by coordinates; treats the render
  only as a final check.

Reconciliation rules:

- A value both paths agree on becomes a **fact**.
- Divergent estimates for **undimensioned** features resolve toward the
  vector-measured value (coordinates beat eyeballs).
- Any disagreement on a **labeled** value means at least one path misassigned;
  neither wins until the attachment is re-verified on a magnified crop.
- Record per-dimension confidence (both-paths / single-path / estimated) in the
  design's `.designs/<doc>/` notes so later sessions know what is solid.

This is cheap insurance against correlated misreads: two runs of the same method can
share a blind spot; two different methods rarely do.

---

## Drawing-vs-Drawing Conflicts: Ask With an Annotated PNG

Customer-supplied CAD sometimes disagrees with itself: two views on the same sheet (or
two sheets) give different values for the same length. **Never silently pick one.**

Produce an annotated PNG the customer can forward and answer definitively:

```bash
uv run --with ezdxf --with matplotlib python3 - <<'EOF'
import ezdxf, matplotlib.pyplot as plt
doc = ezdxf.readfile("/path/to/part_drawing.dxf")
fig, ax = plt.subplots(figsize=(14, 10))
for e in doc.modelspace().query("LINE"):
    ax.plot([e.dxf.start.x, e.dxf.end.x], [e.dxf.start.y, e.dxf.end.y],
            color="0.6", lw=0.7)
# Highlight the two conflicting features in distinct colors
ax.plot([xa0, xa1], [ya, ya], color="red", lw=2.5)
ax.annotate("", xy=(xa1, ya - 15), xytext=(xa0, ya - 15),
            arrowprops=dict(arrowstyle="<->", color="red"))
ax.text((xa0 + xa1) / 2, ya - 40, "View 1: length L1", color="red", ha="center")
# ... same for the second view's version of the feature, in blue ...
ax.text(0.02, 0.02,
        "Question: View 1 shows L1 for this edge, View 2 shows L2.\n"
        "Which value is correct for manufacturing?",
        transform=ax.transAxes, fontsize=11,
        bbox=dict(boxstyle="round", facecolor="lightyellow"))
ax.set_aspect("equal"); ax.axis("off")
fig.savefig("/tmp/conflict_question.png", dpi=200, bbox_inches="tight")
EOF
```

Highlight both conflicting features, add dimension arrows with the two competing
values, and include a plain-language question box. Park the modeling decision until
the answer comes back; note the open conflict in `.designs/<doc>/tasks.md`.

---

## Checklist

1. DWG/DXF available? Convert with ODA, dump entities with ezdxf, validate units
   against magnitudes.
2. Render the PDF at 300 dpi; find the upright rotation before reading anything.
3. Vision path: crop + magnify every label until attachments are unambiguous.
4. Vector path: text spans + drawing geometry, paired by proximity.
5. Unknown embedded font? Assume cipher until proven honest; decode empirically,
   confirm visually.
6. Check per-segment scale; trust labels, use geometry only for undimensioned shapes.
7. Close every dimension chain in a script.
8. High stakes: run the dual-extractor pattern and record per-dimension confidence.
9. Internal contradictions: annotated question PNG to the customer, decision parked.
