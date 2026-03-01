# Swedish Building Regulations — Structural Rules (EKS)

Last scraped: 2026-03-01
Sources: EKS — Boverkets konstruktionsregler, BFS 2011:10
PBL kunskapsbanken:
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-konstruktionsregler/overgripande-bestammelser/indelning-i-sakerhetsklasser/
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-konstruktionsregler/overgripande-bestammelser/nationella-val-i-eks/

> EKS = Boverkets konstruktionsregler (BFS 2011:10)
> EKS makes Sweden's nationally determined parameters (NDP) to the Eurocodes (EN 1990–1999)

---

## Safety Classes (Säkerhetsklasser) — EKS Avdelning A, 13 §

| Class | Risk level | Typical structural elements |
|-------|-----------|----------------------------|
| **SK1** | Low risk for personal injury | Slabs on ground (platta på mark), small rarely-occupied buildings |
| **SK2** | Moderate risk for personal injury | Floor slabs (bjälklag), roof structures with small spans |
| **SK3** | High risk for serious personal injury | Beams with large spans, columns, stabilizing elements (lift shafts/trapphus, wall panels) |

**Rule**: Safety class determines partial factors (γ) for load combinations and material resistances.

### Practical SK selection guide

| Building type | Typical SK by element | Notes |
|--------------|----------------------|-------|
| Single-family house (villa) | Floor slabs: **SK2**; Columns/walls (primary): **SK3** | |
| Multi-storey residential (flerbostadshus) | All floor slabs: **SK2**; All primary stabilizing elements: **SK3** | Stabilizing elements = shear walls, cores, columns |
| Industrial hall, low occupancy | Ground slab: **SK1**; Roof structure: **SK2** | |
| Foundations / piles | Follows superstructure SK; often **SK3** | Per EKS Avdelning I |

> All primary stabilizing elements (stommens stabiliserande delar) are always SK3 per EKS Avdelning A.

---

## Eurocode Structure with Swedish National Annexes (EKS)

EKS is organized into Avdelningar (divisions) corresponding to each Eurocode:

| EKS Division | Eurocode | Subject |
|-------------|----------|---------|
| **Avdelning A** | General / EKS overarching | Safety classes, general rules, definitions |
| **Avdelning B** | SS-EN 1990 | Basis of structural design (fundamental design, load combinations) |
| **Avdelning C** | SS-EN 1991 | Actions on structures — personnel, wind, snow, fire, accidental |
| **Avdelning D** | SS-EN 1992 | Concrete structures |
| **Avdelning E** | SS-EN 1993 | Steel structures |
| **Avdelning F** | SS-EN 1994 | Composite steel-concrete structures |
| **Avdelning G** | SS-EN 1995 | Timber structures |
| **Avdelning H** | SS-EN 1996 | Masonry structures |
| **Avdelning I** | SS-EN 1997 | Geotechnical design |
| **Avdelning J** | SS-EN 1999 | Aluminium structures |

> **Note**: Seismic Eurocode (SS-EN 1998) is NOT incorporated into EKS — Sweden's seismicity is generally low enough that it is handled separately or not required.

---

## Selected National Values (Nationella val) — EKS

| Parameter | Category | Swedish value | Notes |
|-----------|----------|--------------|-------|
| Floor live load — residential | Category A | qk = **1,5 kN/m²**, Qk = **2,0 kN** | Avdelning C (EN 1991-1-1) |
| Floor live load — office | Category B | qk = **2,5 kN/m²**, Qk = **3,5 kN** | Avdelning C |
| Floor live load — assembly areas | Category C1–C3 | qk = **3,0–5,0 kN/m²** | Avdelning C; sub-category dependent |
| Floor live load — storage | Category E1 | qk = **5,0 kN/m²**, Qk = **7,0 kN** | Avdelning C |
| Roof live load (inaccessible) | Category H | qk = **0,5 kN/m²** | Avdelning C |

---

## Key EKS Load Categories (Avdelning C — EN 1991-1-1)

| Category | Use | Notes |
|----------|-----|-------|
| A | Residential, domestic | — |
| B | Office | — |
| C | Assembly areas | Sub-categories C1–C5 |
| D | Shopping | — |
| E | Storage | E1: general storage, E2: industrial |
| F/G | Vehicle areas | F: light, G: heavy |
| H | Roofs | Accessible vs inaccessible |

---

## Snow Loads (Avdelning C — EN 1991-1-3)

Sweden has nationally determined snow load maps per EKS. Values vary significantly by geographic zone:
- Southern Sweden (Malmö/Gothenburg region): sk ≈ 1.0–1.5 kN/m²
- Central Sweden (Stockholm): sk ≈ 1.5–2.0 kN/m²
- Northern Sweden: sk = 2.5–5.5+ kN/m²
(Use EKS Avdelning C national annexes and Boverket's snow load maps for exact values by location)

---

## Wind Loads (Avdelning C — EN 1991-1-4)

Swedish national vb,0 (basic wind velocity):
- Most of Sweden: vb,0 = 24–26 m/s
- Coastal/exposed areas: higher values per national map
(Use EKS Avdelning C and Swedish wind map)

---

## Consequence Classes (Konsekvensklasser) — EN 1990

Related to but distinct from EKS safety classes:

| CC | Description | Relation to SK |
|----|-------------|---------------|
| CC1 | Low consequence | Correlates to SK1 |
| CC2 | Medium consequence | Correlates to SK2 |
| CC3 | High consequence | Correlates to SK3 |

---

## Geotechnical Design — Avdelning I (EN 1997)

| Geotechnical Category | Use |
|----------------------|-----|
| GC1 | Simple foundations, low risk |
| GC2 | Most conventional structures |
| GC3 | Complex geotechnics, high risk |

---

## Notes

- EKS is updated periodically; current version BFS 2011:10 with amendments
- All structural calculations for building permits must reference EKS + relevant EN standards
- SK3 applies to all primary stabilizing elements (stabiliserar stommen) — typically applies to all columns and shear walls in multi-storey buildings
- For timber frame construction: SS-EN 1995 (Avdelning G) + Swedish national annex for moisture/climate class
