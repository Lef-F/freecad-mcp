#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
"""
Spatial clustering of FreeCAD objects for reorganisation analysis.

Usage:
    uv run cluster_spatial.py <objects_spatial.json> [--eps 1500] [--skip-types Pad,Pocket]

Input JSON schema (one record per object):
    name, label, type, cx, cy, cz, xmin, xmax, ymin, ymax, zmin, zmax, in_group

Output:
    - Cluster summary table at multiple eps values
    - Detailed per-cluster object listing at chosen eps
    - Ungrouped objects report
"""
import json
import sys
import argparse
import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN

# ── CLI ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Spatial cluster analysis for FreeCAD objects")
parser.add_argument("input", help="Path to objects_spatial.json")
parser.add_argument("--eps", type=float, default=1500,
                    help="DBSCAN epsilon in mm for detailed output (default: 1500)")
parser.add_argument("--skip-types", default="SubShapeBinder,FeatureBase,Boolean,Pocket,Pad,LinearPattern,AdditiveLoft",
                    help="Comma-separated TypeId suffixes to exclude from clustering")
args = parser.parse_args()

# ── Load ─────────────────────────────────────────────────────────────────────

with open(args.input) as f:
    records = json.load(f)

skip = set(args.skip_types.split(","))
objs = [r for r in records if r["type"].split("::")[-1] not in skip]

print(f"Loaded {len(records)} objects, {len(objs)} after filtering internal PartDesign features\n")

# ── Cluster sweep ────────────────────────────────────────────────────────────

coords_xy = np.array([[r["cx"], r["cy"]] for r in objs])

print("eps (mm) → cluster count (XY only, Z ignored):")
for eps in [1000, 1500, 2500, 4000, 8000]:
    db = DBSCAN(eps=eps, min_samples=1).fit(coords_xy)
    n = len(set(db.labels_))
    bar = "█" * n
    print(f"  {eps:5.0f}mm  {n:3d} clusters  {bar}")

# ── Detailed output at chosen eps ─────────────────────────────────────────────

print(f"\n{'='*70}")
print(f"Detailed clustering at eps={args.eps:.0f}mm")
print(f"{'='*70}")

db = DBSCAN(eps=args.eps, min_samples=1).fit(coords_xy)
clusters: dict[int, list] = defaultdict(list)
for i, lbl in enumerate(db.labels_):
    clusters[lbl].append(objs[i])

for cid in sorted(clusters.keys()):
    members = clusters[cid]
    xs = [o["cx"] for o in members]
    ys = [o["cy"] for o in members]
    zs = [o["cz"] for o in members]
    print(f"\nCluster {cid}  ({len(members)} objects)")
    print(f"  XY centroid: ({np.mean(xs):.0f}, {np.mean(ys):.0f})  "
          f"Z: {min(zs):.0f} – {max(zs):.0f}")
    for o in sorted(members, key=lambda x: x["cz"]):
        grp = ", ".join(o["in_group"]) if o["in_group"] else "—"
        print(f"  z={o['cz']:7.0f}  {o['label']:45s}  [{grp}]")

# ── Ungrouped report ──────────────────────────────────────────────────────────

ungrouped = [o for o in records if not o["in_group"]]
if ungrouped:
    print(f"\n{'='*70}")
    print(f"UNGROUPED objects ({len(ungrouped)}) — not inside any group or App::Part:")
    print(f"{'='*70}")
    for o in sorted(ungrouped, key=lambda x: x["cz"]):
        print(f"  z={o['cz']:7.0f}  {o['label']:45s}  [{o['type']}]  name={o['name']}")
else:
    print("\n✓ No ungrouped objects.")

# ── Z-band summary ────────────────────────────────────────────────────────────

print(f"\n{'='*70}")
print("Z elevation bands (200mm buckets) — reveals vertical systems:")
print(f"{'='*70}")
band_size = 500
z_bands: dict[int, list] = defaultdict(list)
for o in objs:
    band = int(o["cz"] // band_size) * band_size
    z_bands[band].append(o["label"])

for band in sorted(z_bands.keys()):
    labels = z_bands[band]
    sample = ", ".join(labels[:4]) + ("…" if len(labels) > 4 else "")
    print(f"  Z {band:6.0f}–{band+band_size:<6.0f}  {len(labels):3d} objects  {sample}")
