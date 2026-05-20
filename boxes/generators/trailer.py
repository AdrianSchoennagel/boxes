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
from boxes.aruco_factory import ARUCO_DICTIONARY_CHOICES, etch_aruco

import numpy as np
import math

class Trailer(Boxes):
    """Trailer with Lid, optional side-openings, optional lid, axle hole, and hitch-joints."""

    description = """X is length in direction of the hitch, Y is width, H is height. The trailer has a lid and optional side-openings.
    The side-openings can be customized with the Openings* parameters. If MakeStackable is true, the trailer will have a lip on the bottom and stabilizers on the sides to make it stackable."""
    ui_group = "Box"

    def __init__(self) -> None:
        """Register geometry options and default generator behavior."""
        Boxes.__init__(self)

        # Finger-joint and stackable-edge defaults for this generator.
        self.addSettingsArgs(edges.FingerJointSettings, bottom_lip=1.0, play=0.1)
        self.addSettingsArgs(edges.StackableSettings, bottom_stabilizers=0.0, top_stabilizers=0.0, height=3.0)
        # Default dimensions are treated as outside measurements.
        self.buildArgParser(x=260, y=130, h=110, outside=True)

        self.argparser.add_argument("--MakeStackable", action="store", type=boolarg, default=True, help="make crates stackable")
        # self.argparser.add_argument("--AddPatternMask", action="store", type=boolarg, default=False, help="add pattern mask")
        self.argparser.add_argument("--AxleDiameter", action="store", type=float, default=3.0, help="diameter of the axle hole in mm")

        lid_group = self.argparser.add_argument_group("Lid")
        lid_group.add_argument("--AddLid", action="store", type=boolarg, default=True, help="add a lid panel")
        lid_group.add_argument("--SplitLid", action="store", type=boolarg, default=True, help="split lid into fixed rear and removable front")
        lid_group.add_argument("--LidSplitRatio", action="store", type=float, default=0.5, help="rear lid length as a fraction of the total length")

        # Side openings
        side_openings_group = self.argparser.add_argument_group("Side openings")
        side_openings_group.add_argument("--AddSideOpenings", action="store", type=boolarg, default=True, help="add side openings")
        side_openings_group.add_argument("--AddFrontOpenings", action="store", type=boolarg, default=False, help="add front and back openings")
        side_openings_group.add_argument("--OpeningTopOffset", action="store", type=float, default=20.0, help="offset of the opening hole from top edge")
        side_openings_group.add_argument("--OpeningSideOffset", action="store", type=float, default=45.0, help="offset of the opening hole from side edge")
        side_openings_group.add_argument("--OpeningBottomOffset", action="store", type=float, default=20.0, help="offset of the opening hole from bottom edge")
        side_openings_group.add_argument("--OpeningRadius", action="store", type=float, default=5, help="opening hole radius")

        chute_group = self.argparser.add_argument_group("Chutes")
        chute_group.add_argument("--AddChutes", action="store", type=boolarg, default=True, help="add side chutes")
        chute_group.add_argument("--ChuteSlopePercent", action="store", type=float, default=30.0, help="chute incline as rise/run percent")
        chute_group.add_argument("--ChuteOutsideExtension", action="store", type=float, default=50.0, help="extra chute extension outside the side opening in mm")

        # aruco marker for lid
        lid_aruco_group = self.argparser.add_argument_group("Lid ArUco")
        lid_aruco_group.add_argument("--AddLidArucoEtching", action="store", type=boolarg, default=True, help="add an ArUco marker etching on the lid")
        lid_aruco_group.add_argument("--LidArucoId", action="store", type=int, default=0, help="numeric ArUco marker id")
        lid_aruco_group.add_argument(
            "--LidArucoDictionary",
            action="store",
            type=str,
            choices=ARUCO_DICTIONARY_CHOICES,
            default="DICT_6X6_50",
            help="OpenCV ArUco dictionary name",
        )
        lid_aruco_group.add_argument("--LidArucoSize", action="store", type=float, default=70.0, help="overall marker size on lid in mm")
        lid_aruco_group.add_argument("--LidArucoOffsetX", action="store", type=float, default=0.0, help="marker X offset from lid center in mm")
        lid_aruco_group.add_argument("--LidArucoOffsetY", action="store", type=float, default=0.0, help="marker Y offset from lid center in mm")

        side_aruco_group = self.argparser.add_argument_group("Side ArUco")
        side_aruco_group.add_argument("--AddSideArucoEtching", action="store", type=boolarg, default=True, help="add an ArUco marker etching on both side panels")
        side_aruco_group.add_argument("--SideArucoId", action="store", type=int, default=0, help="numeric side ArUco marker id")
        side_aruco_group.add_argument(
            "--SideArucoDictionary",
            action="store",
            type=str,
            choices=ARUCO_DICTIONARY_CHOICES,
            default="DICT_5X5_50",
            help="OpenCV ArUco dictionary name for side marker",
        )
        side_aruco_group.add_argument("--SideArucoSize", action="store", type=float, default=30.0, help="overall marker size on side panel in mm")
        side_aruco_group.add_argument("--SideArucoMargin", action="store", type=float, default=5.0, help="right margin for side marker in mm")
        side_aruco_group.add_argument("--SideArucoOffsetY", action="store", type=float, default=20.0, help="marker Y offset from side panel center in mm")

        # Hitch joint parameters
        hitch_group = self.argparser.add_argument_group("Hitch")
        hitch_group.add_argument("--AddHitchJoint", action="store", type=boolarg, default=True, help="add hitch joint features and parts")
        hitch_group.add_argument("--HitchLength", action="store", type=float, default=100.0, help="hitch connector length in mm. This is the distance from the front edge of the trailer to the center of the hitch pin hole.")
        hitch_group.add_argument("--HitchWidth", action="store", type=float, default=10.0, help="hitch connector width in mm")
        hitch_group.add_argument("--HitchPinDiameter", action="store", type=float, default=5.0, help="rear wall pin-hole diameter in mm")
        hitch_group.add_argument("--HitchPinOffsetBottom", action="store", type=float, default=65.0, help="vertical offset of hitch pin/slot from bottom in mm")
        hitch_group.add_argument("--HitchSlotClearance", action="store", type=float, default=0.3, help="extra clearance for front hitch slot in mm")
        hitch_group.add_argument("--HitchLatchArmLength", action="store", type=float, default=10.0, help="length of hitch tongue inside trailer in mm")
        hitch_group.add_argument("--HitchLatchNeckWidth", action="store", type=float, default=6.0, help="width of the neck of the hitch tongue (part inside trailer) in mm")
        hitch_group.add_argument("--HitchSecurerThickness", action="store", type=float, default=5.0, help="extra thickness of the hitch securer in mm")

        # Project-specific fabrication defaults.
        self.argparser.set_defaults(burn=0.075)
        self.argparser.set_defaults(format="dxf")
        self.argparser.set_defaults(reference="0")

    def openingHole(self, width):
        """Draw the rounded rectangular opening centered on the current wall."""
        stackEdge = self.edges['s'].settings
        offsetForStacking = stackEdge.height if self.MakeStackable else 0
        hoffset = self.OpeningTopOffset
        hw = width - self.OpeningSideOffset * 2
        hh = self.h - self.OpeningTopOffset - self.OpeningBottomOffset
        hr = self.OpeningRadius
        opening_y = hh/2 + hoffset - offsetForStacking
        self.rectangularHole(width/2, opening_y, hw, hh, hr)
        # if self.AddPatternMask:
        #     self.rectangularHole(width/2, opening_y, hw + hoffset * 2, hh + hoffset * 2, hr + hoffset, color = Color.ANNOTATIONS)
        #     patternHeight = self.h - hoffset * 2
        #     patterny = opening_y + patternHeight/2 if self.MakeStackable else hoffset + patternHeight/2
        #     self.rectangularHole(width/2, patterny, width - hoffset * 2, patternHeight, 0, color = Color.ANNOTATIONS)

    def topFingerHoles(self, width, length=None, offset=0.0):
        """Add top finger-joint holes only when a matching lid is generated."""
        if not self.AddLid:
            return
        if length is None:
            length = width
        dist = self.fingerHolesAt.settings.edge_width
        self.fingerHolesAt(offset, self.burn + dist + self.thickness / 2, length, 0)

    def sideTopFeatures(self, width):
        """Apply side-panel top-edge cutouts in callback order."""
        if self.AddSideOpenings:
            self.openingHole(width)
        if self.SplitLid:
            self.sideHingeSlots(width)
            self.topFingerHoles(width, length=self._lid_rear_len)
        else:
            self.topFingerHoles(width)

    def frontTopFeatures(self, width):
        """Apply front/back top-edge cutouts in callback order."""
        if self.AddFrontOpenings:
            self.openingHole(width)
        if not self.SplitLid:
            self.topFingerHoles(width)

    def frontBottomFeatures(self, width):
        """Apply front wall features including hitch slot."""
        if self.AddChutes:
            self.chuteFingerHoles(width)
        if not self.AddHitchJoint:
            return

        # Front rectungular hole for the tongue to pass through
        slot_w = self.HitchWidth + self.HitchSlotClearance
        slot_h = self.thickness + self.HitchSlotClearance
        stack = self.edges['s'].settings
        y_center = self.HitchPinOffsetBottom - stack.height 
        self.rectangularHole(
            width / 2.0,
            y_center,
            slot_w,
            slot_h,
            center_y=True,
            center_x=True
        )

        # front rectungular hole for the tongue securer to lock into
        securer_w = self.thickness
        securer_h = 2 * self.HitchSecurerThickness + self.thickness
        self.rectangularHole(
            width / 2.0,
            y_center,
            securer_w,
            securer_h,
            center_y=True,
            center_x=True
        )

    def backTopFeatures(self, width):
        if self.AddFrontOpenings:
            self.openingHole(width)
        self.topFingerHoles(width)

    def backBottomFeatures(self, width):
        """Apply back wall features including rear pin hole."""
        if self.AddChutes:
            self.chuteFingerHoles(width)
        if not self.AddHitchJoint:
            return

        # Rear cutout with a central pin rising from the bottom:
        # top window + two lower side windows leave a center tongue (pin).
        pin_w = self.HitchPinDiameter
        pin_h = max(self.HitchPinDiameter * 1.4, self.thickness * 1.2)
        outer_w = max(self.HitchWidth * 1.8, pin_w + 6.0)
        side_w = max((outer_w - pin_w) / 2.0, 1.0)
        top_h = self.thickness * 1.1

        stack = self.edges['s'].settings
        y_pin = self.HitchPinOffsetBottom - stack.height - self.thickness / 2.0
        x_left = width / 2.0 - (pin_w / 2.0 + side_w / 2.0)
        x_right = width / 2.0 + (pin_w / 2.0 + side_w / 2.0)
        y_top = y_pin + pin_h

        self.rectangularHole(x_left, y_pin, side_w, pin_h+0.01, center_y=False)
        self.rectangularHole(x_right, y_pin, side_w, pin_h+0.01, center_y=False)
        self.rectangularHole(width / 2.0, y_top, outer_w, top_h, center_y=False)

    def rearSideFootHole(self, width):
        """Place a round axle hole in the rear side foot."""
        stack = self.edges['s'].settings
        d = self.AxleDiameter
        self.hole(width - (d+1), -stack.height / 1, d=d)

    def sideArucoFeatures(self, panel_w, panel_h, mirrored=False):
        """Etch an ArUco marker on the right side of a side panel, centered in height."""
        if not self.AddSideArucoEtching:
            return
        size = min(float(self.SideArucoSize), panel_w - 2.0, panel_h - 2.0)
        if size <= 0:
            return
        ox = panel_w / 2.0 - size / 2.0 - float(self.SideArucoMargin)
        if mirrored:
            ox = -ox
        etch_aruco(
            self,
            panel_w,
            panel_h,
            self.SideArucoDictionary,
            self.SideArucoId,
            size,
            offset_x=ox,
            offset_y=self.SideArucoOffsetY,
            callback_edge_char="s",
        )

    def sideBottomFeatures(self, panel_w, panel_h, mirrored=False):
        """Apply side-panel bottom-edge features."""
        self.rearSideFootHole(panel_w)
        self.sideArucoFeatures(panel_w, panel_h, mirrored)

    def sideHingeSlots(self, width):
        """Cut hinge slots into the side top edge at the lid split."""
        if self._lid_front_len <= 0:
            return
        settings = self.edges["i"].settings
        t = self.thickness
        hinge_axle = settings.axle
        pinl = max((hinge_axle ** 2 - t ** 2), 0.0) ** 0.5 * settings.pinwidth
        if settings.style == "outset":
            r = 0.5 * hinge_axle
            alpha = math.degrees(math.asin(0.5 * t / r))
            pos = math.cos(math.radians(alpha)) * r
        else:
            pos = 0.5 * hinge_axle + settings.hingestrength
        stack = self.edges["s"].settings
        x = width - pos
        y = self.burn + t / 2.0 + stack.holedistance
        self.hole(x, y, d=hinge_axle)
        self.rectangularHole(x, y, pinl, t)

    def get_chute_length(self):
        """Calculate the required chute length based on the opening size and chute slope."""
        t = self.thickness
        inner_width = self.y - 2 * t
        if inner_width <= 0:
            return 0.0
        max_inside_depth = inner_width / 2.0
        stack = self.edges['s'].settings
        max_height = self.OpeningBottomOffset - t / 2.0 - t - stack.holedistance

        slope = abs(self.ChuteSlopePercent) / 100.0
        if slope <= 0.0:
            return max_inside_depth
        angle = math.atan(slope)

        height = min(max_height, max_inside_depth * math.tan(angle))
        depth = height / math.tan(angle)

        return math.sqrt(height ** 2 + depth ** 2)

    def renderChuteParts(self):
        """Render chute panels and optional supports."""
        if not self.AddChutes:
            return
        t = self.thickness
        inner_width = self.y - 2 * t
        if inner_width <= 0:
            return
        outside_extension = max(0.0, self.ChuteOutsideExtension)
        inside_depth = self.get_chute_length()

        tab_width = max(0.0, self.x - 2 * self.OpeningSideOffset)
        if tab_width <= 0.0:
            return
        side_offset = (self.x - tab_width) / 2.0

        borders = [
            self.x, 90,
            inside_depth, 90,
            side_offset, -90,
            outside_extension, 90,
            tab_width, 90,
            outside_extension, -90,
            side_offset, 90,
            inside_depth, 90,
        ]
        chute_edges = ["e", "f", "e", "e", "e", "e", "e", "f"]

        self.polygonWall(borders, edge=chute_edges, move="up", label="Chute Left")
        self.polygonWall(borders, edge=chute_edges, move="up", label="Chute Right")

    def chuteFingerHoles(self, width):
        """Add finger holes for the chute on front/back panels."""
        t = self.thickness
        inner_width = width - 2 * t
        if inner_width <= 0:
            return        
        inside_depth = self.get_chute_length()

        stackEdge = self.edges['s'].settings
        offsetForStacking = stackEdge.height if self.MakeStackable else 0
        stack = self.edges['s'].settings
        max_height = self.OpeningBottomOffset - t / 2.0 - t - stack.holedistance
        y = self.OpeningBottomOffset + t / 2.0 + t + stack.holedistance  # + offsetForStacking
        self.fingerHolesAt(0, y, inside_depth, -self.ChuteSlopePercent)
        self.fingerHolesAt(width, y, inside_depth, 180+self.ChuteSlopePercent)

    def lidArucoFeatures(self, lid_w, lid_h):
        """Etch ArUco marker and a small Arabic ID label beside it."""
        if not self.AddLidArucoEtching:
            return

        etch_aruco(
            self,
            lid_w,
            lid_h,
            self.LidArucoDictionary,
            self.LidArucoId,
            self.LidArucoSize,
            self.LidArucoOffsetX,
            self.LidArucoOffsetY,
            callback_edge_char="f",
        )

        marker_size = min(float(self.LidArucoSize), lid_w - 2.0, lid_h - 2.0)
        if marker_size <= 0:
            return
        ox = (lid_w - marker_size) / 2.0 + float(self.LidArucoOffsetX)
        oy = (lid_h - marker_size) / 2.0 + float(self.LidArucoOffsetY)
        label = str(int(self.LidArucoId))
        label_fontsize = max(4.0, marker_size * 0.12)
        label_gap = 2.0
        # Text anchoring uses font-height heuristics; a small negative nudge centers it visually.
        label_y_nudge = -0.15 * label_fontsize

        with self.saved_context():
            base_y = -(self.edges["f"].startWidth() + self.burn)
            self.moveTo(0, base_y)
            self.text(
                label,
                x=ox + marker_size + label_gap,
                y=oy + marker_size / 2.0 + label_y_nudge,
                align="middle left",
                fontsize=label_fontsize,
                color=Color.ETCHING,
            )

    def hitchConnectorFeatures(self):
        """Add circular hole cutout to the hitch tongue."""
        tip_margin = 0
        self.hole(
            self.HitchLatchArmLength + self.HitchLength - tip_margin,
            self.HitchLatchNeckWidth + self.HitchWidth / 2.0,
            d=self.HitchPinDiameter + self.HitchSlotClearance
        )

    def renderHitchParts(self):
        """Render polygon hitch tongue and octagonal front guide plate."""
        if not self.AddHitchJoint:
            return

        self.ctx.save()
        # Approximate a rounded right end with 3 chord segments (45 deg each).
        end_chord = self.HitchWidth / (1 + 2*math.sin(math.radians(45)))

        tongue_borders = [
            # lower neck
            self.HitchLatchArmLength, 90,
            self.HitchLatchNeckWidth, -90,
            # length
            self.HitchLength + self.thickness, 0,
            # front rounded end
            end_chord/2, 45,
            end_chord, 45,
            end_chord, 45,
            end_chord, 45,
            end_chord/2, 0,
            # length
            self.HitchLength + self.thickness, -90,
            # upper neck
            self.HitchLatchNeckWidth, 90,
            self.HitchLatchArmLength, 90,
            # back with clip insert
            self.HitchLatchNeckWidth + self.HitchWidth/2 - self.thickness/2 - self.burn, 90,
            self.thickness, -90,
            self.thickness, -90,
            self.thickness, 90,
            self.HitchLatchNeckWidth + self.HitchWidth/2 - self.thickness/2 - self.burn, 90,
            #self.HitchWidth+2*self.HitchLatchNeckWidth, 90
        ]
        self.polygonWall(
            borders=tongue_borders,
            edge="e",
            callback=[lambda: self.hitchConnectorFeatures()],
            move="right",
            label="Hitch Tongue",
        )

        hitch_secure_borders = [
            self.HitchLatchArmLength + self.HitchSecurerThickness, 90,
            self.HitchSecurerThickness, 90,
            self.HitchLatchArmLength, -90,
            self.thickness, -90,
            self.HitchLatchArmLength, 90,
            self.HitchSecurerThickness, 90,
            self.HitchLatchArmLength + self.HitchSecurerThickness, 90,
            self.thickness + 2* self.HitchSecurerThickness, 90
        ]
        self.polygonWall(
            borders=hitch_secure_borders,
            edge="e",
            move="up",
            label="Hitch Securer",
        )

        self.ctx.restore()
        self.polygonWall(
            borders=tongue_borders,
            edge="e",
            move="up only",
            label="Move cursor up",
        )

    def renderLidParts(self, l, b):
        """Render the lid panel if enabled."""
        self.ctx.save()
        if self.AddLid:
            if self.SplitLid:
                split_ratio = self.LidSplitRatio
                if split_ratio <= 0.0 or split_ratio >= 1.0:
                    split_ratio = 0.5
                rear_len = l * split_ratio
                front_len = l - rear_len
                self._lid_rear_len = rear_len
                self._lid_front_len = front_len

                self.rectangularWall(
                    front_len,
                    b,
                    ["I", "e", "J", "e"],
                    move="right",
                    label="Front Lid",
                )
                self.rectangularWall(
                    rear_len,
                    b,
                    ["f", "f", "f", "e"],
                    callback=[
                        lambda: self.lidArucoFeatures(rear_len, b),
                        None,
                        None,
                        None,
                    ],
                    move="up",
                    label="Rear Lid",
                )
            else:
                self._lid_rear_len = l
                self._lid_front_len = 0.0
                self.rectangularWall(
                    l,
                    b,
                    "ffff",
                    callback=[
                        lambda: self.lidArucoFeatures(l, b),
                        None,
                        None,
                        None,
                    ],
                    move="up",
                    label="Lid",
                )
        else:
            self._lid_rear_len = 0.0
            self._lid_front_len = 0.0
        self.ctx.restore()
        self.rectangularWall(l, b, "ffff", move="only up", label="Move cursor up") 

    def render(self):
        """Generate all parts: bottom, walls, optional lid, and feature cutouts."""
        l, b, h = self.x, self.y, self.h

        self.rectangularWall(l, b, "ffff", move="up", label="Bottom")
        self.renderLidParts(l, b)

        if self.MakeStackable:
            frontEdges = "sfSf"
            sideEdges = "sFSF"
            frontEdgesNoTop = "sfef"
            sideTopEdgeRear = "S"
        else:
            frontEdges = "sfef"
            sideEdges = "sFeF"
            frontEdgesNoTop = "sfef"
            sideTopEdgeRear = "e"

        if self.SplitLid:
            frontEdges = "sfSf" if self.MakeStackable else "sfef"

        # rectangularWall callback slots are ordered as [bottom, right, top, left].
        # Side panels: bottom slot adds rear axle hole, top slot adds opening + lid finger holes.
        self.rectangularWall(l, h, sideEdges, callback=[lambda: self.sideBottomFeatures(l, h), None, lambda: self.sideTopFeatures(l), None], ignore_widths=[1, 6], move="up", label="side1")
        self.rectangularWall(l, h, sideEdges, callback=[lambda: self.sideBottomFeatures(l, h, mirrored=True), None, lambda: self.sideTopFeatures(l), None], ignore_widths=[1, 6], move="mirror up", label="side2")

        # Front/back panels: top slot adds openings/finger holes; callbacks also add hitch features.
        self.ctx.save()
        self.rectangularWall(b, h, frontEdges, callback=[lambda: self.frontBottomFeatures(b), None, lambda: self.frontTopFeatures(b), None], ignore_widths=[1, 6], move="right", label="front")
        backEdges = "sfSf" if (self.MakeStackable and not self.SplitLid) else ("sfSf" if self.MakeStackable else "sfef")
        self.rectangularWall(b, h, backEdges, callback=[lambda: self.backBottomFeatures(b), None, lambda: self.backTopFeatures(b), None], ignore_widths=[1, 6], move="up", label="back")
        self.ctx.restore()
        self.rectangularWall(b, h, backEdges, move="only up", label="Move cursor up")

        self.renderChuteParts()

        self.renderHitchParts()

