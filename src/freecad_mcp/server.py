import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
import xmlrpc.client
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Literal, cast

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent, ImageContent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FreeCADMCPserver")


_only_text_feedback = False
_rpc_host = "localhost"

# Snapshots for before/after: {view_name: (screenshot_b64, gemini_analysis_text)}
_snapshots: dict[str, tuple[str, str]] = {}

_session_dir: str | None = None
_screenshot_count: int = 0
_detected_client_name: str | None = None


class FreeCADConnection:
    def __init__(self, host: str = "localhost", port: int = 9875):
        self.server = xmlrpc.client.ServerProxy(
            f"http://{host}:{port}", allow_none=True
        )

    def ping(self) -> bool:
        return cast(bool, self.server.ping())

    def create_document(self, name: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.server.create_document(name))

    def create_object(self, doc_name: str, obj_data: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], self.server.create_object(doc_name, obj_data))

    def edit_object(
        self, doc_name: str, obj_name: str, obj_data: dict[str, Any]
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any], self.server.edit_object(doc_name, obj_name, obj_data)
        )

    def delete_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.server.delete_object(doc_name, obj_name))

    def insert_part_from_library(self, relative_path: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.server.insert_part_from_library(relative_path))

    def execute_code(self, code: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.server.execute_code(code))

    def get_active_screenshot(
        self,
        view_name: str = "Isometric",
        width: int | None = None,
        height: int | None = None,
        focus_object: str | None = None,
        background_color: str = "white",
    ) -> str | None:
        try:
            # Check if we're in a view that supports screenshots
            result = cast(
                dict[str, Any],
                self.server.execute_code("""
import FreeCAD
import FreeCADGui

if FreeCAD.Gui.ActiveDocument and FreeCAD.Gui.ActiveDocument.ActiveView:
    view_type = type(FreeCAD.Gui.ActiveDocument.ActiveView).__name__

    # These view types don't support screenshots
    unsupported_views = ['SpreadsheetGui::SheetView', 'DrawingGui::DrawingView', 'TechDrawGui::MDIViewPage']

    if view_type in unsupported_views or not hasattr(FreeCAD.Gui.ActiveDocument.ActiveView, 'saveImage'):
        print("Current view does not support screenshots")
    else:
        print(f"Current view supports screenshots: {view_type}")
else:
    print("No active view")
"""),
            )

            # Screenshot support is detected via the printed message — if the message contains
            # "does not support screenshots" or the code failed, skip the screenshot.
            if not result.get(
                "success", False
            ) or "Current view does not support screenshots" in result.get(
                "message", ""
            ):
                logger.info(
                    "Screenshot unavailable in current view (likely Spreadsheet or TechDraw view)"
                )
                return None

            # Otherwise, try to get the screenshot
            return cast(
                str | None,
                self.server.get_active_screenshot(
                    view_name, width, height, focus_object, background_color
                ),
            )
        except Exception as e:
            # Log the error but return None instead of raising an exception
            logger.error(f"Error getting screenshot: {e}")
            return None

    def get_objects(self, doc_name: str, summary_only: bool = True) -> dict[str, Any]:
        return cast(dict[str, Any], self.server.get_objects(doc_name, summary_only))

    def get_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.server.get_object(doc_name, obj_name))

    def get_parts_list(self) -> list[str]:
        return cast(list[str], self.server.get_parts_list())

    def list_documents(self) -> list[str]:
        return cast(list[str], self.server.list_documents())


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    try:
        logger.info("FreeCADMCP server starting up")
        try:
            _ = get_freecad_connection()
            logger.info("Successfully connected to FreeCAD on startup")
        except Exception as e:
            logger.warning(f"Could not connect to FreeCAD on startup: {str(e)}")
            logger.warning(
                "Make sure the FreeCAD addon is running before using FreeCAD resources or tools"
            )
        yield {}
    finally:
        # Clean up the global connection on shutdown
        global _freecad_connection, _session_dir
        if _freecad_connection:
            logger.info("Disconnecting from FreeCAD on shutdown")
            _freecad_connection = None
        if _session_dir and os.path.isdir(_session_dir):
            shutil.rmtree(_session_dir, ignore_errors=True)
            logger.info(f"Cleaned up screenshot session dir: {_session_dir}")
            _session_dir = None
        logger.info("FreeCADMCP server shut down")


