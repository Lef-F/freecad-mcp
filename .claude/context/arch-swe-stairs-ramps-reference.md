# Swedish Building Regulations — Stairs, Ramps & Circulation

Last scraped: 2026-03-01
Sources: BBR avsnitt 3:4, avsnitt 8:2, avsnitt 5 (trapphus)
PBL kunskapsbanken:
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-byggregler/brandskydd/trapphus/
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-byggregler/tillganglighet/ramper/

> **Transition note**: BBR applies during transition period — old rules valid for permits/notifications submitted before 1 July 2026.

---

## Protected Stairwells (Brandskyddade trapphus) — BBR 5:24–5:25

### Stairwell Classes

| Class | Description | Fire separation | Door requirement |
|-------|-------------|-----------------|-----------------|
| **Tr1** | Highest protection; air-lock (lobby) to exterior | **EI 60** separating structure | Tr1 → lobby: min **E 30-S200C**; lobby → dwelling/office: min **EI 60-S200C** |
| **Tr2** | Standard protected stairwell; connects only to Vk1/Vk3 via own hall | **EI 60** | ≤8 floors: min **EI 30-S200C**; 8–16 floors: **EI 60-S200C** |

### When stairwell class is required (BBR 5:321 & 5:322)

| Floors | Use class | Min stairwell | Notes |
|--------|-----------|---------------|-------|
| 2–8 | Vk3 (dwellings) | **Tr2** | Tr2 acceptable as sole egress |
| 2–8 | Vk1 (offices) | **Tr2** | Tr2 acceptable as sole egress |
| 8–16 | Vk3 | **Tr2** | |
| 8–16 | Vk1 | **Tr1** | |
| >16 | Any | Analytical + ≥1 **Tr1** | Analytical fire dimensioning required |

**BBR 5:321**: All occupied spaces must have ≥2 evacuation routes (general rule).

**BBR 5:322 exception**: Evacuation via window acceptable up to **23 m** above ground → no second stairwell required.

**BBR 5:256**: Pressurization of Tr1 stairwells verified per standard **SS-EN 12101-6**.

---

## Ramp Requirements — BBR 3:12 & 3:14

> Full ramp details (gradient, width, landings, edge guards, contrast marking) are in **[arch-swe-accessibility-reference.md](arch-swe-accessibility-reference.md)**. Key values for quick reference:

| Parameter | Value | BBR ref |
|-----------|-------|---------|
| Max gradient | **1:12** (8.3%) | BBR 3:122 |
| Min free width | **1,3 m** | BBR 3:122 |
| Landing length | **≥2,0 m** | BBR 3:122 |

---

## Circulation Spaces — BBR 8:34

| BBR ref | Requirement | Value | Type | Applies to |
|---------|-------------|-------|------|------------|
| BBR 8:34 | Free height in corridors, stairs, ramps | **≥2,00 m** | Krav | All buildings |

---

## Stair Geometry (General) — BBR avsnitt 8:232 & 8:2321

| Parameter | Value | BBR ref | Type |
|-----------|-------|---------|------|
| Sätthöjd (riser height) max — bostäder | **180 mm** | BBR 8:232 | Krav |
| Sätthöjd (riser height) max — other buildings | **200 mm** | BBR 8:232 | Krav |
| Stegdjup (tread depth) min — bostäder | **220 mm** | BBR 8:232 | Krav |
| Stegdjup (tread depth) min — other buildings | **200 mm** | BBR 8:232 | Krav |
| Comfort formula | **2 × sätthöjd + stegdjup = 580–650 mm** | BBR 8:232 | Allmänt råd |
| Min stair free width — bostäder | **900 mm** | BBR 8:232 | Krav |
| Min stair free width — public buildings | **1 200 mm** | BBR 8:232 | Krav |
| Handrail height (ledstång) | **0,90 m** at ramps and stairs | BBR 8:2321 | Krav |
| Balustrade height (räcke) at openings >0.5 m | **1,10 m** | BBR 8:2322 | Krav |
| Handrails required | Both sides if stair >500 mm wide | BBR 8:2321 | Krav |

> Note: Values from BBR training data — verify against current BBR avsnitt 8:232 for permit-stage calculations.

---

## Evacuation Routes — BBR 5:3

| Rule | Value/Condition | BBR ref |
|------|----------------|---------|
| Min 2 evacuation routes per fire compartment | General requirement | BBR 5:321 |
| Window evacuation allowed | Up to **23 m** above ground | BBR 5:322 |
| Max travel distance to stairwell (Vk3) | Typically **30 m** (per floor plan layout) | BBR 5:332 (general guidance) |

---

## Notes

- "Trapphus" (stairwell enclosure) must form its own fire compartment (brandcell)
- Pressurized stairwells (Tr1) prevent smoke ingress; verified by EN 12101-6 calculation
- Stair geometry rules (steg/steg-djup, min width) also in BBR 8:232
- For accessible stairs: min width 1,2 m; contrast nosing at each step recommended
