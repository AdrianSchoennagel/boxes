from __future__ import annotations

import sys
import re
from xml.etree import ElementTree as ET

from svgpathtools import Arc, CubicBezier, Line, QuadraticBezier, parse_path

from boxes.Color import Color


def _identity_matrix():
    # SVG affine matrix: [a c e; b d f; 0 0 1]
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mat_mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply_matrix(pt, m):
    a, b, c, d, e, f = m
    x = pt.real
    y = pt.imag
    return complex(a * x + c * y + e, b * x + d * y + f)


def _parse_nums(s):
    return [float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", s)]


def _parse_transform(transform):
    if not transform:
        return _identity_matrix()

    m = _identity_matrix()
    for name, args in re.findall(r"([A-Za-z]+)\s*\(([^\)]*)\)", transform):
        vals = _parse_nums(args)
        op = _identity_matrix()
        lname = name.lower()
        if lname == "matrix" and len(vals) >= 6:
            op = (vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])
        elif lname == "translate":
            tx = vals[0] if len(vals) >= 1 else 0.0
            ty = vals[1] if len(vals) >= 2 else 0.0
            op = (1.0, 0.0, 0.0, 1.0, tx, ty)
        elif lname == "scale":
            sx = vals[0] if len(vals) >= 1 else 1.0
            sy = vals[1] if len(vals) >= 2 else sx
            op = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif lname == "rotate" and len(vals) >= 1:
            ang = math.radians(vals[0])
            ca = math.cos(ang)
            sa = math.sin(ang)
            rot = (ca, sa, -sa, ca, 0.0, 0.0)
            if len(vals) >= 3:
                cx, cy = vals[1], vals[2]
                op = _mat_mul(_mat_mul((1.0, 0.0, 0.0, 1.0, cx, cy), rot), (1.0, 0.0, 0.0, 1.0, -cx, -cy))
            else:
                op = rot
        elif lname == "skewx" and len(vals) >= 1:
            t = math.tan(math.radians(vals[0]))
            op = (1.0, 0.0, t, 1.0, 0.0, 0.0)
        elif lname == "skewy" and len(vals) >= 1:
            t = math.tan(math.radians(vals[0]))
            op = (1.0, t, 0.0, 1.0, 0.0, 0.0)

        # SVG transform list applies left-to-right.
        m = _mat_mul(m, op)
    return m


def _parse_css_class_fills(root):
    class_fills = {}
    style_blocks = []
    for el in root.iter():
        if el.tag.endswith("style") and el.text:
            style_blocks.append(el.text)

    # Minimal CSS parser for rules like: .st0{fill:#179C7D;}
    for css in style_blocks:
        for cls, body in re.findall(r"\.([A-Za-z0-9_-]+)\s*\{([^}]*)\}", css):
            m = re.search(r"fill\s*:\s*([^;]+)", body)
            if m:
                class_fills[cls] = m.group(1).strip()
    return class_fills


def _path_fill(el, class_fills):
    fill = el.attrib.get("fill")
    if fill:
        return fill.strip()

    style = el.attrib.get("style", "")
    m = re.search(r"fill\s*:\s*([^;]+)", style)
    if m:
        return m.group(1).strip()

    classes = el.attrib.get("class", "").split()
    for cls in classes:
        if cls in class_fills:
            return class_fills[cls]
    return None


def _is_white_fill(fill):
    if not fill:
        return False
    f = fill.strip().lower()
    if f in {"#fff", "#ffffff", "white", "rgb(255,255,255)", "rgb(255, 255, 255)"}:
        return True
    return False


def _is_paint_server_fill(fill):
    if not fill:
        return False
    return fill.strip().lower().startswith("url(")


def _is_visible_nonwhite_fill(fill):
    if fill is None:
        # SVG default fill is black when unspecified.
        return True
    f = fill.strip().lower()
    if _is_paint_server_fill(f):
        return False
    if f in {"none", "transparent"}:
        return False
    return not _is_white_fill(fill)


def _is_explicit_nonwhite_fill(fill):
    if fill is None:
        return False
    f = fill.strip().lower()
    if _is_paint_server_fill(f):
        return False
    if f in {"none", "transparent"}:
        return False
    return not _is_white_fill(fill)


