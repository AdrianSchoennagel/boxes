from __future__ import annotations

import sys
from xml.etree import ElementTree as ET

from svgpathtools import Arc, CubicBezier, Line, QuadraticBezier, parse_path

from boxes.Color import Color


def _iter_svg_paths(svg_path: str):
    paths = []
    try:
        tree = ET.parse(svg_path)
    except Exception as e:
        print(f"[Trailer] Failed to read SVG logo '{svg_path}': {e}", file=sys.stderr)
        return None
    root = tree.getroot()
    for el in root.iter():
        if el.tag.endswith("path"):
            d = el.attrib.get("d", "").strip()
            if d:
                try:
                    parsed = parse_path(d)
                except Exception as e:
                    print(f"[Trailer] Failed to parse a path from SVG logo '{svg_path}': {e}", file=sys.stderr)
                    continue
                if parsed:
                    paths.append(parsed)
    return paths


def _svg_bbox(paths):
    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")
    for p in paths:
        if not p:
            continue
        pxmin, pxmax, pymin, pymax = p.bbox()
        xmin = min(xmin, pxmin)
        xmax = max(xmax, pxmax)
        ymin = min(ymin, pymin)
        ymax = max(ymax, pymax)
    if xmin == float("inf"):
        return 0.0, 0.0, 0.0, 0.0
    return xmin, xmax, ymin, ymax


def _draw_svg_paths(ctx, paths):
    break_eps = 1e-6
    for p in paths:
        if not p:
            continue
        current = None
        for segment in p:
            start = segment.start
            if current is None or abs(start - current) > break_eps:
                # Path data may contain multiple subpaths. Start each one explicitly
                # to avoid connecting letters with unwanted bridge lines.
                ctx.move_to(start.real, start.imag)
            if isinstance(segment, Line):
                end = segment.end
                ctx.line_to(end.real, end.imag)
            elif isinstance(segment, CubicBezier):
                c1 = segment.control1
                c2 = segment.control2
                end = segment.end
                ctx.curve_to(c1.real, c1.imag, c2.real, c2.imag, end.real, end.imag)
            elif isinstance(segment, QuadraticBezier):
                p0 = segment.start
                p1 = segment.control
                p2 = segment.end
                c1 = p0 + (2.0 / 3.0) * (p1 - p0)
                c2 = p2 + (2.0 / 3.0) * (p1 - p2)
                ctx.curve_to(c1.real, c1.imag, c2.real, c2.imag, p2.real, p2.imag)
            elif isinstance(segment, Arc):
                # Approximate arcs with short line segments.
                samples = 24
                for i in range(1, samples + 1):
                    pt = segment.point(i / samples)
                    ctx.line_to(pt.real, pt.imag)
            else:
                end = segment.end
                ctx.line_to(end.real, end.imag)
            current = segment.end


def etch_svg_logo(
    box,
    panel_w: float,
    panel_h: float,
    svg_path: str,
    max_width: float,
    max_height: float,
    center_x: float,
    center_y: float,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    callback_edge_char: str | None = None,
    mirrored: bool = False,
) -> None:
    if not svg_path:
        return

    paths = _iter_svg_paths(svg_path)
    if paths is None:
        return
    if not paths:
        print(f"[Trailer] SVG logo has no usable path elements: '{svg_path}'", file=sys.stderr)
        return

    xmin, xmax, ymin, ymax = _svg_bbox(paths)
    src_w = xmax - xmin
    src_h = ymax - ymin
    if src_w <= 0 or src_h <= 0:
        print(f"[Trailer] SVG logo has invalid bounds and was skipped: '{svg_path}'", file=sys.stderr)
        return

    draw_w = min(float(max_width), panel_w - 2.0)
    draw_h = min(float(max_height), panel_h - 2.0)
    if draw_w <= 0 or draw_h <= 0:
        return
    scale = min(draw_w / src_w, draw_h / src_h)

    with box.saved_context() as ctx:
        if callback_edge_char is not None:
            base_y = -(box.edges[callback_edge_char].startWidth() + box.burn)
            box.moveTo(0, base_y)

        box.set_source_color(Color.ETCHING)
        x = center_x + float(offset_x)
        y = center_y + float(offset_y)
        ctx.translate(x, y)
        sx = -scale if mirrored else scale
        # SVG coordinates are y-down; panel drawing coordinates are y-up.
        ctx.scale(sx, -scale)
        ctx.translate(-(xmin + 0.5 * src_w), -(ymin + 0.5 * src_h))
        _draw_svg_paths(ctx, paths)
        ctx.stroke()
        box.set_source_color(Color.BLACK)
