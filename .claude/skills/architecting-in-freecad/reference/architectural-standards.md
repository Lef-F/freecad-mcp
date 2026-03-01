# Architectural Standards Quick Reference

Standard dimensions, accessibility requirements, and structural rules of thumb for architectural design in FreeCAD. All values in millimeters unless noted.

> **Jurisdiction**: These are generic / international defaults (loosely US/IBC-based).
> **For Swedish projects**, BBR values take precedence. Key differences:
> - Ceiling heights: BBR 2400mm (bostäder), 2700mm (publika lokaler) — not the 2300mm here
> - Door clear passage: BBR 760mm interior, 800mm entrance — not ADA 815mm
> - Ramp gradient: same (1:12), but BBR adds 2m landing + 500mm max rise between landings
> - Daylight: BBR requires dagsljusfaktor ≥1.0% over half the assessed floor area
> - Fire: BBR uses Br0–Br3 + EI/REI classes, not the generic hour ratings below

### When to consult BBR files

Start with `.claude/context/bbr-reference.md` (index + quick-ref), then open the relevant topic file:

| Topic in this file | BBR context file |
|-------------------|-----------------|
| Room dimensions, ceiling heights | `arch-swe-room-dimensions-reference.md` |
| Accessibility, ramps, lifts | `arch-swe-accessibility-reference.md` |
| Doors, windows, daylight (DF%) | `arch-swe-doors-windows-daylight-reference.md` |
| Fire classes, stairwells, egress | `arch-swe-fire-safety-reference.md` |
| Stairs geometry, ramps, circulation | `arch-swe-stairs-ramps-reference.md` |
| Structural loads, safety classes (EKS) | `arch-swe-structural-reference.md` |
| Parking, site planning | `arch-swe-parking-reference.md` |

---

## Room Dimensions (Residential)

| Room | Minimum | Typical | Notes |
|------|---------|---------|-------|
| Bedroom (single) | 2100 × 3000 (7 m²) | 3000 × 3600 | No dimension < 2100mm. Egress window required. |
| Bedroom (master) | 2100 × 3000 | 4200 × 4800 | Walk-in closet typical |
| Living room | 3600 × 3600 (13 m²) | 4200 × 5400 | |
| Dining room | — | 3600 × 3600 | Allows 6-person table + circulation |
| Kitchen | No min area | 2400 × 3000 to 3000 × 3600 | 900mm counter height, 1000–1200mm between facing counters |
| Bathroom (full) | 1500 × 1200 (1.8 m²) | 1500 × 2400 | 1500mm for double vanity min |
| Bathroom (half) | 900 × 1500 | 1200 × 1500 | WC + basin only |
| Hallway/corridor | 900 min width | 1200 | ADA: 915mm min (see below) |
| Garage (single) | 3000 × 6000 | 3600 × 6600 | Min height 2400mm |
| Garage (double) | 5400 × 6000 | 6000 × 6600 | |

## Room Dimensions (Commercial)

| Room | Typical | Notes |
|------|---------|-------|
| Office (single) | 3000 × 3600 (10 m²) | |
| Open office | 6–8 m² per person | |
| Conference (8 person) | 4200 × 5400 | |
| Restroom stall | 900 × 1500 | ADA: 1500 × 1500 |
| Corridor (public) | 1500–1800 | Fire code: depends on occupancy |

---

## Ceiling Heights