def _iter_svg_paths(svg_path: str):
    paths = []
    try:
        tree = ET.parse(svg_path)
    except Exception as e:
        print(f"[Trailer] Failed to read SVG logo '{svg_path}': {e}", file=sys.stderr)
        return None
    root = tree.getroot()
    class_fills = _parse_css_class_fills(root)

    non_render_containers = {
        "defs",
        "symbol",
        "pattern",
        "clippath",
        "mask",
        "marker",
        "metadata",
    }

    def walk(el, parent_matrix, rendered=True):
        tag_name = el.tag.split("}")[-1].lower()
        if tag_name in non_render_containers:
            rendered = False

        local_matrix = _parse_transform(el.attrib.get("transform", ""))
        matrix = _mat_mul(parent_matrix, local_matrix)

        if rendered and el.tag.endswith("path"):
            d = el.attrib.get("d", "").strip()
            fill = _path_fill(el, class_fills)

            if d:
                try:
                    parsed = parse_path(d)
                except Exception as e:
                    print(f"[Trailer] Failed to parse a path from SVG logo '{svg_path}': {e}", file=sys.stderr)
                    return
                if parsed:
                    # Split compound path data into truly continuous subpaths.
                    # This avoids unintended bridge lines between separate glyphs.
                    for subpath in parsed.continuous_subpaths():
                        if subpath:
                            paths.append((subpath, fill, matrix))

        for child in el:
            walk(child, matrix, rendered=rendered)

    walk(root, _identity_matrix(), rendered=True)
    return paths


def _svg_bbox(paths):
    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")
    for p, _fill, matrix in paths:
        if not p:
            continue
        pts = [_apply_matrix(p[0].start, matrix)]
        for segment in p:
            pts.extend(_apply_matrix(pt, matrix) for pt in _sample_segment_points(segment))
        xs = [pt.real for pt in pts]
        ys = [pt.imag for pt in pts]
        xmin = min(xmin, min(xs))
        xmax = max(xmax, max(xs))
        ymin = min(ymin, min(ys))
        ymax = max(ymax, max(ys))
    if xmin == float("inf"):
        return 0.0, 0.0, 0.0, 0.0
    return xmin, xmax, ymin, ymax


def _draw_svg_paths(ctx, paths):
    break_eps = 1e-6
    for p, _fill, matrix in paths:
        if not p:
            continue
        current = None
        for segment in p:
            start = _apply_matrix(segment.start, matrix)
            if current is None or abs(start - current) > break_eps:
                # Path data may contain multiple subpaths. Start each one explicitly
                # to avoid connecting letters with unwanted bridge lines.
                ctx.move_to(start.real, start.imag)
            if isinstance(segment, Line):
                end = _apply_matrix(segment.end, matrix)
                ctx.line_to(end.real, end.imag)
            elif isinstance(segment, CubicBezier):
                c1 = _apply_matrix(segment.control1, matrix)
                c2 = _apply_matrix(segment.control2, matrix)
                end = _apply_matrix(segment.end, matrix)
                ctx.curve_to(c1.real, c1.imag, c2.real, c2.imag, end.real, end.imag)
            elif isinstance(segment, QuadraticBezier):
                p0 = _apply_matrix(segment.start, matrix)
                p1 = _apply_matrix(segment.control, matrix)
                p2 = _apply_matrix(segment.end, matrix)
                c1 = p0 + (2.0 / 3.0) * (p1 - p0)
                c2 = p2 + (2.0 / 3.0) * (p1 - p2)
                ctx.curve_to(c1.real, c1.imag, c2.real, c2.imag, p2.real, p2.imag)
            elif isinstance(segment, Arc):
                # Approximate arcs with short line segments.
                samples = 24
                for i in range(1, samples + 1):
                    pt = _apply_matrix(segment.point(i / samples), matrix)
                    ctx.line_to(pt.real, pt.imag)
            else:
                end = _apply_matrix(segment.end, matrix)
                ctx.line_to(end.real, end.imag)
            current = end


def _sample_segment_points(segment):
    if isinstance(segment, Line):
        return [segment.end]
    if isinstance(segment, (CubicBezier, QuadraticBezier)):
        samples = 16
        return [segment.point(i / samples) for i in range(1, samples + 1)]
    if isinstance(segment, Arc):
        samples = 24
        return [segment.point(i / samples) for i in range(1, samples + 1)]
    return [segment.end]


def _path_to_polygon(path, matrix):
    try:
        from shapely.geometry import Polygon
    except Exception:
        return None

    if not path:
        return None
    start = _apply_matrix(path[0].start, matrix)
    end = _apply_matrix(path[-1].end, matrix)
    if abs(end - start) > 1e-6:
        return None

    pts = [start]
    for segment in path:
        pts.extend(_apply_matrix(pt, matrix) for pt in _sample_segment_points(segment))
    coords = [(p.real, p.imag) for p in pts]
    if len(coords) < 4:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    poly = Polygon(coords)
    if poly.is_empty or poly.area <= 1e-9:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
        if poly.is_empty:
            return None
    return poly