mcp = FastMCP(
    "FreeCADMCP",
    instructions="FreeCAD integration through the Model Context Protocol",
    lifespan=server_lifespan,
)


_freecad_connection: FreeCADConnection | None = None


def get_freecad_connection() -> FreeCADConnection:
    """Get or create a persistent FreeCAD connection"""
    global _freecad_connection
    if _freecad_connection is None:
        _freecad_connection = FreeCADConnection(host=_rpc_host, port=9875)
        if not _freecad_connection.ping():
            logger.error("Failed to ping FreeCAD")
            _freecad_connection = None
            raise Exception(
                "Failed to connect to FreeCAD. Make sure the FreeCAD addon is running."
            )
    return _freecad_connection


def _is_cli_client(ctx: Context) -> bool:
    """Return True if the connected client is Claude Code CLI.

    Claude Code CLI sends clientInfo.name containing "code" (e.g. "claude-code").
    Claude Desktop sends "claude-desktop" or similar.
    Falls back to False (Desktop behaviour) for unknown clients.
    """
    global _detected_client_name
    if _detected_client_name is None:
        try:
            cp = ctx.request_context.session.client_params
            _detected_client_name = (
                cp.clientInfo.name if (cp and cp.clientInfo) else "unknown"
            )
        except Exception as e:
            _detected_client_name = "unknown"
            logger.debug(f"Could not detect MCP client type: {e}")
        logger.info(f"MCP client detected: {_detected_client_name!r}")
    return "code" in _detected_client_name.lower()


def _save_screenshot_file(screenshot_b64: str) -> str:
    """Decode and save a base64 screenshot to a temp file. Returns the file path.

    Files are written to a per-session temp directory and cleaned up on server shutdown.
    This allows Claude Code CLI to load the image via its Read tool.
    """
    global _session_dir, _screenshot_count
    if _session_dir is None:
        _session_dir = tempfile.mkdtemp(prefix="freecad_mcp_")
    _screenshot_count += 1
    path = os.path.join(_session_dir, f"screenshot_{_screenshot_count:04d}.webp")
    with open(path, "wb") as f:
        f.write(base64.b64decode(screenshot_b64))
    return path


# Helper function to safely add screenshot to response
def add_screenshot_if_available(
    response: list[TextContent],
    screenshot: str | None,
    ctx: Context,
    screenshot_attempted: bool = True,
) -> list[TextContent | ImageContent]:
    """Safely add screenshot to response only if it's available.

    CLI clients receive a file path (no base64); Desktop clients receive ImageContent.
    When screenshot_attempted=False (caller opted out), no "unavailable" note is shown.
    """
    result: list[TextContent | ImageContent] = list(response)
    if screenshot is not None and not _only_text_feedback:
        if _is_cli_client(ctx):
            path = _save_screenshot_file(screenshot)
            result.append(TextContent(type="text", text=f"Screenshot: {path}"))
        else:
            result.append(
                ImageContent(type="image", data=screenshot, mimeType="image/webp")
            )
    elif screenshot_attempted and not _only_text_feedback:
        # Screenshot was requested but the view doesn't support it (e.g. TechDraw, Spreadsheet)
        result.append(
            TextContent(
                type="text",
                text="Note: Visual preview is unavailable in the current view type (such as TechDraw or Spreadsheet). "
                "Switch to a 3D view to see visual feedback.",
            )
        )
    return result


