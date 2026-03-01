# Swedish Building Regulations — Fire Safety & Separation

Last scraped: 2026-03-01
Sources: BBR avsnitt 5, BFS 2011:6
PBL kunskapsbanken:
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-byggregler/brandskydd/
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-byggregler/brandskydd/byggnadsklass-och-verksamhetsklasser/
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-byggregler/brandskydd/brandklasserd-for-ytskikt/
- https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-byggregler/brandskydd/trapphus/

> **Transition note**: BBR applies during transition period — old rules valid for permits/notifications submitted before 1 July 2026.

---

## BBR Avsnitt 5 Structure

| Section | Subject |
|---------|---------|
| BBR 5:2 | Brandtekniska klasser och egenskaper (fire classes) |
| BBR 5:3 | Utrymning vid brand (evacuation) |
| BBR 5:4 | Eldstäder (hearths and fireplaces) |
| BBR 5:5 | Brandspridning inom byggnader (internal fire spread) |
| BBR 5:6 | Brandspridning mellan byggnader (≥8 m separation or fire construction) |
| BBR 5:7 | Räddningsinsatser (rescue access, FiRe brigade) |

---

## Building Classes (Byggnadsklasser) — BBR 5:22

| Class | Swedish name | Protection need | Typical buildings |
|-------|-------------|-----------------|-------------------|
| **Br0** | Br noll | Mycket stort skyddsbehov (very high) | High-rises, hospitals, special buildings |
| **Br1** | Br ett | Stort skyddsbehov (large) | Standard multi-storey flerbostadshus, offices >8 floors |
| **Br2** | Br två | Måttligt skyddsbehov (moderate) | Lower-rise residential/commercial |
| **Br3** | Br tre | Litet skyddsbehov (small) | Small single-family homes, minor buildings |

---

## Use Classes (Verksamhetsklasser) — BBR 5:21

| Class | Sub | Description | Users | Evacuation assumption |
|-------|-----|-------------|-------|----------------------|
| **Vk1** | — | Industry, offices, similar | Awake, good local knowledge | Can self-evacuate |
| **Vk2** | 2A | Assembly spaces | ≤150 persons, temporary visitors | Need guidance |
| **Vk2** | 2B | Large assembly spaces | >150 persons | Need guidance |
| **Vk2** | 2C | Large assembly + alcohol | >150 persons, alcohol served | Need extra assistance |
| **Vk3** | 3A | Normal dwellings, apartments | Familiar users, may be asleep | Need time to wake/orient |
| **Vk3** | 3B | Group housing (HVB, sheltered) | May need significant assistance | Need assistance |
| **Vk4** | — | Hotels, temporary accommodation | Unknown space, may be asleep | Need guidance |
| **Vk5** | 5A | Outpatient healthcare | Awake, some may need assistance | Limited self-evacuation |
| **Vk5** | 5B | Residential healthcare | May need evacuation assistance | Need assistance |
| **Vk5** | 5C | Hospital/intensive care | Cannot self-evacuate | Full assistance required |
| **Vk6** | — | High fire/explosion risk premises | Varies | Special fire risk |

---

## Reaction-to-Fire Classes (Brandklasser för ytskikt) — BBR 5:231

European classification system (EN 13501-1):

| Class | Description | Approx. old Swedish equiv. |
|-------|-------------|---------------------------|
| **A1** | Non-combustible, no contribution to fire | — |
| **A2** | Non-combustible, negligible contribution | — |
| **B** | Very limited fire contribution | Klass I |
| **C** | Limited fire contribution | Klass II |
| **D** | Acceptable fire contribution (incl. untreated wood) | Klass III |
| **E** | Acceptable fire contribution (short flame) | — |
| **F** | No performance determined | — |

### Smoke production suffix
| Code | Meaning |
|------|---------|
| **s1** | Very limited smoke production |
| **s2** | Limited smoke production |
| **s3** | No performance requirement |

### Flaming droplets/particles suffix
| Code | Meaning |
|------|---------|
| **d0** | No flaming droplets or particles |
| **d1** | Limited flaming droplets |
| **d2** | No performance requirement |

### Surface suffixes by application
| Suffix | Application | Example |
|--------|-------------|---------|
| *(none)* | Walls, ceilings | B-s1,d0 |
| **fl** | Floors | Cfl-s1 |
| **L** | Pipe insulation | CL-s3,d0 |
| **ca** | Cables | Dca-s2,d2 |

### Where classes apply
| BBR ref | Requirement | Applies to |
|---------|-------------|------------|
| BBR 5:231 | Wall/ceiling class per room type | All rooms |
| BBR 5:524 | Floor class required in egress routes and assembly spaces | Evacuation paths, Vk2 |
| BBR 5:525 | Pipe insulation class = wall/ceiling class of that space | All pipe insulation |
| BBR 5:527 | Cable fire class required in all buildings | All buildings |

---

## Fire Resistance Classes (Brandmotstånd)

Classes from EN 13501-2:

| Code | Meaning |
|------|---------|
| **R** | Load-bearing capacity (bärförmåga) |
| **E** | Integrity — smoke/flame tight (täthet) |
| **I** | Insulation — limits heat transfer (isolering) |
| **REI 60** | Load-bearing + integrity + insulation, 60 min |
| **EI 60** | Integrity + insulation, 60 min (non-load-bearing separation) |
| **EI 30** | Integrity + insulation, 30 min |
| **E 30** | Integrity only, 30 min |

### Door classifications (used in stairwell requirements)
| Code | Meaning |
|------|---------|
| **EI 60-S200C** | EI 60, smoke class S200, self-closing C |
| **EI 30-S200C** | EI 30, smoke class S200, self-closing |
| **E 30-S200C** | E 30 (integrity only), smoke class S200, self-closing |

---

## Fire Spread Between Buildings — BBR 5:6

| Rule | Value | Notes |
|------|-------|-------|
| Min separation between buildings | **≥8 m** | OR use fire-construction (brandskyddskonstruktion) |
| Fire construction alternative | EI 60 wall facing property boundary | |

---

## Notes

- Analytical fire dimensioning allowed as alternative to prescriptive rules (BBR 5:11)
- "Brandcell" = fire compartment; each dwelling must be its own fire compartment (Br1–Br3)
- Sprinkler systems can substitute for some prescriptive requirements
