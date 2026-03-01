import FreeCAD as App
import json

# Properties to skip in full serialization — large, internal, or already captured separately
_SKIP_PROPERTIES = frozenset({
    "Shape",            # Captured separately via serialize_shape()
    "ExpressionEngine", # Internal expression bindings, rarely useful
    "OutList",          # Forward dependency graph (can be large)
    "InList",           # Reverse dependency graph (can be large)
    "Mesh",             # Raw mesh data (very large)
    "Points",           # Point cloud data (very large)
})

# Max length for str() fallback values — prevents huge strings from Shape objects etc.
_MAX_STR_LEN = 200


def serialize_value(value):
    if isinstance(value, (int, float, str, bool)):
        return value
    elif isinstance(value, App.Vector):
        return {"x": value.x, "y": value.y, "z": value.z}
    elif isinstance(value, App.Rotation):
        return {
            "Axis": {"x": value.Axis.x, "y": value.Axis.y, "z": value.Axis.z},
            "Angle": value.Angle,
        }
    elif isinstance(value, App.Placement):
        return {
            "Base": serialize_value(value.Base),
            "Rotation": serialize_value(value.Rotation),
        }
    elif isinstance(value, (list, tuple)):
        return [serialize_value(v) for v in value]
    elif hasattr(App, "Color") and isinstance(value, App.Color):
        return list(value)
    elif hasattr(App, "DocumentObject") and isinstance(value, App.DocumentObject):
        return {"Name": value.Name, "Label": value.Label}
    else:
        s = str(value)
        return s[:_MAX_STR_LEN] + "…" if len(s) > _MAX_STR_LEN else s


def serialize_shape(shape):
    if shape is None:
        return None
    try:
        return {
            "Volume": shape.Volume,
            "Area": shape.Area,
            "VertexCount": len(shape.Vertexes),
            "EdgeCount": len(shape.Edges),
            "FaceCount": len(shape.Faces),
        }
    except Exception as e:
        return {"error": str(e)}


def serialize_view_object(view):
    if view is None:
        return None
    result = {"Visibility": view.Visibility}
    if hasattr(view, "ShapeColor"):
        result["ShapeColor"] = serialize_value(view.ShapeColor)
    if hasattr(view, "Transparency"):
        result["Transparency"] = view.Transparency
    return result


def serialize_object(obj, summary_only: bool = False):
    """Serialize a FreeCAD object to a JSON-safe dict.

    Args:
        obj: FreeCAD document object, document, or list of objects.
        summary_only: When True, return only Name/Label/TypeId/Placement/Shape —
            no Properties dict, no ViewObject. Use for listing many objects.
            When False (default), return all properties excluding _SKIP_PROPERTIES.
    """
    if isinstance(obj, list):
        return [serialize_object(item, summary_only=summary_only) for item in obj]
    elif isinstance(obj, App.Document):
        return {
            "Name": obj.Name,
            "Label": obj.Label,
            "FileName": obj.FileName,
            "Objects": [serialize_object(child, summary_only=summary_only) for child in obj.Objects],
        }
    else:
        result = {
            "Name": obj.Name,
            "Label": obj.Label,
            "TypeId": obj.TypeId,
            "Placement": serialize_value(getattr(obj, "Placement", None)),
            "Shape": serialize_shape(getattr(obj, "Shape", None)),
        }

        if summary_only:
            return result

        result["Properties"] = {}
        result["ViewObject"] = {}

        for prop in obj.PropertiesList:
            if prop in _SKIP_PROPERTIES:
                continue
            try:
                result["Properties"][prop] = serialize_value(getattr(obj, prop))
            except Exception as e:
                result["Properties"][prop] = f"<error: {str(e)}>"

        if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
            view = obj.ViewObject
            result["ViewObject"] = serialize_view_object(view)

        return result
