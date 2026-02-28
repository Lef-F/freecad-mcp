---
name: debugging-rpc-connection
description: Diagnoses communication failures between the MCP server and the FreeCAD RPC server, identifying whether the issue is connection, serialization, or GUI thread related.
---

# Debugging RPC Connection Issues

## When to Use
When MCP tools fail with connection errors, timeouts, or unexpected responses from FreeCAD.

## Steps

### 1. Verify FreeCAD RPC server is running
- In FreeCAD: check the MCP Addon toolbar → "Start RPC Server" should have been clicked
- Look at FreeCAD's Python console for startup messages
- The server binds to port 9875 by default

### 2. Test raw connectivity
```python
import xmlrpc.client
server = xmlrpc.client.ServerProxy("http://localhost:9875", allow_none=True)
server.ping()  # Should return True
```

### 3. Check host configuration
- If using `--host` flag, verify the IP/hostname is reachable
- If remote: confirm "Remote Connections" is enabled in FreeCAD's MCP toolbar
- If remote: confirm client IP is in the allowed IPs list

### 4. Identify failure layer

| Symptom | Likely cause |
|---------|-------------|
| `ConnectionRefusedError` | RPC server not running or wrong port |
| `socket.timeout` | Firewall blocking, wrong host, or FreeCAD frozen |
| `Fault` exception | RPC method raised an error inside FreeCAD |
| Method returns but no FreeCAD change | GUI task queue not processing (timer stopped?) |
| `None` screenshot | View type doesn't support `saveImage()` |
| Serialization error | New FreeCAD type not handled in `serialize_value()` |

### 5. Check GUI task queue
If operations are accepted but never execute:
- The 500ms timer (`process_gui_tasks`) may have stopped
- FreeCAD may be blocked by a modal dialog
- Try restarting the RPC server from the toolbar

### 6. Inspect RPC response
Add temporary logging in `FreeCADRPC` methods using `FreeCAD.Console.PrintMessage()` to print the response dict before returning. Check FreeCAD's Python console for output.

## Common Fixes

- **Restart RPC server**: Stop → Start from toolbar (resets thread and queue)
- **Wrong view**: Switch to 3D view before taking screenshots
- **Stale connection**: The MCP server caches the connection — restart the MCP server to reconnect
- **Property errors**: Check `obj.PropertiesList` to see valid property names for the object type

## Verification
- `ping()` returns `True` via raw XML-RPC connection
- An MCP tool call succeeds end-to-end and returns expected data
- Screenshots are returned as non-empty base64 strings (when in a supported view)
