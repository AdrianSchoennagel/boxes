# Copyright (C) 2026
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

from __future__ import annotations

import math
from pathlib import Path

from boxes import *
from boxes.aruco_factory import ARUCO_DICTIONARY_CHOICES, etch_aruco
from boxes.svg_logo_factory import etch_svg_logo


class Turtlebot3Hats(Boxes):
    """Import a DXF shape and add an ArUco marker etching to it."""

    ui_group = "Misc"

    def __init__(self) -> None:
        super().__init__()

        self.argparser.add_argument(
            "--input",
            action="store",
            type=str,
            default="/mnt/c/Users/schoennagel/ownCloud/Documents/Science/Trailer-Hardware/turtlebot3_plate_solid.dxf",
            help="path to input DXF file",
        )
        self.argparser.add_argument(
            "--CurveTolerance",
            action="store",
            type=float,
            default=0.25,
            help="maximum chord error in mm for flattening curves",
        )
        self.argparser.add_argument(
            "--DxfScale",
            action="store",
            type=float,
            default=1.0,
            help="additional uniform scale applied after DXF unit conversion",
        )
        self.argparser.add_argument(
            "--ShapeMove",
            action="store",
            type=str,
            default="",
            help="optional move parameter for placing the imported shape",
        )

        aruco_group = self.argparser.add_argument_group("ArUco")
        aruco_group.add_argument(
            "--AddArucoEtching",
            action="store",
            type=boolarg,
            default=True,
            help="add ArUco etching on top of the imported shape",
        )
        aruco_group.add_argument(
            "--ArucoId",
            action="store",
            type=int,
            default=0,
            help="numeric ArUco marker id",
        )
        aruco_group.add_argument(
            "--ArucoDictionary",
            action="store",
            type=str,
            choices=ARUCO_DICTIONARY_CHOICES,
            default="DICT_6X6_50",
            help="OpenCV ArUco dictionary name",
        )
        aruco_group.add_argument(
            "--ArucoSize",
            action="store",
            type=float,
            default=70.0,
            help="overall marker size in mm",
        )
        aruco_group.add_argument(
            "--ArucoOffsetX",
            action="store",
            type=float,
            default=0.0,
            help="marker X offset from shape center in mm",
        )
        aruco_group.add_argument(
            "--ArucoOffsetY",
            action="store",
            type=float,
            default=0.0,
            help="marker Y offset from shape center in mm",
        )

        logo_group = self.argparser.add_argument_group("Top/Bottom Logos")
        logo_group.add_argument(
            "--AddTopLogo",
            action="store",
            type=boolarg,
            default=True,
            help="add one SVG logo near the top of the shape",
        )
        logo_group.add_argument(
            "--AddBottomLogo",
            action="store",
            type=boolarg,
            default=True,
            help="add one SVG logo near the bottom of the shape",
        )
        logo_group.add_argument(
            "--TopLogoSvgPath",
            action="store",
            type=str,
            default="/mnt/c/Users/schoennagel/Pictures/logo-ivi.svg",
            help="path to top SVG logo",
        )
        logo_group.add_argument(
            "--BottomLogoSvgPath",
            action="store",
            type=str,
            default="/mnt/c/Users/schoennagel/Pictures/logo-ovgu-FIN.svg",
            help="path to bottom SVG logo",
        )
        logo_group.add_argument(
            "--TopLogoMaxWidth",
            action="store",
            type=float,
            default=80.0,
            help="max top logo width in mm",
        )
        logo_group.add_argument(
            "--TopLogoMaxHeight",
            action="store",
            type=float,
            default=20.0,
            help="max top logo height in mm",
        )
        logo_group.add_argument(
            "--BottomLogoMaxWidth",
            action="store",
            type=float,
            default=80.0,
            help="max bottom logo width in mm",
        )
        logo_group.add_argument(
            "--BottomLogoMaxHeight",
            action="store",
            type=float,
            default=20.0,
            help="max bottom logo height in mm",
        )
        logo_group.add_argument(
            "--TopLogoOffsetX",
            action="store",
            type=float,
            default=0.0,
            help="X offset of the top logo from center in mm",
        )
        logo_group.add_argument(
            "--TopLogoOffsetY",
            action="store",
            type=float,
            default=50.0,
            help="Y offset of the top logo in mm",
        )
        logo_group.add_argument(
            "--BottomLogoOffsetX",
            action="store",
            type=float,
            default=2.0,
            help="X offset of the bottom logo from center in mm",
        )
        logo_group.add_argument(
            "--BottomLogoOffsetY",
            action="store",
            type=float,
            default=-50.0,
            help="Y offset of the bottom logo in mm",
        )

        self.argparser.set_defaults(burn=0.075)
        self.argparser.set_defaults(format="dxf")
        self.argparser.set_defaults(reference="0")

    def _arc_points(self, cx: float, cy: float, radius: float, start_deg: float, end_deg: float):
        delta = (float(end_deg) - float(start_deg)) % 360.0
        if delta <= 0:
            delta += 360.0

        segments = max(8, int(math.ceil(delta / 10.0)))
        points = []
        for i in range(segments + 1):
            a = math.radians(start_deg + delta * i / segments)
            points.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
        return points

    def _flatten_entity(self, entity, tolerance: float):
        etype = entity.dxftype()

        if etype == "INSERT":
            flattened = []
            try:
                for virtual in entity.virtual_entities():
                    flattened.extend(self._flatten_entity(virtual, tolerance))
            except Exception:
                return []
            return flattened

        if etype == "LINE":
            s = entity.dxf.start
            e = entity.dxf.end
            return [([(s.x, s.y), (e.x, e.y)], False)]

        if etype == "ARC":
            c = entity.dxf.center
            points = self._arc_points(c.x, c.y, entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle)
            return [(points, False)]

        if etype == "CIRCLE":
            c = entity.dxf.center
            points = self._arc_points(c.x, c.y, entity.dxf.radius, 0.0, 360.0)
            return [(points[:-1], True)]

        if etype == "LWPOLYLINE":
            points_with_bulge = list(entity.get_points("xyb"))
            if any(abs(p[2]) > 1e-9 for p in points_with_bulge):
                flattened = []
                for virtual in entity.virtual_entities():
                    flattened.extend(self._flatten_entity(virtual, tolerance))
                return flattened

            points = [(p[0], p[1]) for p in points_with_bulge]
            if len(points) < 2:
                return []
            return [(points, bool(entity.closed))]

        if etype == "POLYLINE":
            points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
            if len(points) < 2:
                return []
            return [(points, bool(entity.is_closed))]

        if etype in {"SPLINE", "ELLIPSE"}:
            points = [(p.x, p.y) for p in entity.flattening(distance=tolerance)]
            if len(points) < 2:
                return []
            closed = bool(getattr(entity, "closed", False))
            return [(points, closed)]

        # Fallback for other curve-like entities that support flattening.
        if hasattr(entity, "flattening"):
            points = [(p.x, p.y) for p in entity.flattening(distance=tolerance)]
            if len(points) >= 2:
                return [(points, False)]

        return []

    def _load_dxf_paths(self):
        try:
            import ezdxf
            from ezdxf import recover
            from ezdxf import units as ezdxf_units
        except Exception as exc:
            raise RuntimeError("turtlebot3_hats requires ezdxf. Install it with: pip install ezdxf") from exc

        if not self.input:
            raise ValueError("Please provide --input pointing to a DXF file.")

        input_path = Path(self.input)
        if not input_path.exists():
            raise FileNotFoundError(f"DXF file not found: {input_path}")

        # Prefer regular loader first (worked with this file before);
        # fall back to recovery parser only if normal loading fails.
        try:
            doc = ezdxf.readfile(str(input_path))
        except Exception:
            doc, _auditor = recover.readfile(str(input_path))

        unit_factor = 1.0
        if getattr(doc, "units", 0):
            unit_factor = ezdxf_units.conversion_factor(doc.units, ezdxf_units.MM)
        scale = unit_factor * float(self.DxfScale)
        tolerance = max(0.01, float(self.CurveTolerance) / max(scale, 1e-9))

        # Use modelspace content as primary source for generator geometry.
        # If empty, optionally scan other layouts.
        model_entities = list(doc.modelspace())
        entity_sources = [model_entities]
        if not model_entities:
            for layout in doc.layouts:
                if layout.name.upper() != "MODEL":
                    entity_sources.append(list(layout))

        paths = []
        entity_types = set()
        for source in entity_sources:
            for entity in source:
                entity_types.add(entity.dxftype())
                paths.extend(self._flatten_entity(entity, tolerance))
            if paths:
                break

        cleaned = []
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for points, closed in paths:
            scaled = []
            for x, y in points:
                sx = float(x) * scale
                sy = float(y) * scale
                scaled.append((sx, sy))
                min_x = min(min_x, sx)
                min_y = min(min_y, sy)
                max_x = max(max_x, sx)
                max_y = max(max_y, sy)
            if len(scaled) >= 2:
                cleaned.append((scaled, closed))

        if not cleaned:
            known = ", ".join(sorted(entity_types)) if entity_types else "none"
            raise RuntimeError(
                "No drawable entities found in input DXF. "
                f"Found entity types: {known}."
            )

        normalized = []
        for points, closed in cleaned:
            normalized.append(([(x - min_x, y - min_y) for x, y in points], closed))

        width = max_x - min_x
        height = max_y - min_y
        return normalized, width, height

    def top_logo_features(self, panel_w: float, panel_h: float):
        if not self.AddTopLogo or not self.TopLogoSvgPath:
            return
        logo_w = min(float(self.TopLogoMaxWidth), max(panel_w - 2.0, 0.0))
        logo_h = min(float(self.TopLogoMaxHeight), max(panel_h - 2.0, 0.0))
        if logo_w <= 0.0 or logo_h <= 0.0:
            return
        center_x = panel_w / 2.0 + float(self.TopLogoOffsetX)
        center_y = panel_h / 2.0 + float(self.TopLogoOffsetY)
        etch_svg_logo(
            self,
            panel_w,
            panel_h,
            self.TopLogoSvgPath,
            logo_w,
            logo_h,
            center_x,
            center_y,
        )

    def bottom_logo_features(self, panel_w: float, panel_h: float):
        if not self.AddBottomLogo or not self.BottomLogoSvgPath:
            return
        logo_w = min(float(self.BottomLogoMaxWidth), max(panel_w - 2.0, 0.0))
        logo_h = min(float(self.BottomLogoMaxHeight), max(panel_h - 2.0, 0.0))
        if logo_w <= 0.0 or logo_h <= 0.0:
            return
        center_x = panel_w / 2.0 + float(self.BottomLogoOffsetX)
        center_y = panel_h / 2.0 + float(self.BottomLogoOffsetY)
        etch_svg_logo(
            self,
            panel_w,
            panel_h,
            self.BottomLogoSvgPath,
            logo_w,
            logo_h,
            center_x,
            center_y,
        )

    def aruco_label_features(self, panel_w: float, panel_h: float):
        if not self.AddArucoEtching:
            return

        marker_size = min(float(self.ArucoSize), panel_w - 2.0, panel_h - 2.0)
        if marker_size <= 0:
            return

        ox = (panel_w - marker_size) / 2.0 + float(self.ArucoOffsetX)
        oy = (panel_h - marker_size) / 2.0 + float(self.ArucoOffsetY)
        label = str(int(self.ArucoId))
        label_fontsize = max(4.0, marker_size * 0.12)
        label_gap = 2.0
        # Match trailer-like visual centering for text baseline alignment.
        label_y_nudge = -0.15 * label_fontsize

        self.text(
            label,
            x=ox + marker_size + label_gap,
            y=oy + marker_size / 2.0 + label_y_nudge,
            align="middle left",
            fontsize=label_fontsize,
            color=Color.ETCHING,
        )

    def render(self):
        paths, width, height = self._load_dxf_paths()

        if self.move(width, height, self.ShapeMove, before=True):
            return

        # Imported shape is perimeter/cut geometry.
        self.set_source_color(Color.OUTER_CUT)
        for points, closed in paths:
            self.drawPoints(points, kerfdir=0, close=closed)
        # Commit cut/perimeter paths before switching to etching features.
        self.ctx.stroke()

        if self.AddArucoEtching:
            etch_aruco(
                self,
                width,
                height,
                self.ArucoDictionary,
                self.ArucoId,
                self.ArucoSize,
                self.ArucoOffsetX,
                self.ArucoOffsetY,
            )
            # ArUco rectangles are path primitives; stroke them explicitly in etching color.
            self.set_source_color(Color.ETCHING)
            self.ctx.stroke()
            self.set_source_color(Color.BLACK)
        self.aruco_label_features(width, height)

        self.top_logo_features(width, height)
        self.bottom_logo_features(width, height)

        # Restore expected default for subsequent drawing operations.
        self.set_source_color(Color.BLACK)

        self.move(width, height, self.ShapeMove)