| Space Type | Minimum | Typical |
|------------|---------|---------|
| Habitable rooms | 2300 (7'6") | 2400–2700 |
| Bathrooms, kitchens | 2100 (7'0") | 2400 |
| Basements (habitable) | 2100 | 2400 |
| Commercial | 2700 | 3000–3600 |
| Retail | 3000 | 3600–4500 |

---

## Floor-to-Floor Heights

| Building Type | Typical | Breakdown |
|---------------|---------|-----------|
| Residential | 2800–3000 | 2500 clear + 200 slab + 100 finish |
| Commercial office | 3600–4000 | 2700 clear + 400 structure + 300 services |
| Retail | 4000–5000 | Higher for display/HVAC |

---

## Door Dimensions

| Type | Width | Height | Notes |
|------|-------|--------|-------|
| Main entrance | 900–1000 | 2100 | Single leaf |
| Main entrance (double) | 1500–1800 | 2100 | Two leaves |
| Interior (standard) | 750–800 | 2000 | |
| Interior (ADA) | 900 (815 clear) | 2000 | 5 lbs max force, lever handle |
| Bathroom | 600–750 | 2000 | |
| Sliding (patio) | 1500–2400 | 2100 | |
| Garage | 2400–2700 | 2100–2300 | |

---

## Window Dimensions

| Type | Width | Height | Notes |
|------|-------|--------|-------|
| Standard casement | 600–1200 | 1000–1500 | |
| Picture window | 1200–2400 | 1200–1800 | Fixed, no opening |
| Bedroom (egress) | 500 min clear | 610 min clear | 5.7 sq ft opening, sill max 1120mm |
| Floor-to-ceiling | 900–2400 | 2100–2700 | |

**Standard sill heights**: 800–900mm (residential), 900mm (commercial), 0mm (floor-to-ceiling).

**Head height**: Typically aligns at 2100mm across all windows in a facade.

---

## Stair Dimensions

| Element | Residential | Commercial | ADA |
|---------|------------|------------|-----|
| Riser max | 190 (7.5") | 178 (7") | 178 |
| Tread min | 250 (10") | 280 (11") | 280 |
| Width min | 900 (36") | 1100 (44") | 915 (36") |
| Headroom min | 2000 (6'8") | 2000 | 2000 |
| Handrail height | 860–960 | 860–960 | 860–960 |

**Comfort formula**: `2 × riser + tread = 600–650mm`

**Step count**: `floor_to_floor / riser` (round to integer, adjust riser to fit exactly)

**Landing**: Required every 3700mm (12') vertical rise. Landing depth = stair width minimum.

---

## Accessibility (ADA / Universal Design)

### Circulation

| Element | Requirement |
|---------|------------|
| Corridor min width | 915mm (36") clear continuous |
| Passing space | 1525 × 1525mm (60" × 60") every 61m (200') |
| Wheelchair turning | 1525mm (60") diameter |
| Wheelchair space | 760 × 1220mm (30" × 48") clear floor |
| Door clear width | 815mm (32") minimum |
| Door threshold | 13mm (0.5") maximum |
| Door handle height | 860–1220mm (34"–48") above floor |

### Ramps

| Element | Requirement |
|---------|------------|
| Maximum slope | 1:12 (8.3%) |
| Maximum rise per run | 760mm (30") |
| Minimum width | 915mm (36") clear |
| Landing at direction change | 1525 × 1525mm (60" × 60") |
| Edge protection | Required (curb or rail) |

### Restrooms

| Element | Requirement |
|---------|------------|
| Accessible stall | 1525 × 1525mm (60" × 60") min |
| Grab bar height | 840–920mm (33"–36") |
| Lavatory height max | 865mm (34") |
| Mirror bottom max | 1015mm (40") |

---

## Wall Thicknesses

| Type | Thickness | Notes |
|------|-----------|-------|
| Exterior (masonry) | 200–300 | Load-bearing |
| Exterior (frame) | 150–200 | With cladding: add 50–100 |
| Interior (load-bearing) | 150–200 | |
| Interior (partition) | 75–100 | Non-structural |
| Interior (acoustic) | 150–200 | With insulation |
| Cavity wall | 250–300 | 100 brick + 50 cavity + 100 block |

---

## Structural Rules of Thumb

### Beams

| Material | Depth Rule | Notes |
|----------|-----------|-------|
| Steel (W-shape) | span / 24 | e.g., 7200mm span → 300mm deep beam |
| Concrete (rect) | span / 12–15 | Width = depth / 2–3 |
| Timber (joist) | span / 15–20 | |
| Glulam | span / 16–20 | |

### Slabs

| Type | Span:Depth Ratio | Notes |
|------|------------------|-------|
| Concrete (one-way) | 20:1 to 25:1 | e.g., 5000mm span → 200–250mm |
| Concrete (two-way) | 30:1 to 35:1 | |
| Post-tensioned | 40:1 to 45:1 | |

### Columns

| Material | Size Rule | Notes |
|----------|----------|-------|
| Concrete (1-2 story) | 225 × 225mm min | Increases with load |
| Steel | Per AISC tables | Typical: W200–W310 for 3-5 stories |
| Timber post | 150 × 150mm min | |
| Column spacing | 3000–6000mm | 4500–5400mm most common |

---

## Typical Building Envelopes

| Building Type | Footprint | Floors | Floor-to-Floor |
|---------------|-----------|--------|----------------|
| Single-family house | 80–200 m² | 1–2 | 2800–3000 |
| Townhouse | 50–80 m² per floor | 2–3 | 2800–3000 |
| Apartment building | 300–1000 m² per floor | 3–8 | 3000 |
| Small office | 200–500 m² per floor | 2–4 | 3600–4000 |
| Retail | 500–2000 m² | 1–2 | 4000–5000 |

---

## Fire Separation

| Condition | Requirement |
|-----------|------------|
| Between dwelling units | 1 hour fire-rated wall |
| Between floors | 1 hour fire-rated assembly |
| Corridor walls (commercial) | 1 hour fire-rated |
| Stairwell enclosure (≤3 stories) | 1 hour fire-rated |
| Stairwell enclosure (>3 stories) | 2 hour fire-rated |
| Distance to property line < 1.5m | 1 hour exterior wall |

---

## Parking

| Type | Stall Size | Aisle Width |
|------|-----------|-------------|
| Standard (90°) | 2500 × 5500 | 7200 (two-way) |
| Compact (90°) | 2400 × 4800 | 6600 |
| ADA accessible | 3600 × 5500 | 7200 |
| ADA van-accessible | 3600 × 5500 + 2400 aisle | 7200 |

**Ratio**: 1 stall per 30–50 m² gross floor area (varies by jurisdiction).
