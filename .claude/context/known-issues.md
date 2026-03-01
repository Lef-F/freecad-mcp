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

### `execute_code` Screenshot on Diagnostic Calls
- **Status**: Fixed — `execute_code` now accepts `capture_screenshot=False` to skip the screenshot
- **Workaround (before fix)**: Use `--only-text-feedback` flag

### MCP/Addon Version Mismatch — `summary_only` Parameter
- **Symptom**: If MCP server is 0.1.17+ but FreeCAD addon is older (pre-0.1.17), calling `get_objects` will fail with `TypeError: get_objects() takes 2 positional arguments but 3 were given` because the old addon doesn't accept the `summary_only` positional arg
- **Fix**: Restart FreeCAD after deploying the updated addon to `Mod/FreeCADMCP/`
- **Detection**: The error appears as `"Error: ..."` in the MCP tool response, not a connection failure

### Parts Library Dependency
- **Affected tools**: `get_parts_list`, `insert_part_from_library`
- **Symptom**: Empty results or errors when the FreeCAD Parts Library addon is not installed
- **Fix**: No code fix needed; these tools require the optional [Parts Library addon](https://github.com/FreeCAD/FreeCAD-library)

## Python Version Matrix

FreeCAD bundles its **own Python interpreter** — separate from the MCP server's Python environment.

| Component | Python version | Notes |
|-----------|---------------|-------|
| MCP server (`src/`) | 3.12+ (required) | Runs outside FreeCAD; managed by `uv` |
| FreeCAD addon (`addon/`) | 3.11.x (bundled) | Runs inside FreeCAD's embedded interpreter |

**FreeCAD 1.0.2 (macOS) ships Python 3.11.13** via conda:
```
/Applications/FreeCAD.app/Contents/Resources/bin/python --version
# → Python 3.11.13
# conda package: python-3.11.13-hc22306f_0_cpython.json
```

### Implications for addon code
- Do NOT use Python 3.12+ features in `addon/` (e.g., `type` statement aliases)
- Python 3.10+ features (match/case, `X | Y` union annotations) are safe — FreeCAD bundles 3.11
- The MCP server in `src/` can freely use 3.12+ features (dict unpacking improvements, etc.)

### How to re-check the embedded Python version
```bash
# Find the Python binary in the FreeCAD bundle (macOS)
find /Applications/FreeCAD.app -name "python" -maxdepth 6
/Applications/FreeCAD.app/Contents/Resources/bin/python --version

# Or read the conda metadata directly
cat /Applications/FreeCAD.app/Contents/Resources/conda-meta/python-*.json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['version'])"
```

On **Linux AppImage/Snap**, the path pattern is different — look inside the mounted AppImage or:
```bash
# Linux AppImage (mount first, or extract)
find /path/to/squashfs-root -name "python3.*" -maxdepth 5 | head -5
```

On **Windows**, check `%LOCALAPPDATA%\Programs\FreeCAD\bin\python.exe --version`.

## FreeCAD Version Compatibility

| Feature | FreeCAD 1.0.2 | FreeCAD 1.1+ |
|---------|---------------|--------------|
| `App.Color` | Not available | Available |
| `saveImage()` | Works (3D views only) | Works (3D views only) |
| `ObjectsFem.make*()` | Available | Available |
| Parts Library addon | Optional | Optional |
| Embedded Python | 3.11.13 | TBD |

## Serialization Safety Rules

1. `serialize_value()` must never raise — unhandled types fall back to `str(value)`
2. New `isinstance` checks for FreeCAD types must use `hasattr` guards for version safety
3. `serialize_object()` is wrapped in try/except at the RPC level; individual property errors are caught per-property
4. Return `list` (not `tuple`) for JSON-serializable collections
