#!/usr/bin/env python3
"""Auto-save FreeCAD document after write operations.

Used as a PostToolUse hook in .claude/settings.json.
Triggers after MCP tools that mutate the document.
"""

import sys
import xmlrpc.client

try:
    s = xmlrpc.client.ServerProxy("http://127.0.0.1:9875")
    result = s.execute_code(
        "doc = FreeCAD.ActiveDocument\n"
        "if doc and doc.FileName:\n"
        "    doc.save()\n"
        '    print("saved:", doc.Label)\n'
        "else:\n"
        '    print("skipped: no doc or unsaved doc")'
    )
    output = result.get("message", "")
    # Extract the print output from the RPC response
    if "saved:" in output:
        label = output.split("saved:", 1)[1].strip()
        print(f"Auto-saved: {label}")
    elif "skipped:" in output:
        pass  # New/unsaved doc, nothing to do
    elif not result.get("success"):
        print(f"Auto-save failed: {result.get('error', 'unknown')}", file=sys.stderr)
except ConnectionRefusedError:
    pass  # FreeCAD not running — tool would have failed too, so this is a no-op
except Exception as e:
    print(f"Auto-save hook error: {e}", file=sys.stderr)