def _path_bounds(path, matrix):
    pts = [_apply_matrix(path[0].start, matrix)]
    for segment in path:
        pts.extend(_apply_matrix(pt, matrix) for pt in _sample_segment_points(segment))
    xs = [p.real for p in pts]
    ys = [p.imag for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    return xmin, xmax, ymin, ymax


def _build_knockout_geometry(paths):
    try:
        from shapely.ops import unary_union
    except Exception:
        return None

    white_polys = []
    nonwhite_polys = []
    for path, fill, matrix in paths:
        poly = _path_to_polygon(path, matrix)
        if poly is None:
            continue
        if _is_white_fill(fill):
            white_polys.append(poly)
        elif _is_explicit_nonwhite_fill(fill):
            nonwhite_polys.append(poly)

    if not nonwhite_polys:
        return None

    base = unary_union(nonwhite_polys)
    if white_polys:
        cutters = []
        keep_outside = []
        base_for_test = base.buffer(1e-6)
        for w in white_polys:
            # Classify by overlap with base area, not by strict set difference.
            # This is robust against tiny numeric gaps from curve sampling.
            if base_for_test.intersects(w):
                cutters.append(w)
            else:
                keep_outside.append(w)

        knocked = base.difference(unary_union(cutters)) if cutters else base
        if keep_outside:
            return unary_union([knocked, unary_union(keep_outside)])
        return knocked
    return base


def _draw_shapely_geometry(ctx, geom):
    gtype = getattr(geom, "geom_type", "")
    if gtype == "Polygon":
        ext = list(geom.exterior.coords)
        if ext:
            ctx.move_to(ext[0][0], ext[0][1])
            for x, y in ext[1:]:
                ctx.line_to(x, y)
            ctx.line_to(ext[0][0], ext[0][1])
        for ring in geom.interiors:
            pts = list(ring.coords)
            if not pts:
                continue
            ctx.move_to(pts[0][0], pts[0][1])
            for x, y in pts[1:]:
                ctx.line_to(x, y)
            ctx.line_to(pts[0][0], pts[0][1])
        return

    if gtype in {"MultiPolygon", "GeometryCollection"}:
        for part in geom.geoms:
            _draw_shapely_geometry(ctx, part)


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

    # Ignore paint-server paths (fill:url(...)). These are typically pattern
    # carrier rectangles and lead to box artifacts in etching output.
    paths = [(p, f, m) for p, f, m in paths if not _is_paint_server_fill(f)]
    if not paths:
        print(f"[Trailer] SVG logo had no drawable paths after filtering: '{svg_path}'", file=sys.stderr)
        return

    has_white = any(_is_white_fill(fill) for _p, fill, _m in paths)
    has_nonwhite = any(_is_explicit_nonwhite_fill(fill) for _p, fill, _m in paths)
    knockout_geom = None
    draw_paths = [(p, f, m) for p, f, m in paths if _is_visible_nonwhite_fill(f) or _is_white_fill(f)]
    if has_white and has_nonwhite:
        knockout_geom = _build_knockout_geometry(paths)

    xmin, xmax, ymin, ymax = _svg_bbox(draw_paths)
    if knockout_geom is not None and not knockout_geom.is_empty:
        kxmin, kymin, kxmax, kymax = knockout_geom.bounds
        xmin = min(xmin, kxmin)
        ymin = min(ymin, kymin)
        xmax = max(xmax, kxmax)
        ymax = max(ymax, kymax)
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
        if knockout_geom is not None and not knockout_geom.is_empty:
            _draw_shapely_geometry(ctx, knockout_geom)
            extra_paths = []
            for item in draw_paths:
                p, fill, matrix = item
                poly = _path_to_polygon(p, matrix)
                if _is_explicit_nonwhite_fill(fill):
                    # Explicit filled base geometry already drawn via knockout result,
                    # except for open paths that cannot be polygonized.
                    if poly is None:
                        extra_paths.append(item)
                elif _is_white_fill(fill):
                    # White paths are handled by knockout (inside/outside base);
                    # keep only open white paths here.
                    if poly is None:
                        extra_paths.append(item)
                else:
                    # Keep default/non-explicit colored paths such as text.
                    extra_paths.append(item)
            _draw_svg_paths(ctx, extra_paths)
        else:
            _draw_svg_paths(ctx, draw_paths)
        ctx.stroke()
        box.set_source_color(Color.BLACK)
