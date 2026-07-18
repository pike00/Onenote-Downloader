from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from onenote_archive.preprocess import himetric_to_px

INKML_NS = "http://www.w3.org/2003/InkML"
NS = {"inkml": INKML_NS}


@dataclass
class Brush:
    brush_id: str
    width_px: float = 2.5
    color: str = "#000000"
    alpha: float = 1.0
    tip: str = "ellipse"
    raster_op: str = "copyPen"


@dataclass
class Trace:
    points: list[tuple[float, float]]  # CSS px
    brush: Brush
    pressure: list[float] = field(default_factory=list)


@dataclass
class InkDocument:
    traces: list[Trace]
    max_x: float = 0.0
    max_y: float = 0.0


def parse_inkml(inkml_text: str) -> InkDocument:
    # ElementTree needs a default ns or Clark notation; register prefix
    text = inkml_text
    # Ensure parseable: some docs use inkml: prefix with xmlns
    root = ET.fromstring(text)
    # Normalize tag lookup with/without namespace
    brushes: dict[str, Brush] = {}

    for brush_el in _findall(root, "brush"):
        bid = brush_el.get("{http://www.w3.org/XML/1998/namespace}id") or brush_el.get("id") or ""
        props = {_prop_name(p): p.get("value", "") for p in _findall(brush_el, "brushProperty")}
        width_h = float(props.get("width") or 75)
        color = props.get("color") or "#000000"
        try:
            transparency = float(props.get("transparency") or 0)
        except ValueError:
            transparency = 0.0
        alpha = max(0.0, min(1.0, 1.0 - transparency))
        brushes[bid] = Brush(
            brush_id=bid,
            width_px=max(1.0, himetric_to_px(width_h)),
            color=color,
            alpha=alpha,
            tip=props.get("tip") or "ellipse",
            raster_op=props.get("rasterOp") or "copyPen",
        )
        brushes[f"#{bid}"] = brushes[bid]

    default_brush = Brush(brush_id="default")
    traces: list[Trace] = []
    max_x = max_y = 0.0

    for trace_el in _findall(root, "trace"):
        brush_ref = trace_el.get("brushRef") or ""
        brush = brushes.get(brush_ref) or brushes.get(brush_ref.lstrip("#")) or default_brush
        context = trace_el.get("contextRef") or ""
        has_pressure = "Pressure" in context or "WithPressure" in context
        points_px: list[tuple[float, float]] = []
        pressures: list[float] = []
        raw = (trace_el.text or "").strip()
        if not raw:
            continue
        for point in raw.split(","):
            parts = point.strip().split()
            if len(parts) < 2:
                continue
            x = himetric_to_px(float(parts[0]))
            y = himetric_to_px(float(parts[1]))
            points_px.append((x, y))
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            if has_pressure and len(parts) >= 3:
                pressures.append(float(parts[2]) / 32767.0)
        if len(points_px) >= 2:
            traces.append(Trace(points=points_px, brush=brush, pressure=pressures))

    return InkDocument(traces=traces, max_x=max_x, max_y=max_y)


def _findall(parent: ET.Element, local: str) -> list[ET.Element]:
    out = parent.findall(f".//{{{INKML_NS}}}{local}")
    if out:
        return out
    # fallback without ns
    return parent.findall(f".//{local}")


def _prop_name(el: ET.Element) -> str:
    return el.get("name") or ""


def rgba_from_brush(brush: Brush) -> tuple[int, int, int, int]:
    color = brush.color.lstrip("#")
    if len(color) == 6:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    else:
        r = g = b = 0
    a = int(round(brush.alpha * 255))
    # Highlighters often use maskPen — keep translucent
    if brush.raster_op.lower() == "maskpen":
        a = min(a, 140)
    return r, g, b, a