def _call_gemini(
    image_b64: str, question: str, before_analysis: str | None = None
) -> str | None:
    """Send a screenshot to Gemini CLI. Returns analysis text, or None if CLI unavailable."""
    gemini_path = shutil.which("gemini")
    if not gemini_path:
        return None

    img_path = f"/tmp/freecad_mcp_{uuid.uuid4().hex[:8]}.webp"
    try:
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(image_b64))

        if before_analysis:
            prompt = (
                f"BEFORE state description: {before_analysis}\n\n"
                f"Now for the AFTER state — {question} @{img_path}"
            )
        else:
            prompt = f"{question} @{img_path}"

        result = subprocess.run(
            [gemini_path, "--include-directories", "/tmp", "-p", prompt, "-o", "text"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        logger.warning(f"Gemini CLI call failed: {e}")
        return None
    finally:
        if os.path.exists(img_path):
            os.unlink(img_path)


@mcp.tool()
def create_document(ctx: Context, name: str) -> list[TextContent]:
    """Create a new document in FreeCAD.

    Args:
        name: The name of the document to create.

    Returns:
        A message indicating the success or failure of the document creation.

    Examples:
        If you want to create a document named "MyDocument", you can use the following data.
        ```json
        {
            "name": "MyDocument"
        }
        ```
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.create_document(name)
        if res["success"]:
            return [
                TextContent(
                    type="text",
                    text=f"Document '{res['document_name']}' created successfully",
                )
            ]
        else:
            return [
                TextContent(
                    type="text", text=f"Failed to create document: {res['error']}"
                )
            ]
    except Exception as e:
        logger.error(f"Failed to create document: {str(e)}")
        return [TextContent(type="text", text=f"Failed to create document: {str(e)}")]


@mcp.tool()
def create_object(
    ctx: Context,
    doc_name: str,
    obj_type: str,
    obj_name: str,
    analysis_name: str | None = None,
    obj_properties: dict[str, Any] | None = None,
    capture_screenshot: bool = True,
) -> list[TextContent | ImageContent]:
    """Create a new object in FreeCAD.
    Object type is starts with "Part::" or "Draft::" or "PartDesign::" or "Fem::".

    Args:
        doc_name: The name of the document to create the object in.
        obj_type: The type of the object to create (e.g. 'Part::Box', 'Part::Cylinder', 'Draft::Circle', 'PartDesign::Body', etc.).
        obj_name: The name of the object to create.
        obj_properties: The properties of the object to create.

    Returns:
        A message indicating the success or failure of the object creation and a screenshot of the object.

    Examples:
        If you want to create a cylinder with a height of 30 and a radius of 10, you can use the following data.
        ```json
        {
            "doc_name": "MyCylinder",
            "obj_name": "Cylinder",
            "obj_type": "Part::Cylinder",
            "obj_properties": {
                "Height": 30,
                "Radius": 10,
                "Placement": {
                    "Base": {
                        "x": 10,
                        "y": 10,
                        "z": 0
                    },
                    "Rotation": {
                        "Axis": {
                            "x": 0,
                            "y": 0,
                            "z": 1
                        },
                        "Angle": 45
                    }
                },
                "ViewObject": {
                    "ShapeColor": [0.5, 0.5, 0.5, 1.0]
                }
            }
        }
        ```

        If you want to create a circle with a radius of 10, you can use the following data.
        ```json
        {
            "doc_name": "MyCircle",
            "obj_name": "Circle",
            "obj_type": "Draft::Circle",
        }
        ```

        If you want to create a FEM analysis, you can use the following data.
        ```json
        {
            "doc_name": "MyFEMAnalysis",
            "obj_name": "FemAnalysis",
            "obj_type": "Fem::AnalysisPython",
        }
        ```

        If you want to create a FEM constraint, you can use the following data.
        ```json
        {
            "doc_name": "MyFEMConstraint",
            "obj_name": "FemConstraint",
            "obj_type": "Fem::ConstraintFixed",
            "analysis_name": "MyFEMAnalysis",
            "obj_properties": {
                "References": [
                    {
                        "object_name": "MyObject",
                        "face": "Face1"
                    }
                ]
            }
        }
        ```

        If you want to create a FEM mechanical material, you can use the following data.
        ```json
        {
            "doc_name": "MyFEMAnalysis",
            "obj_name": "FemMechanicalMaterial",
            "obj_type": "Fem::MaterialCommon",
            "analysis_name": "MyFEMAnalysis",
            "obj_properties": {
                "Material": {
                    "Name": "MyMaterial",
                    "Density": "7900 kg/m^3",
                    "YoungModulus": "210 GPa",
                    "PoissonRatio": 0.3
                }
            }
        }
        ```

        If you want to create a FEM mesh, you can use the following data.
        The `Part` property is required.
        ```json
        {
            "doc_name": "MyFEMMesh",
            "obj_name": "FemMesh",
            "obj_type": "Fem::FemMeshGmsh",
            "analysis_name": "MyFEMAnalysis",
            "obj_properties": {
                "Part": "MyObject",
                "ElementSizeMax": 10,
                "ElementSizeMin": 0.1,
                "MeshAlgorithm": 2
            }
        }
        ```
    """
    freecad = get_freecad_connection()
    try:
        obj_data = {
            "Name": obj_name,
            "Type": obj_type,
            "Properties": obj_properties or {},
            "Analysis": analysis_name,
        }
        res = freecad.create_object(doc_name, obj_data)
        screenshot = (
            freecad.get_active_screenshot()
            if (capture_screenshot and not _only_text_feedback)
            else None
        )

        if res["success"]:
            response = [
                TextContent(
                    type="text",
                    text=f"Object '{res['object_name']}' created successfully",
                ),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
        else:
            response = [
                TextContent(
                    type="text", text=f"Failed to create object: {res['error']}"
                ),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
    except Exception as e:
        logger.error(f"Failed to create object: {str(e)}")
        return [TextContent(type="text", text=f"Failed to create object: {str(e)}")]


@mcp.tool()
def edit_object(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    obj_properties: dict[str, Any],
    capture_screenshot: bool = True,
) -> list[TextContent | ImageContent]:
    """Edit an object in FreeCAD.
    This tool is used when the `create_object` tool cannot handle the object creation.

    Args:
        doc_name: The name of the document to edit the object in.
        obj_name: The name of the object to edit.
        obj_properties: The properties of the object to edit.

    Returns:
        A message indicating the success or failure of the object editing and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.edit_object(doc_name, obj_name, {"Properties": obj_properties})
        screenshot = (
            freecad.get_active_screenshot()
            if (capture_screenshot and not _only_text_feedback)
            else None
        )

        if res["success"]:
            response = [
                TextContent(
                    type="text",
                    text=f"Object '{res['object_name']}' edited successfully",
                ),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
        else:
            response = [
                TextContent(type="text", text=f"Failed to edit object: {res['error']}"),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
    except Exception as e:
        logger.error(f"Failed to edit object: {str(e)}")
        return [TextContent(type="text", text=f"Failed to edit object: {str(e)}")]


@mcp.tool()
def delete_object(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    capture_screenshot: bool = True,
) -> list[TextContent | ImageContent]:
    """Delete an object in FreeCAD.

    Args:
        doc_name: The name of the document to delete the object from.
        obj_name: The name of the object to delete.

    Returns:
        A message indicating the success or failure of the object deletion and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.delete_object(doc_name, obj_name)
        screenshot = (
            freecad.get_active_screenshot()
            if (capture_screenshot and not _only_text_feedback)
            else None
        )

        if res["success"]:
            response = [
                TextContent(
                    type="text",
                    text=f"Object '{res['object_name']}' deleted successfully",
                ),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
        else:
            response = [
                TextContent(
                    type="text", text=f"Failed to delete object: {res['error']}"
                ),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
    except Exception as e:
        logger.error(f"Failed to delete object: {str(e)}")
        return [TextContent(type="text", text=f"Failed to delete object: {str(e)}")]


@mcp.tool()
def execute_code(
    ctx: Context,
    code: str,
    capture_screenshot: bool = True,
) -> list[TextContent | ImageContent]:
    """Execute arbitrary Python code in FreeCAD.

    Args:
        code: The Python code to execute.
        capture_screenshot: Whether to capture and return a screenshot after execution.
            Set to False for diagnostic/read-only queries to save tokens. Defaults to True.

    Returns:
        A message indicating the success or failure of the code execution, the output of the code execution, and optionally a screenshot.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.execute_code(code)
        screenshot = (
            freecad.get_active_screenshot()
            if (capture_screenshot and not _only_text_feedback)
            else None
        )

        if res["success"]:
            response = [
                TextContent(
                    type="text", text=f"Code executed successfully: {res['message']}"
                ),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
        else:
            response = [
                TextContent(
                    type="text", text=f"Failed to execute code: {res['error']}"
                ),
            ]
            return add_screenshot_if_available(response, screenshot, ctx)
    except Exception as e:
        logger.error(f"Failed to execute code: {str(e)}")
        return [TextContent(type="text", text=f"Failed to execute code: {str(e)}")]


@mcp.tool()
def get_view(
    ctx: Context,
    view_name: Literal[
        "Isometric",
        "Front",
        "Top",
        "Right",
        "Back",
        "Left",
        "Bottom",
        "Dimetric",
        "Trimetric",
    ],
    width: int | None = None,
    height: int | None = None,
    focus_object: str | None = None,
    background_color: str = "white",
) -> list[ImageContent | TextContent]:
    """Get a screenshot of the active view.

    Args:
        view_name: The name of the view to get the screenshot of.
        The following views are available:
        - "Isometric"
        - "Front"
        - "Top"
        - "Right"
        - "Back"
        - "Left"
        - "Bottom"
        - "Dimetric"
        - "Trimetric"
        width: The width of the screenshot in pixels. If not specified, uses the default (400px).
        height: The height of the screenshot in pixels. If not specified, uses the default (300px).
        focus_object: The name of the object to focus on. If not specified, fits all objects in the view.
        background_color: Background color for the screenshot (e.g. "white", "black", "transparent").

    Returns:
        A screenshot of the active view.
    """
    if _only_text_feedback:
        return [
            TextContent(type="text", text="Screenshot not available in text-only mode.")
        ]
    freecad = get_freecad_connection()
    screenshot = freecad.get_active_screenshot(
        view_name, width, height, focus_object, background_color
    )

    if screenshot is not None:
        if _is_cli_client(ctx):
            path = _save_screenshot_file(screenshot)
            return [TextContent(type="text", text=f"Screenshot: {path}")]
        else:
            return [ImageContent(type="image", data=screenshot, mimeType="image/webp")]
    else:
        return [
            TextContent(
                type="text",
                text="Cannot get screenshot in the current view type (such as TechDraw or Spreadsheet)",
            )
        ]


@mcp.tool()
def snapshot_view(
    ctx: Context,
    view_name: Literal[
        "Isometric",
        "Front",
        "Top",
        "Right",
        "Back",
        "Left",
        "Bottom",
        "Dimetric",
        "Trimetric",
    ] = "Isometric",
    width: int | None = None,
    height: int | None = None,
    focus_object: str | None = None,
) -> list[TextContent | ImageContent]:
    """Store a snapshot of the current view for before/after comparison with analyze_view.

    If Gemini CLI is available, also runs a pre-analysis so analyze_view can later
    describe what changed. Falls back gracefully if Gemini is not installed.

    Args:
        view_name: Standard view to capture.
        width: Screenshot width in pixels.
        height: Screenshot height in pixels.
        focus_object: Object to zoom to before capturing.
    """
    if _only_text_feedback:
        return [
            TextContent(
                type="text", text="snapshot_view not available in text-only mode."
            )
        ]

    freecad = get_freecad_connection()
    screenshot = freecad.get_active_screenshot(view_name, width, height, focus_object)
    if screenshot is None:
        return [
            TextContent(
                type="text",
                text="snapshot_view: no screenshot available in current view.",
            )
        ]

    analysis = (
        _call_gemini(
            screenshot,
            "Describe this FreeCAD 3D model in detail: structural elements visible, positions, colors, and spatial arrangement.",
        )
        or ""
    )

    _snapshots[view_name] = (screenshot, analysis)
    msg = f"Snapshot stored for '{view_name}' view."
    if analysis:
        msg += f"\nGemini pre-analysis: {analysis}"
    else:
        msg += "\n(Gemini CLI not available — snapshot stored without pre-analysis.)"
    result: list[TextContent | ImageContent] = [TextContent(type="text", text=msg)]
    if _is_cli_client(ctx):
        path = _save_screenshot_file(screenshot)
        result.append(TextContent(type="text", text=f"Screenshot: {path}"))
    else:
        result.append(
            ImageContent(type="image", data=screenshot, mimeType="image/webp")
        )
    return result


@mcp.tool()
def analyze_view(
    ctx: Context,
    view_name: Literal[
        "Isometric",
        "Front",
        "Top",
        "Right",
        "Back",
        "Left",
        "Bottom",
        "Dimetric",
        "Trimetric",
    ] = "Isometric",
    question: str = "Describe what you see in this 3D model. What structural elements are visible, how are they positioned, and does anything look spatially wrong or misaligned?",
    width: int | None = None,
    height: int | None = None,
    focus_object: str | None = None,
    compare_to_snapshot: bool = False,
) -> list[TextContent | ImageContent]:
    """Capture a view and analyze it visually.

    Always returns the screenshot so Claude can see it. If Gemini CLI is installed
    and authenticated, also returns Gemini's textual analysis. If Gemini is not
    available, returns the screenshot with a note.

    Args:
        view_name: Standard view to capture.
        question: What to ask Gemini. Include design context ("This is a parking lot
                  structure...") so Gemini understands what to look for.
        width: Screenshot width in pixels.
        height: Screenshot height in pixels.
        focus_object: Object to zoom to before capturing.
        compare_to_snapshot: If True, includes the prior snapshot_view description
                             as context so Gemini can describe what changed.
    """
    if _only_text_feedback:
        return [
            TextContent(
                type="text", text="analyze_view not available in text-only mode."
            )
        ]

    freecad = get_freecad_connection()
    screenshot = freecad.get_active_screenshot(view_name, width, height, focus_object)
    if screenshot is None:
        return [
            TextContent(
                type="text",
                text="analyze_view: no screenshot available in current view.",
            )
        ]

    before_analysis: str | None = None
    if compare_to_snapshot and view_name in _snapshots:
        _, before_analysis = _snapshots[view_name]

    analysis = _call_gemini(screenshot, question, before_analysis)

    if _is_cli_client(ctx):
        path = _save_screenshot_file(screenshot)
        result: list[TextContent | ImageContent] = [
            TextContent(type="text", text=f"Screenshot: {path}")
        ]
    else:
        result = [ImageContent(type="image", data=screenshot, mimeType="image/webp")]
    if analysis:
        result.append(
            TextContent(type="text", text=f"**Gemini visual analysis:**\n\n{analysis}")
        )
    else:
        if not shutil.which("gemini"):
            result.append(
                TextContent(
                    type="text",
                    text=(
                        "Gemini CLI not found — visual analysis unavailable. "
                        "Install Gemini CLI for enhanced visual verification."
                    ),
                )
            )
    return result


@mcp.tool()
def insert_part_from_library(
    ctx: Context,
    relative_path: str,
    capture_screenshot: bool = False,
) -> list[TextContent | ImageContent]:
    """Insert a part from the parts library addon.

    Args:
        relative_path: The relative path of the part to insert.

    Returns:
        A message indicating the success or failure of the part insertion and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.insert_part_from_library(relative_path)
        screenshot = (
            freecad.get_active_screenshot()
            if (capture_screenshot and not _only_text_feedback)
            else None
        )

        if res["success"]:
            response = [
                TextContent(
                    type="text", text=f"Part inserted from library: {res['message']}"
                ),
            ]
            return add_screenshot_if_available(
                response, screenshot, ctx, screenshot_attempted=capture_screenshot
            )
        else:
            response = [
                TextContent(
                    type="text",
                    text=f"Failed to insert part from library: {res['error']}",
                ),
            ]
            return add_screenshot_if_available(
                response, screenshot, ctx, screenshot_attempted=capture_screenshot
            )
    except Exception as e:
        logger.error(f"Failed to insert part from library: {str(e)}")
        return [
            TextContent(
                type="text", text=f"Failed to insert part from library: {str(e)}"
            )
        ]


@mcp.tool()
def get_objects(
    ctx: Context,
    doc_name: str,
    detailed: bool = False,
    capture_screenshot: bool = False,
) -> list[TextContent | ImageContent]:
    """Get all objects in a document.
    You can use this tool to get the objects in a document to see what you can check or edit.

    By default returns a compact summary (Name, Label, TypeId, Placement, Shape) for each
    object. Pass detailed=True to include all properties — only use this when you need to
    inspect specific property values across many objects, as it is significantly larger.
    For full details on a single object, prefer get_object() instead.

    Args:
        doc_name: The name of the document to get the objects from.
        detailed: When True, include all object properties. Defaults to False (summary only).

    Returns:
        A list of objects in the document and a screenshot of the document.
    """
    freecad = get_freecad_connection()
    try:
        result = freecad.get_objects(doc_name, summary_only=not detailed)
        if not result.get("success", False):
            return [
                TextContent(
                    type="text", text=f"Error: {result.get('error', 'Unknown error')}"
                )
            ]
        screenshot = (
            freecad.get_active_screenshot()
            if (capture_screenshot and not _only_text_feedback)
            else None
        )
        response = [
            TextContent(type="text", text=json.dumps(result["objects"])),
        ]
        return add_screenshot_if_available(
            response, screenshot, ctx, screenshot_attempted=capture_screenshot
        )
    except Exception as e:
        logger.error(f"Failed to get objects: {str(e)}")
        return [TextContent(type="text", text=f"Failed to get objects: {str(e)}")]


@mcp.tool()
def get_object(
    ctx: Context,
    doc_name: str,
    obj_name: str,
    capture_screenshot: bool = False,
) -> list[TextContent | ImageContent]:
    """Get an object from a document.
    You can use this tool to get the properties of an object to see what you can check or edit.

    Args:
        doc_name: The name of the document to get the object from.
        obj_name: The name of the object to get.

    Returns:
        The object and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        result = freecad.get_object(doc_name, obj_name)
        if not result.get("success", False):
            return [
                TextContent(
                    type="text", text=f"Error: {result.get('error', 'Unknown error')}"
                )
            ]
        screenshot = (
            freecad.get_active_screenshot()
            if (capture_screenshot and not _only_text_feedback)
            else None
        )
        response = [
            TextContent(type="text", text=json.dumps(result["object"])),
        ]
        return add_screenshot_if_available(
            response, screenshot, ctx, screenshot_attempted=capture_screenshot
        )
    except Exception as e:
        logger.error(f"Failed to get object: {str(e)}")
        return [TextContent(type="text", text=f"Failed to get object: {str(e)}")]


@mcp.tool()
def get_parts_list(ctx: Context) -> list[TextContent]:
    """Get the list of parts in the parts library addon."""
    freecad = get_freecad_connection()
    parts = freecad.get_parts_list()
    if parts:
        return [TextContent(type="text", text=json.dumps(parts))]
    else:
        return [
            TextContent(
                type="text",
                text="No parts found in the parts library. You must add parts_library addon.",
            )
        ]


@mcp.tool()
def list_documents(ctx: Context) -> list[TextContent]:
    """Get the list of open documents in FreeCAD.

    Returns:
        A list of document names.
    """
    freecad = get_freecad_connection()
    docs = freecad.list_documents()
    return [TextContent(type="text", text=json.dumps(docs))]


@mcp.prompt()
def asset_creation_strategy() -> str:
    return """
Asset Creation Strategy for FreeCAD MCP

When creating content in FreeCAD, always follow these steps:

0. Before starting any task, always use get_objects() to confirm the current state of the document.

1. Utilize the parts library:
   - Check available parts using get_parts_list().
   - If the required part exists in the library, use insert_part_from_library() to insert it into your document.

2. If the appropriate asset is not available in the parts library:
   - Create basic shapes (e.g., cubes, cylinders, spheres) using create_object().
   - Adjust and define detailed properties of the shapes as necessary using edit_object().

3. Always assign clear and descriptive names to objects when adding them to the document.

4. Explicitly set the position, scale, and rotation properties of created or inserted objects using edit_object() to ensure proper spatial relationships.

5. After editing an object, always verify that the set properties have been correctly applied by using get_object().

6. If detailed customization or specialized operations are necessary, use execute_code() to run custom Python scripts.

Only revert to basic creation methods in the following cases:
- When the required asset is not available in the parts library.
- When a basic shape is explicitly requested.
- When creating complex shapes requires custom scripting.
"""


def _validate_host(value: str) -> str:
    """Validate that *value* is a valid IP address or hostname.

    Used as the ``type`` callback for the ``--host`` argparse argument.
    Raises ``argparse.ArgumentTypeError`` on invalid input.
    """
    import argparse

    import validators

    if validators.ipv4(value) or validators.ipv6(value) or validators.hostname(value):
        return value
    raise argparse.ArgumentTypeError(
        f"Invalid host: '{value}'. Must be a valid IP address or hostname."
    )


def main() -> None:
    """Run the MCP server"""
    global _only_text_feedback, _rpc_host
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only-text-feedback", action="store_true", help="Only return text feedback"
    )
    parser.add_argument(
        "--host",
        type=_validate_host,
        default="localhost",
        help="Host address of the FreeCAD RPC server to connect to (default: localhost)",
    )
    args = parser.parse_args()
    _only_text_feedback = args.only_text_feedback
    _rpc_host = args.host
    logger.info(f"Only text feedback: {_only_text_feedback}")
    logger.info(f"Connecting to FreeCAD RPC server at: {_rpc_host}")
    mcp.run()
