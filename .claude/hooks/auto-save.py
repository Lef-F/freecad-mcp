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
        "    FreeCADGui.getDocument(doc.Name).Modified = False\n"
        '    print("saved:", doc.Label)\n'
        "else:\n"
        '    print("skipped")'
    )
    output = result.get("message", "")
    if "saved:" in output:
        label = output.split("saved:", 1)[1].strip()
        print(f"Auto-saved: {label}")
except ConnectionRefusedError:
    pass  # FreeCAD not running
except Exception as e:
    print(f"Auto-save hook error: {e}", file=sys.stderr)
