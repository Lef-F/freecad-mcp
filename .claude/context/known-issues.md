# Known Issues & Compatibility

Reference for known bugs, version-specific issues, and workarounds.

## Critical Issues (Fixed)

### `FreeCAD.Color` AttributeError
- **File**: `addon/FreeCADMCP/rpc_server/serialize.py`, line 22
- **Affected versions**: FreeCAD 1.0.2 (and possibly other older releases)
- **Symptom**: `get_objects` crashes with `AttributeError: module 'FreeCAD' has no attribute 'Color'`; `get_object` returns `<error: ...>` strings in property values
- **Root cause**: `isinstance(value, App.Color)` evaluated at call time, but `App.Color` doesn't exist in FreeCAD 1.0.2
- **Fix**: Guard with `hasattr(App, "Color")` before the `isinstance` check
- **Impact**: Unblocks `get_objects` and `get_object` on FreeCAD 1.0.2

### Raw XML-RPC Faults from `get_objects`/`get_object`
- **File**: `addon/FreeCADMCP/rpc_server/rpc_server.py`, lines 308-320
- **Symptom**: Serialization errors propagate as raw XML-RPC faults instead of structured error responses
- **Fix**: Wrapped `serialize_object()` calls in try/except, returning `{"success": false, "error": ...}` on failure
- **Impact**: MCP tools now show clean error messages instead of XML-RPC stack traces

## Behavioral Issues

### Screenshot Size Overflow
- **Affected tools**: `get_view`, `create_object`, `edit_object`, `delete_object`, `execute_code`, `get_objects`, `get_object`
- **Symptom**: Screenshots >300KB on high-DPI (Retina) displays when `width`/`height` are omitted
- **Workaround**: Pass explicit small dimensions (200-400px) to `get_view`; use `--only-text-feedback` to suppress all screenshots

### `execute_code` Always Returns Screenshot
- **Symptom**: Even diagnostic/read-only `execute_code` calls return a base64 screenshot, consuming tokens
- **Workaround**: Use `--only-text-feedback` flag, or accept the screenshot overhead

### Parts Library Dependency
- **Affected tools**: `get_parts_list`, `insert_part_from_library`
- **Symptom**: Empty results or errors when the FreeCAD Parts Library addon is not installed
- **Fix**: No code fix needed; these tools require the optional [Parts Library addon](https://github.com/FreeCAD/FreeCAD-library)

## FreeCAD Version Compatibility

| Feature | FreeCAD 1.0.2 | FreeCAD 1.1+ |
|---------|---------------|--------------|
| `App.Color` | Not available | Available |
| `saveImage()` | Works (3D views only) | Works (3D views only) |
| `ObjectsFem.make*()` | Available | Available |
| Parts Library addon | Optional | Optional |

## Serialization Safety Rules

1. `serialize_value()` must never raise — unhandled types fall back to `str(value)`
2. New `isinstance` checks for FreeCAD types must use `hasattr` guards for version safety
3. `serialize_object()` is wrapped in try/except at the RPC level; individual property errors are caught per-property
4. Return `list` (not `tuple`) for JSON-serializable collections
