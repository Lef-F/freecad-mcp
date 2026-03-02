#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["trimesh", "numpy"]
# ///
"""
Export visible FreeCAD objects to a clean GLB/glTF file.

Connects to a running FreeCAD instance via XML-RPC, exports all visible
objects with colors via ImportGui.export(), then cleans up the result:
  1. Remove duplicate subtrees (objects exported both in groups and flat)
  2. Strip alpha-0 (invisible) mesh primitives
  3. Merge duplicate materials
  4. Fix coplanar Z-fighting (offset overlapping surfaces)

Usage:
    uv run export_glb.py [--output PATH] [--format gltf|glb]

The script requires FreeCAD to be running with the MCP addon's RPC server
started (port 9875).
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import textwrap
import xmlrpc.client
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# FreeCAD RPC connection
# ---------------------------------------------------------------------------

RPC_URL = "http://127.0.0.1:9875"


def connect() -> xmlrpc.client.ServerProxy:
    proxy = xmlrpc.client.ServerProxy(RPC_URL)
    try:
        proxy.ping()
    except (ConnectionRefusedError, OSError):
        print("Error: Cannot connect to FreeCAD RPC server on port 9875.")
        print("Make sure FreeCAD is running and the MCP addon RPC server is started.")
        sys.exit(1)
    return proxy


def execute_code(proxy: xmlrpc.client.ServerProxy, code: str) -> str:
    """Run Python code inside FreeCAD and return the printed output."""
    result = proxy.execute_code(code)
    if isinstance(result, dict):
        if not result.get("success", False):
            print(f"FreeCAD error: {result.get('error', 'unknown')}")
            sys.exit(1)
        # Output is in 'message' field, after "Output: " prefix
        msg = result.get("message", "")
        marker = "Output: "
        idx = msg.find(marker)
        if idx >= 0:
            return msg[idx + len(marker) :]
        return msg
    return str(result)


# ---------------------------------------------------------------------------
# FreeCAD export
# ---------------------------------------------------------------------------


FREECAD_EXPORT_SCRIPT = '''\
import FreeCAD
import FreeCADGui
import ImportGui

doc = FreeCAD.ActiveDocument
if doc is None:
    print("ERROR:No active document")
else:
    # Noise types that never carry exportable geometry
    NOISE = {
        "App::Origin", "App::Line", "App::Plane", "App::OriginFeature",
        "Sketcher::SketchObject", "Image::ImagePlane",
        "TechDraw::DrawPage", "TechDraw::DrawViewPart",
        "TechDraw::DrawViewSection", "TechDraw::DrawViewDimension",
        "Part::Part2DObjectPython",
    }

    def is_visible(obj):
        return (hasattr(obj, "ViewObject")
                and obj.ViewObject.Visibility)

    def has_real_shape(obj):
        """Check if the object has exportable geometry (Part shape or Mesh)."""
        if hasattr(obj, "Shape") and not obj.Shape.isNull() and obj.Shape.Volume > 0:
            return True
        # Mesh::Feature objects store geometry in obj.Mesh, not obj.Shape
        if hasattr(obj, "Mesh") and obj.Mesh.CountPoints > 0:
            return True
        return False

    def is_final(obj):
        """Check if the object is marked as Final via MCP_Role."""
        return getattr(obj, "MCP_Role", "") == "Final"

    def collect_exportable(obj, depth=0):
        """Recursively collect objects marked MCP_Role=Final.

        Strategy: dive to leaf nodes first.
        - If it's noise (Origin, Sketch, etc.) -> skip
        - If it's a PartDesign::Body with MCP_Role=Final -> export it,
          don't recurse into child features
        - If it has Group children -> recurse into them
          - Include App::Part containers if they have Final descendants
            (App::Part carries placement transforms)
        - If it's a leaf with MCP_Role=Final and a real shape -> export it
        """
        if obj.TypeId in NOISE:
            return []

        prefix = "  " * depth

        # PartDesign::Body — final object whose shape is the Tip.
        # Never recurse into its features (Pad, Pocket, etc.)
        if obj.TypeId == "PartDesign::Body":
            if is_final(obj) and has_real_shape(obj):
                print("%s+ %s (%s)" % (prefix, obj.Label, obj.TypeId))
                return [obj]
            return []

        # Container with children -> recurse
        children = getattr(obj, "Group", None)
        if children:
            child_results = []
            for child in children:
                child_results.extend(collect_exportable(child, depth + 1))

            # App::Part carries placement transforms for its children.
            # Include it so the OCAF exporter preserves the hierarchy.
            if obj.TypeId == "App::Part" and child_results:
                print("%s+ %s (%s) [container with transform]" % (prefix, obj.Label, obj.TypeId))
                return [obj] + child_results

            # Plain groups have no transform — just return children
            return child_results

        # Leaf object with MCP_Role=Final and a real shape -> export
        if is_final(obj) and has_real_shape(obj):
            print("%s+ %s (%s)" % (prefix, obj.Label, obj.TypeId))
            return [obj]

        return []

    # Find top-level objects (not inside any group)
    all_grouped = set()
    for obj in doc.Objects:
        for child in getattr(obj, "Group", []):
            all_grouped.add(child.Name)

    top_level = [obj for obj in doc.Objects if obj.Name not in all_grouped]

    visible = []
    print("Scanning object tree...")
    for obj in top_level:
        visible.extend(collect_exportable(obj))

    # Deduplicate (same object might appear via multiple paths)
    seen = set()
    unique = []
    for obj in visible:
        if obj.Name not in seen:
            seen.add(obj.Name)
            unique.append(obj)
    visible = unique

    # Remove source objects that are already included via their Array/Pattern
    array_sources = set()
    for obj in visible:
        base = getattr(obj, "Base", None)
        if base is not None:
            array_sources.add(base.Name)
        source = getattr(obj, "SourceObject", None)
        if source is not None:
            array_sources.add(source.Name)
    if array_sources:
        before = len(visible)
        visible = [o for o in visible if o.Name not in array_sources]
        print("Removed %d array source objects: %s" % (before - len(visible), array_sources))

    # Convert Mesh::Feature objects to temporary Part::Feature objects.
    # FreeCAD's OCAF glTF exporter only handles Part::Feature — it silently
    # skips Mesh::Feature objects.  We create temporary conversions, export,
    # then delete them.
    import Part as PartMod
    temp_objects = []
    for i, obj in enumerate(visible):
        if obj.TypeId != "Mesh::Feature":
            continue
        verts, facets = obj.Mesh.Topology
        if not verts or not facets:
            continue
        shape = PartMod.Shape()
        shape.makeShapeFromMesh((verts, facets), 0.1, True)
        tmp_name = "_tmp_mesh2part_%s" % obj.Name
        tmp_obj = doc.addObject("Part::Feature", tmp_name)
        tmp_obj.Shape = shape
        tmp_obj.Placement = obj.Placement
        # Copy color and transparency from original mesh
        if hasattr(obj, "ViewObject"):
            try:
                if hasattr(obj.ViewObject, "ShapeColor"):
                    tmp_obj.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
                if hasattr(obj.ViewObject, "Transparency"):
                    tmp_obj.ViewObject.Transparency = obj.ViewObject.Transparency
            except Exception:
                pass
        temp_objects.append(tmp_name)
        visible[i] = tmp_obj
        print("  Converted Mesh::Feature '%s' -> Part::Feature '%s'" % (obj.Label, tmp_name))

    if temp_objects:
        doc.recompute()

    print("\\nExporting %d objects..." % len(visible))

    if visible:
        ImportGui.export(visible, "__OUTPUT_PATH__")
        import os
        size = os.path.getsize("__OUTPUT_PATH__")
        print("Exported: %d bytes" % size)
    else:
        print("ERROR:No visible objects to export")

    # Clean up temporary conversion objects
    for name in temp_objects:
        doc.removeObject(name)
    if temp_objects:
        doc.recompute()
        print("Cleaned up %d temporary conversion objects" % len(temp_objects))
'''


def export_from_freecad(proxy: xmlrpc.client.ServerProxy, tmp_path: str) -> str:
    """Export visible objects from FreeCAD to a temporary glTF file."""
    code = FREECAD_EXPORT_SCRIPT.replace("__OUTPUT_PATH__", tmp_path)
    output = execute_code(proxy, code)
    print(output)
    if "ERROR:" in output:
        sys.exit(1)
    return tmp_path


# ---------------------------------------------------------------------------
# glTF cleanup pipeline
# ---------------------------------------------------------------------------


def load_gltf(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_gltf(g: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(g, f, separators=(",", ":"))


def collect_mesh_names(
    nodes: list, meshes: list, node_idx: int, visited: set | None = None
) -> set[str]:
    """Recursively collect all mesh names under a node."""
    if visited is None:
        visited = set()
    if node_idx in visited:
        return set()
    visited.add(node_idx)
    names = set()
    node = nodes[node_idx]
    if "mesh" in node:
        names.add(meshes[node["mesh"]].get("name", f"mesh_{node['mesh']}"))
    for c in node.get("children", []):
        names.update(collect_mesh_names(nodes, meshes, c, visited))
    return names


def dedup_root_children(g: dict) -> int:
    """Remove root children whose meshes are already in other subtrees.

    FreeCAD's OCAF exporter often creates both a grouped hierarchy AND
    flat copies of the same objects at the root level.  The flat copies
    lack the parent App::Part transform, causing wrong placement.

    For each root child, if its entire mesh set is a subset of some
    other root child's mesh set, it's a duplicate and gets removed.
    """
    nodes = g["nodes"]
    meshes = g["meshes"]
    scene_root_idx = g["scenes"][0]["nodes"][0]
    root = nodes[scene_root_idx]
    children = root.get("children", [])

    if len(children) < 2:
        return 0

    # Compute mesh name set for each root child
    child_meshes = {c: collect_mesh_names(nodes, meshes, c) for c in children}

    # A child is a duplicate if its meshes are a proper subset of (or equal
    # to) another child's meshes AND that other child has strictly more meshes.
    # When two children have identical mesh sets, prefer the one that carries
    # a transform (nested under a named parent node with translation/matrix).
    remove = set()
    for c in children:
        if not child_meshes[c]:
            continue
        for other in children:
            if other == c or other in remove:
                continue
            if child_meshes[c].issubset(child_meshes[other]):
                if len(child_meshes[other]) > len(child_meshes[c]):
                    # c's meshes are fully contained in a larger subtree
                    remove.add(c)
                    break
                # Same size — keep the one with a transform
                other_node = nodes[other]
                c_node = nodes[c]
                other_has_t = "translation" in other_node or "matrix" in other_node
                c_has_t = "translation" in c_node or "matrix" in c_node
                if other_has_t and not c_has_t:
                    remove.add(c)
                    break

    root["children"] = [c for c in children if c not in remove]
    return len(remove)


def strip_alpha_zero(g: dict) -> int:
    """Remove mesh primitives that use fully transparent materials."""
    materials = g.get("materials", [])
    meshes = g.get("meshes", [])
    removed = 0
    for mesh in meshes:
        prims = mesh.get("primitives", [])
        clean = []
        for prim in prims:
            mat_idx = prim.get("material")
            if mat_idx is not None and mat_idx < len(materials):
                mat = materials[mat_idx]
                pbr = mat.get("pbrMetallicRoughness", {})
                color = pbr.get("baseColorFactor", [1, 1, 1, 1])
                if color[3] < 0.01:
                    removed += 1
                    continue
            clean.append(prim)
        mesh["primitives"] = clean
    return removed


def merge_duplicate_materials(g: dict) -> int:
    """Merge materials with identical colors and remap references."""
    materials = g.get("materials", [])
    meshes = g.get("meshes", [])

    color_to_first: dict[tuple, int] = {}
    remap: dict[int, int] = {}
    for i, mat in enumerate(materials):
        pbr = mat.get("pbrMetallicRoughness", {})
        color = tuple(round(c, 6) for c in pbr.get("baseColorFactor", [1, 1, 1, 1]))
        key = (color, mat.get("alphaMode", "OPAQUE"))
        if key in color_to_first:
            remap[i] = color_to_first[key]
        else:
            color_to_first[key] = i

    remapped = 0
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            if prim.get("material") in remap:
                prim["material"] = remap[prim["material"]]
                remapped += 1

    return remapped


def count_triangles(g: dict) -> int:
    """Count total triangles in the active scene graph."""
    nodes = g["nodes"]
    meshes = g["meshes"]
    accessors = g.get("accessors", [])
    scene_root = g["scenes"][0]["nodes"][0]

    def _count(idx: int, visited: set) -> int:
        if idx in visited:
            return 0
        visited.add(idx)
        total = 0
        node = nodes[idx]
        if "mesh" in node:
            for prim in meshes[node["mesh"]].get("primitives", []):
                acc_idx = prim.get("indices")
                if acc_idx is not None and acc_idx < len(accessors):
                    total += accessors[acc_idx].get("count", 0) // 3
        for c in node.get("children", []):
            total += _count(c, visited)
        return total

    return _count(scene_root, set())


# ---------------------------------------------------------------------------
# Geometric cleanup (trimesh-based)
# ---------------------------------------------------------------------------


def _get_world_meshes(scene) -> list[dict]:
    """Extract world-space meshes from a trimesh Scene with metadata."""
    meshes = []
    for node_name in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node_name]
        mesh = scene.geometry[geom_name].copy()
        mesh.apply_transform(transform)
        meshes.append(
            {
                "node": node_name,
                "geom": geom_name,
                "mesh": mesh,
            }
        )
    return meshes


def _build_json_maps(g: dict) -> tuple[dict[str, int], dict[int, list[int]]]:
    """Build mesh_name -> mesh_index and mesh_index -> [node_indices] maps."""
    mesh_name_to_idx: dict[str, int] = {}
    for i, m in enumerate(g.get("meshes", [])):
        name = m.get("name", "")
        if name:
            mesh_name_to_idx[name] = i

    mesh_to_nodes: dict[int, list[int]] = {}
    for i, node in enumerate(g.get("nodes", [])):
        if "mesh" in node:
            mesh_to_nodes.setdefault(node["mesh"], []).append(i)

    return mesh_name_to_idx, mesh_to_nodes


def _remove_node_from_parents(g: dict, node_idx: int) -> bool:
    """Remove a node index from all parent children lists. Returns True if found."""
    removed = False
    for node in g["nodes"]:
        children = node.get("children", [])
        if node_idx in children:
            children.remove(node_idx)
            removed = True
    return removed


def fix_coplanar_zfighting(g: dict, scene) -> int:
    """Detect coplanar mesh pairs and offset one to prevent Z-fighting.

    For each pair of meshes with overlapping AABBs, finds faces within
    the overlap region that have parallel normals at the same plane
    distance. Only faces spatially within the overlap box are counted,
    preventing false positives from distant faces at the same height.

    If the coplanar area is significant (>10% of the smaller mesh),
    the smaller mesh gets a 0.5mm offset along the shared normal.
    """
    world_meshes = _get_world_meshes(scene)
    mesh_name_to_idx, mesh_to_nodes = _build_json_maps(g)

    # Deduplicate by geometry name
    unique = {}
    for m in world_meshes:
        if m["geom"] not in unique:
            unique[m["geom"]] = m
    mesh_list = list(unique.values())

    already_offset: set[str] = set()
    n_fixed = 0

    for i, ma_info in enumerate(mesh_list):
        ma = ma_info["mesh"]
        if len(ma.faces) == 0:
            continue
        for mb_info in mesh_list[i + 1 :]:
            mb = mb_info["mesh"]
            if len(mb.faces) == 0:
                continue

            # AABB overlap check
            a_min, a_max = ma.bounds
            b_min, b_max = mb.bounds
            if not (np.all(a_min <= b_max) and np.all(b_min <= a_max)):
                continue

            # Compute the overlap AABB
            overlap_min = np.maximum(a_min, b_min)
            overlap_max = np.minimum(a_max, b_max)

            na = ma.face_normals
            nb = mb.face_normals
            ca = ma.triangles_center
            cb = mb.triangles_center
            aa = ma.area_faces

            coplanar_area = 0.0
            coplanar_normal = None

            # Check each cardinal direction (+X, -X, +Y, -Y, +Z, -Z)
            for axis in range(3):
                other_axes = [a for a in range(3) if a != axis]
                for sign in [1.0, -1.0]:
                    # A faces aligned with this direction
                    mask_a = np.abs(na[:, axis] - sign) < 0.01
                    if not mask_a.any():
                        continue

                    # Filter to A faces within the overlap box (on wide axes)
                    a_idx = np.where(mask_a)[0]
                    in_box_a = np.ones(len(a_idx), dtype=bool)
                    for oa in other_axes:
                        in_box_a &= ca[a_idx, oa] >= overlap_min[oa]
                        in_box_a &= ca[a_idx, oa] <= overlap_max[oa]
                    a_idx = a_idx[in_box_a]
                    if len(a_idx) == 0:
                        continue

                    # B faces aligned (same or opposite)
                    mask_b_same = np.abs(nb[:, axis] - sign) < 0.01
                    mask_b_opp = np.abs(nb[:, axis] + sign) < 0.01
                    mask_b_any = mask_b_same | mask_b_opp
                    if not mask_b_any.any():
                        continue

                    # Filter to B faces within the overlap box
                    b_idx = np.where(mask_b_any)[0]
                    in_box_b = np.ones(len(b_idx), dtype=bool)
                    for oa in other_axes:
                        in_box_b &= cb[b_idx, oa] >= overlap_min[oa]
                        in_box_b &= cb[b_idx, oa] <= overlap_max[oa]
                    b_idx = b_idx[in_box_b]
                    if len(b_idx) == 0:
                        continue

                    # Plane distances along the normal axis
                    da = ca[a_idx, axis]
                    db = cb[b_idx, axis]

                    # Match A faces to B faces at same plane distance
                    for j, d_a in enumerate(da):
                        if np.any(np.abs(db - d_a) < 0.001):
                            coplanar_area += aa[a_idx[j]]
                            if coplanar_normal is None:
                                coplanar_normal = np.zeros(3)
                                coplanar_normal[axis] = sign

            # Only fix if coplanar area is significant
            smaller_info = ma_info if ma.area < mb.area else mb_info
            smaller_mesh = ma if ma.area < mb.area else mb
            larger_info = mb_info if smaller_info is ma_info else ma_info

            min_threshold = smaller_mesh.area * 0.10
            if coplanar_area < min_threshold or coplanar_normal is None:
                continue

            if smaller_info["geom"] in already_offset:
                continue

            mesh_idx = mesh_name_to_idx.get(smaller_info["geom"])
            if mesh_idx is None:
                continue

            # Apply 0.5mm offset along the coplanar normal
            offset = (coplanar_normal * 0.0005).tolist()
            for ni in mesh_to_nodes.get(mesh_idx, []):
                node = g["nodes"][ni]
                t = node.get("translation", [0, 0, 0])
                node["translation"] = [t[k] + offset[k] for k in range(3)]

            already_offset.add(smaller_info["geom"])
            n_fixed += 1
            axis_name = "XYZ"[int(np.argmax(np.abs(coplanar_normal)))]
            pct = coplanar_area / smaller_mesh.area * 100
            print(
                f"    {smaller_info['geom']} vs {larger_info['geom']}: "
                f"{pct:.0f}% coplanar on {axis_name}"
            )

    return n_fixed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def center_model_at_origin(g: dict) -> None:
    """Shift the root node so the model's bounding box center is at the origin.

    Computes the bounding box from all POSITION accessors, then adds a
    translation to the scene root node to center everything.
    """
    accessors = g.get("accessors", [])

    # Find min/max from all POSITION accessors
    gmin = [float("inf")] * 3
    gmax = [float("-inf")] * 3
    found = False
    for acc in accessors:
        if acc.get("type") == "VEC3" and "min" in acc and "max" in acc:
            amin = acc["min"]
            amax = acc["max"]
            # Only consider accessors that look like positions (have reasonable range)
            for i in range(3):
                if amin[i] < gmin[i]:
                    gmin[i] = amin[i]
                if amax[i] > gmax[i]:
                    gmax[i] = amax[i]
            found = True

    if not found:
        print("Center: no position data found, skipping")
        return

    center = [(gmin[i] + gmax[i]) / 2 for i in range(3)]
    # Don't shift Y (up axis) to center — shift so bottom sits at Y=0
    ground_offset = -gmin[1]  # Move bottom to Y=0 (Y is up in glTF)
    shift = [-center[0], ground_offset, -center[2]]

    scene_root_idx = g["scenes"][0]["nodes"][0]
    root = g["nodes"][scene_root_idx]
    existing = root.get("translation", [0, 0, 0])
    root["translation"] = [existing[i] + shift[i] for i in range(3)]
    print(f"Center: shifted by [{shift[0]:.4f}, {shift[1]:.4f}, {shift[2]:.4f}]")
    print(
        f"  BBox was: X[{gmin[0]:.4f}, {gmax[0]:.4f}] "
        f"Y[{gmin[1]:.4f}, {gmax[1]:.4f}] Z[{gmin[2]:.4f}, {gmax[2]:.4f}]"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Export visible FreeCAD objects to clean glTF/GLB"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: web-export/public/exports/<doc_name>.gltf)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["gltf", "glb"],
        default="gltf",
        help="Output format (default: gltf)",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip FreeCAD export, process existing file at --output path",
    )
    args = parser.parse_args()

    ext = f".{args.format}"

    if args.skip_export and args.output:
        gltf_path = args.output
        print(f"Processing existing file: {gltf_path}")
    else:
        print("Connecting to FreeCAD...")
        proxy = connect()

        doc_name = execute_code(
            proxy,
            textwrap.dedent("""\
            import FreeCAD
            doc = FreeCAD.ActiveDocument
            print(doc.Name if doc else "NONE")
        """),
        ).strip()

        if doc_name == "NONE":
            print("Error: No active document in FreeCAD")
            sys.exit(1)
        print(f"Active document: {doc_name}")

        if args.output:
            out_path = args.output
        else:
            exports_dir = Path(__file__).parent / "public" / "exports"
            exports_dir.mkdir(exist_ok=True)
            out_path = str(exports_dir / f"{doc_name}{ext}")

        tmp_gltf = os.path.join(tempfile.gettempdir(), f"{doc_name}_export.gltf")
        export_from_freecad(proxy, tmp_gltf)
        gltf_path = tmp_gltf

    # Load and clean
    print("\n--- Cleanup pipeline ---")
    g = load_gltf(gltf_path)

    tris_before = count_triangles(g)

    n_dedup = dedup_root_children(g)
    print(f"Dedup: removed {n_dedup} duplicate subtrees")

    n_alpha = strip_alpha_zero(g)
    print(f"Alpha-0: removed {n_alpha} invisible primitives")

    n_mat = merge_duplicate_materials(g)
    print(f"Materials: remapped {n_mat} references")

    tris_after_json = count_triangles(g)
    print(
        f"Triangles: {tris_before:,} -> {tris_after_json:,} "
        f"({100 * tris_after_json / tris_before:.0f}%)"
    )

    # --- Geometric cleanup (trimesh) ---
    print("\n--- Geometric cleanup ---")

    # Save intermediate for trimesh to load
    intermediate_dir = tempfile.mkdtemp(prefix="export_intermediate_")
    intermediate_gltf = os.path.join(intermediate_dir, "intermediate.gltf")
    save_gltf(g, intermediate_gltf)
    bin_name = g.get("buffers", [{}])[0].get("uri", "")
    if bin_name:
        src_bin = os.path.join(os.path.dirname(gltf_path), bin_name)
        if os.path.exists(src_bin):
            shutil.copy2(src_bin, os.path.join(intermediate_dir, bin_name))

    import trimesh

    scene = trimesh.load(intermediate_gltf, force="scene", merge_primitives=True)
    shutil.rmtree(intermediate_dir, ignore_errors=True)

    n_coplanar = fix_coplanar_zfighting(g, scene)
    print(f"Coplanar: fixed {n_coplanar} Z-fighting pairs")

    center_model_at_origin(g)

    # Write output
    if not args.skip_export:
        save_gltf(g, out_path)
        if ext == ".gltf":
            bin_name = g.get("buffers", [{}])[0].get("uri", "")
            if bin_name:
                src_bin = os.path.join(os.path.dirname(gltf_path), bin_name)
                dst_bin = os.path.join(os.path.dirname(out_path), bin_name)
                if src_bin != dst_bin and os.path.exists(src_bin):
                    shutil.copy2(src_bin, dst_bin)

        # Write export-info.json alongside the model for the web viewer to read
        import datetime

        info = {
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(
                timespec="minutes"
            ),
            "model": os.path.basename(out_path),
            "triangles": count_triangles(g),
        }
        info_path = os.path.join(os.path.dirname(out_path), "export-info.json")
        with open(info_path, "w") as f:
            json.dump(info, f)

        print(f"\nWritten: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")
    else:
        save_gltf(g, gltf_path)
        print(f"\nUpdated: {gltf_path} ({os.path.getsize(gltf_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
