# Copyright (C) 2013-2016 Florian Festi
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from boxes import *

import math


class TruckBody(Boxes):
    """Open truck body with one angled corner, partial bottom, and a parallel inner plate."""

    ui_group = "Box"

    description = """Body with one angled upper-left corner in side view, open right side,
partial bottom on the left, and an extra plate parallel to that partial bottom.
All mating connections use finger joints."""

    # Edit these points to define the etched polygon at the angled corner.
    # Points can be any shape/units; they are auto-centered and uniformly scaled.
    CORNER_ETCH_POLYGON_POINTS = [
        (0.0, 1.0),
        (-1.0, -0.5),
        (-1.0, -1.0),
        (0.4, -1.0),
        (1.0, -0.4),
        (1.0, 1.0),
        (0.0, 1.0),
    ]

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings, bottom_lip=0.0, play=0.05)
        self.buildArgParser(x=217, y=138, h=135, outside=False)

        self.argparser.add_argument(
            "--CornerLength",
            action="store",
            type=float,
            default=40.0,
            help="horizontal run of the angled corner in mm",
        )
        self.argparser.add_argument(
            "--CornerDrop",
            action="store",
            type=float,
            default=80.0,
            help="vertical drop of the angled corner in mm",
        )
        self.argparser.add_argument(
            "--BottomLength",
            action="store",
            type=float,
            default=90.0,
            help="length of the partial bottom panel from the left side in mm",
        )
        self.argparser.add_argument(
            "--InnerPlateHeight",
            action="store",
            type=float,
            default=38.0,
            help="height of the extra plate above the bottom in mm",
        )

        self.argparser.add_argument(
            "--OffshootDepth",
            action="store",
            type=float,
            default=60.0,
            help="horizontal extension of the offshoot on the non-angled side in mm",
        )
        self.argparser.add_argument(
            "--OffshootHeight",
            action="store",
            type=float,
            default=70.0,
            help="vertical height of the offshoot on the non-angled side in mm",
        )

        self.argparser.add_argument(
            "--ScrewHoleDiameter",
            action="store",
            type=float,
            default=3.2,
            help="diameter of the screw holes in mm (M3 clearance typically 3.0-3.4)",
        )
        self.argparser.add_argument(
            "--TopScrewEdgeDistance",
            action="store",
            type=float,
            default=5.0,
            help="distance from selected clean edge to screw-hole center on top plate in mm",
        )
        self.argparser.add_argument(
            "--TopScrewCenterOffsets",
            action="store",
            type=argparseSections,
            default="-24:-12:12:24",
            help="offsets along the clean edge from the plate center line in mm (example: -25:25)",
        )
        self.argparser.add_argument(
            "--TopScrewEdgeSide",
            action="store",
            type=str,
            choices=["left", "right"],
            default="right",
            help="which clean edge to measure TopScrewEdgeDistance from",
        )
        self.argparser.add_argument(
            "--InnerPlateScrewEdgeDistance",
            action="store",
            type=float,
            default=15.0,
            help="distance from selected clean edge to screw-hole center on inner plate in mm",
        )
        self.argparser.add_argument(
            "--InnerPlateScrewCenterOffsets",
            action="store",
            type=argparseSections,
            default="-24:-12:12:24",
            help="offsets along the clean edge from the plate center line in mm (example: -25:25)",
        )
        self.argparser.add_argument(
            "--InnerPlateScrewEdgeSide",
            action="store",
            type=str,
            choices=["left", "right"],
            default="right",
            help="which clean edge to measure InnerPlateScrewEdgeDistance from",
        )
        self.argparser.add_argument(
            "--CornerEtchInset",
            action="store",
            type=float,
            default=8.0,
            help="inset from corner to etch center for corner markers in mm",
        )
        self.argparser.add_argument(
            "--CornerEtchCircleOffsetX",
            action="store",
            type=float,
            default=30.0,
            help="x offset from the lower angled corner to circle center in mm",
        )
        self.argparser.add_argument(
            "--CornerEtchCircleOffsetY",
            action="store",
            type=float,
            default=-30.0,
            help="y offset from the lower angled corner to circle center in mm",
        )
        self.argparser.add_argument(
            "--CornerEtchCircleDiameter",
            action="store",
            type=float,
            default=65.0,
            help="diameter of etched circle at the lower corner beneath the angled edge in mm",
        )
        self.argparser.add_argument(
            "--CornerEtchPolygonDiameter",
            action="store",
            type=float,
            default=50.0,
            help="circumscribed diameter of etched polygon at the upper corner in mm",
        )
        self.argparser.add_argument(
            "--CornerEtchPolygonOffsetX",
            action="store",
            type=float,
            default=8.0,
            help="x offset from the upper angled corner to polygon center in mm (world frame)",
        )
        self.argparser.add_argument(
            "--CornerEtchPolygonOffsetY",
            action="store",
            type=float,
            default=-30.0,
            help="y offset from the upper angled corner to polygon center in mm (world frame)",
        )
        self.argparser.add_argument(
            "--SideRectEtchWidth",
            action="store",
            type=float,
            default=5.0,
            help="width of rectangular etch on side walls in mm (0 disables)",
        )
        self.argparser.add_argument(
            "--SideRectEtchHeight",
            action="store",
            type=float,
            default=85.0,
            help="height of rectangular etch on side walls in mm (0 disables)",
        )
        self.argparser.add_argument(
            "--SideRectEtchOffsetX",
            action="store",
            type=float,
            default=90.0,
            help="x offset from side-profile start corner to rectangle center in mm (world frame)",
        )
        self.argparser.add_argument(
            "--SideRectEtchOffsetY",
            action="store",
            type=float,
            default=95.0,
            help="y offset from side-profile start corner to rectangle center in mm (world frame)",
        )
        self.argparser.add_argument(
            "--SideRectEtch2Width",
            action="store",
            type=float,
            default=0.0,
            help="width of second rectangular etch on side walls in mm (0 disables)",
        )
        self.argparser.add_argument(
            "--SideRectEtch2Height",
            action="store",
            type=float,
            default=0.0,
            help="height of second rectangular etch on side walls in mm (0 disables)",
        )
        self.argparser.add_argument(
            "--SideRectEtch2OffsetX",
            action="store",
            type=float,
            default=0.0,
            help="x offset from side-profile start corner to second rectangle center in mm (world frame)",
        )
        self.argparser.add_argument(
            "--SideRectEtch2OffsetY",
            action="store",
            type=float,
            default=0.0,
            help="y offset from side-profile start corner to second rectangle center in mm (world frame)",
        )

        self.argparser.set_defaults(burn=0.075)
        self.argparser.set_defaults(format="dxf")
        self.argparser.set_defaults(reference="0")

        self._geom = None

    def _prepare_geometry(self):
        x, y, h = self.x, self.y, self.h
        cl = self.CornerLength
        cd = self.CornerDrop
        bl = self.BottomLength
        ih = self.InnerPlateHeight
        od = self.OffshootDepth
        oh = self.OffshootHeight
        t = self.thickness

        if x <= 4 * t:
            raise ValueError("x is too small for this geometry")
        if y <= 2 * t:
            raise ValueError("y is too small for this geometry")
        if h <= 3 * t:
            raise ValueError("h is too small for this geometry")

        cl = min(max(cl, 2 * t), x - 2 * t)
        cd = min(max(cd, 2 * t), h - 2 * t)
        bl = min(max(bl, 2 * t), x - 2 * t)

        left_height = h - cd
        if ih <= t:
            ih = t
        if ih >= left_height - t:
            ih = left_height - t
        if ih <= t:
            raise ValueError("InnerPlateHeight does not fit below the angled corner")

        od = max(0.0, od)
        oh = min(max(0.0, oh), h - 2 * t)

        top_length = x - cl
        diagonal = (cl ** 2 + cd ** 2) ** 0.5
        corner_angle = math.degrees(math.atan2(cd, cl))

        self._geom = {
            "x": x,
            "y": y,
            "h": h,
            "corner_length": cl,
            "corner_drop": cd,
            "bottom_length": bl,
            "inner_plate_height": ih,
            "offshoot_depth": od,
            "offshoot_height": oh,
            "left_height": left_height,
            "top_length": top_length,
            "diagonal": diagonal,
            "corner_angle": corner_angle,
        }

    def _extra_plate_slots(self):
        g = self._geom
        self.fingerHolesAt(0, g["inner_plate_height"], g["bottom_length"], 0)

    def _left_wall_plate_slot(self):
        g = self._geom
        self.fingerHolesAt(g["inner_plate_height"], 0, g["y"], 90)

    def _etch_side_rectangle_cfg(self, w, h, dx, dy, mirrored=False):
        if w <= 0 or h <= 0:
            return
        dx = float(dx)
        if mirrored:
            dx = -dx
        dy = float(dy)
        lx, ly = self._world_offset_to_local(dx, dy)
        self.rectangularHole(lx, ly, w, h, r=0, color=Color.ETCHING)

    def _etch_side_rectangle(self, mirrored=False):
        self._etch_side_rectangle_cfg(
            float(self.SideRectEtchWidth),
            float(self.SideRectEtchHeight),
            self.SideRectEtchOffsetX,
            self.SideRectEtchOffsetY,
            mirrored,
        )

    def _etch_side_rectangle2(self, mirrored=False):
        self._etch_side_rectangle_cfg(
            float(self.SideRectEtch2Width),
            float(self.SideRectEtch2Height),
            self.SideRectEtch2OffsetX,
            self.SideRectEtch2OffsetY,
            mirrored,
        )

    def _side_base_features_left(self):
        self._extra_plate_slots()
        self._etch_side_rectangle(False)
        self._etch_side_rectangle2(False)

    def _side_base_features_right(self):
        self._extra_plate_slots()
        self._etch_side_rectangle(True)
        self._etch_side_rectangle2(True)

    def _world_offset_to_local(self, dx, dy):
        """Convert world-frame offset from current callback corner into local coords."""
        m = getattr(self.ctx, "_m", None)
        if m is None:
            return float(dx), float(dy)
        ox, oy = m * (0.0, 0.0)
        inv = ~m
        return inv * (ox + float(dx), oy + float(dy))

    def _etch_circle_beneath_angled_edge(self):
        self._etch_circle_beneath_angled_edge_mirrored(False)

    def _etch_circle_beneath_angled_edge_mirrored(self, mirrored=False):
        d = float(self.CornerEtchCircleDiameter)
        if d <= 0:
            return
        x = float(self.CornerEtchCircleOffsetX)
        if mirrored:
            x = -x
        y = float(self.CornerEtchCircleOffsetY)
        lx, ly = self._world_offset_to_local(x, y)
        self.hole(lx, ly, d=d, color=Color.ETCHING)
        self.hole(lx, ly, d=d-15, color=Color.ETCHING)

    def _etch_polygon_at_angled_corner(self):
        self._etch_polygon_at_angled_corner_mirrored(False)

    def _etch_polygon_at_angled_corner_mirrored(self, mirrored=False):
        d = float(self.CornerEtchPolygonDiameter)
        if d <= 0:
            return
        points = list(self.CORNER_ETCH_POLYGON_POINTS)
        if len(points) < 3:
            return

        xs = [(-float(px) if mirrored else float(px)) for px, _ in points]
        ys = [float(py) for _, py in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)
        scale = d / max(span_x, span_y)
        cx = 0.5 * (min_x + max_x)
        cy = 0.5 * (min_y + max_y)

        # Explicit world-frame placement from the angled corner callback anchor.
        anchor_x = float(self.CornerEtchPolygonOffsetX)
        if mirrored:
            anchor_x = -anchor_x
        anchor_y = float(self.CornerEtchPolygonOffsetY)
        with self.saved_context():
            self.ctx.stroke()
            self.set_source_color(Color.ETCHING)
            p0px = -float(points[0][0]) if mirrored else float(points[0][0])
            w0x = anchor_x + (p0px - cx) * scale
            w0y = anchor_y + (float(points[0][1]) - cy) * scale
            p0x, p0y = self._world_offset_to_local(w0x, w0y)
            self.ctx.move_to(p0x, p0y)
            for px, py in points[1:]:
                qpx = -float(px) if mirrored else float(px)
                wqx = anchor_x + (qpx - cx) * scale
                wqy = anchor_y + (float(py) - cy) * scale
                qx, qy = self._world_offset_to_local(wqx, wqy)
                self.ctx.line_to(qx, qy)
            self.ctx.line_to(p0x, p0y)
            self.ctx.stroke()

    def _drill_plate_holes(self, plate_length, edge_distance, center_offsets, edge_side):
        d = float(self.ScrewHoleDiameter)
        if d <= 0:
            return
        depth = self._geom["y"]

        if edge_side == "left":
            x = float(edge_distance)
        else:
            x = plate_length - float(edge_distance)
        if x <= d / 2.0 or x >= plate_length - d / 2.0:
            return

        # Place holes along the clean edge direction using centerline-relative offsets.
        centerline = depth / 2.0
        min_y = d / 2.0
        max_y = depth - d / 2.0
        for off in center_offsets:
            y = centerline + float(off)
            if min_y <= y <= max_y:
                self.hole(x, y, d=d)

    def _top_plate_holes(self):
        g = self._geom
        self._drill_plate_holes(
            g["top_length"],
            self.TopScrewEdgeDistance,
            self.TopScrewCenterOffsets,
            self.TopScrewEdgeSide,
        )

    def _inner_plate_holes(self):
        g = self._geom
        self._drill_plate_holes(
            g["bottom_length"],
            self.InnerPlateScrewEdgeDistance,
            self.InnerPlateScrewCenterOffsets,
            self.InnerPlateScrewEdgeSide,
        )

    def render(self):
        self._prepare_geometry()
        g = self._geom

        if self.outside:
            raise ValueError("outside=true is currently not supported for TruckBody")

        # Side profile: partial bottom and optional offshoot on the non-angled side.
        if g["offshoot_depth"] > 0 and g["offshoot_height"] > 0:
            side_borders = [
                g["bottom_length"],
                0,
                g["x"] - g["bottom_length"],
                90,
                g["h"] - g["offshoot_height"],
                -90,
                g["offshoot_depth"],
                90,
                g["offshoot_height"],
                90,
                g["offshoot_depth"],
                0,
                g["top_length"],
                g["corner_angle"],
                g["diagonal"],
                90 - g["corner_angle"],
                g["left_height"],
                90,
            ]
            # Keep the offshoot and non-angled side open; keep mating edges finger-jointed.
            side_edges = "feeeeefff"
            upper_angled_corner_idx = 7
            lower_angled_corner_idx = 8
        else:
            side_borders = [
                g["bottom_length"],
                0,
                g["x"] - g["bottom_length"],
                90,
                g["h"],
                90,
                g["top_length"],
                g["corner_angle"],
                g["diagonal"],
                90 - g["corner_angle"],
                g["left_height"],
                90,
            ]
            side_edges = "feefff"
            upper_angled_corner_idx = 4
            lower_angled_corner_idx = 5

        side_callbacks_left = [None] * (len(side_borders) // 2)
        side_callbacks_left[0] = self._side_base_features_left
        side_callbacks_left[upper_angled_corner_idx] = self._etch_polygon_at_angled_corner
        side_callbacks_left[lower_angled_corner_idx] = self._etch_circle_beneath_angled_edge

        side_callbacks_right = [None] * (len(side_borders) // 2)
        side_callbacks_right[0] = self._side_base_features_right
        side_callbacks_right[upper_angled_corner_idx] = lambda: self._etch_polygon_at_angled_corner_mirrored(True)
        side_callbacks_right[lower_angled_corner_idx] = lambda: self._etch_circle_beneath_angled_edge_mirrored(True)

        self.polygonWall(
            side_borders,
            edge=side_edges,
            callback=side_callbacks_left,
            move="right",
            label="side left",
        )
        self.polygonWall(
            side_borders,
            edge=side_edges,
            callback=side_callbacks_right,
            move="mirror right",
            label="side right",
        )

        # reset pose to left border
        self.polygonWall(side_borders, move="only left", label="reset pose to left border")
        self.polygonWall(side_borders, move="only left", label="reset pose to left border")
        self.polygonWall(side_borders, move="only up", label="reset pose to left border")


        # Left wall closes only the angled-side end; right side intentionally remains open.
        self.rectangularWall(
            g["left_height"],
            g["y"],
            "FfFf",
            callback=[self._left_wall_plate_slot],
            move="right",
            label="left wall",
        )

        self.rectangularWall(
            g["top_length"],
            g["y"],
            "FeFf",
            callback=[self._top_plate_holes],
            move="right",
            label="top",
        )
        self.rectangularWall(g["diagonal"], g["y"], "FFFF", move="right", label="angled face")
        self.rectangularWall(g["bottom_length"], g["y"], "FeFF", move="right", label="partial bottom")
        self.rectangularWall(
            g["bottom_length"],
            g["y"],
            "feff",
            callback=[self._inner_plate_holes],
            move="up",
            label="inner parallel plate",
        )
