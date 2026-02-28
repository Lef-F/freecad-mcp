---
name: preparing-release
description: Walks through the version bump, validation, and tagging process for publishing a new release to PyPI.
---

# Preparing a Release

## When to Use
When changes are ready to be published as a new version on PyPI.

## Steps

### 1. Verify code quality
```bash
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
uv run pytest
```

### 2. Check current version
Read the `version` field in `pyproject.toml`. Current versioning follows semver: `0.1.x` for patches, `0.2.0` for minor features.

### 3. Bump version
Edit the `version` field in `pyproject.toml`. Follow semver:
- **Patch** (`0.1.x → 0.1.x+1`): bug fixes, minor improvements
- **Minor** (`0.1.x → 0.2.0`): new tools, new features, non-breaking changes
- **Major** (`0.x → 1.0`): breaking changes to MCP tool signatures or RPC protocol

### 4. Commit and tag
```bash
git add pyproject.toml
git commit -m "chore: bump version to <new_version>"
git tag v<new_version>
```

### 5. Build and publish
```bash
uv build
uv publish
```

### 6. Push
```bash
git push origin main --tags
```

## Verification
- Confirm the new version appears on PyPI
- Test installation: `uvx freecad-mcp --help`
- Verify the version tag exists: `git tag -l`
