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

        # Opening and assembly feature toggles.
        self.argparser.add_argument("--AddSideOpenings", action="store", type=boolarg, default=True, help="add side openings")
        self.argparser.add_argument("--AddFrontOpenings", action="store", type=boolarg, default=False, help="add front and back openings")
        self.argparser.add_argument("--OpeningTopOffset", action="store", type=float, default=20.0, help="offset of the opening hole from top edge")
        self.argparser.add_argument("--OpeningSideOffset", action="store", type=float, default=15.0, help="offset of the opening hole from side edge")
        self.argparser.add_argument("--OpeningBottomOffset", action="store", type=float, default=20.0, help="offset of the opening hole from bottom edge")
        self.argparser.add_argument("--OpeningRadius", action="store", type=float, default=5, help="opening hole radius")
        self.argparser.add_argument("--MakeStackable", action="store", type=boolarg, default=True, help="make crates stackable")
        # self.argparser.add_argument("--AddPatternMask", action="store", type=boolarg, default=False, help="add pattern mask")

        self.argparser.add_argument("--AddLid", action="store", type=boolarg, default=True, help="add a lid panel")
        self.argparser.add_argument("--AddLidArucoEtching", action="store", type=boolarg, default=False, help="add an ArUco marker etching on the lid")
        self.argparser.add_argument("--LidArucoId", action="store", type=int, default=0, help="numeric ArUco marker id")
        self.argparser.add_argument(
            "--LidArucoDictionary",
            action="store",
            type=str,
            choices=ARUCO_DICTIONARY_CHOICES,
            default="DICT_5X5_100",
            help="OpenCV ArUco dictionary name",
        )
        self.argparser.add_argument("--LidArucoSize", action="store", type=float, default=70.0, help="overall marker size on lid in mm")
        self.argparser.add_argument("--LidArucoOffsetX", action="store", type=float, default=0.0, help="marker X offset from lid center in mm")
        self.argparser.add_argument("--LidArucoOffsetY", action="store", type=float, default=0.0, help="marker Y offset from lid center in mm")

        self.argparser.add_argument("--AxleDiameter", action="store", type=float, default=3.0, help="diameter of the axle hole in mm")
        self.argparser.add_argument("--AddHitchJoint", action="store", type=boolarg, default=True, help="add hitch joint features and parts")
        self.argparser.add_argument("--HitchLength", action="store", type=float, default=100.0, help="hitch connector length in mm. This is the distance from the front edge of the trailer to the center of the hitch pin hole.")
        self.argparser.add_argument("--HitchWidth", action="store", type=float, default=10.0, help="hitch connector width in mm")
        self.argparser.add_argument("--HitchPinDiameter", action="store", type=float, default=5.0, help="rear wall pin-hole diameter in mm")
        self.argparser.add_argument("--HitchPinOffsetBottom", action="store", type=float, default=65.0, help="vertical offset of hitch pin/slot from bottom in mm")
        self.argparser.add_argument("--HitchSlotClearance", action="store", type=float, default=0.3, help="extra clearance for front hitch slot in mm")
        self.argparser.add_argument("--HitchLatchArmLength", action="store", type=float, default=10.0, help="length of hitch tongue inside trailer in mm")
        self.argparser.add_argument("--HitchLatchNeckWidth", action="store", type=float, default=6.0, help="width of the neck of the hitch tongue (part inside trailer) in mm")
        self.argparser.add_argument("--HitchSecurerThickness", action="store", type=float, default=5.0, help="extra thickness of the hitch securer in mm")

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

    def topFingerHoles(self, width):
        """Add top finger-joint holes only when a matching lid is generated."""
        if not self.AddLid:
            return
        dist = self.fingerHolesAt.settings.edge_width
        self.fingerHolesAt(0, self.burn + dist + self.thickness / 2, width, 0)

    def sideTopFeatures(self, width):
        """Apply side-panel top-edge cutouts in callback order."""
        if self.AddSideOpenings:
            self.openingHole(width)
        self.topFingerHoles(width)

    def frontTopFeatures(self, width):
        """Apply front/back top-edge cutouts in callback order."""
        if self.AddFrontOpenings:
            self.openingHole(width)
        self.topFingerHoles(width)

    def frontBottomFeatures(self, width):
        """Apply front wall features including hitch slot."""
        if not self.AddHitchJoint:
            return

        # Front rectungular hole for the tongue to pass through
        slot_w = self.HitchWidth + self.HitchSlotClearance
        slot_h = self.thickness + self.HitchSlotClearance
        y_center = self.HitchPinOffsetBottom
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
        self.frontTopFeatures(width)

    def backBottomFeatures(self, width):
        """Apply back wall features including rear pin hole."""
        if not self.AddHitchJoint:
            return

        # Rear cutout with a central pin rising from the bottom:
        # top window + two lower side windows leave a center tongue (pin).
        pin_w = self.HitchPinDiameter
        pin_h = max(self.HitchPinDiameter * 1.4, self.thickness * 1.2)
        outer_w = max(self.HitchWidth * 1.8, pin_w + 6.0)
        side_w = max((outer_w - pin_w) / 2.0, 1.0)
        top_h = self.thickness * 1.1

        y_pin = self.HitchPinOffsetBottom
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
            move="left",
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
            borders=tongue_borders,
            edge="e",
            move="right only", # doesnt draw, oly moves cursor
            label="",
        )
        self.polygonWall(
            borders=hitch_secure_borders,
            edge="e",
            move="",
            label="Hitch Securer",
        )

    def render(self):
        """Generate all parts: bottom, walls, optional lid, and feature cutouts."""
        l, b, h = self.x, self.y, self.h

        self.rectangularWall(l, b, "ffff", move="up", label="Bottom")
        if self.AddLid:
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

        if self.MakeStackable:
            frontEdges = "sfSf"
            sideEdges = "sFSF"
        else:
            frontEdges = "sfef"
            sideEdges = "sFeF"

        # rectangularWall callback slots are ordered as [bottom, right, top, left].
        # Side panels: bottom slot adds rear axle hole, top slot adds opening + lid finger holes.
        self.rectangularWall(l, h, sideEdges, callback=[lambda: self.rearSideFootHole(l), None, lambda: self.sideTopFeatures(l), None], ignore_widths=[1, 6], move="up", label="side1")
        self.rectangularWall(l, h, sideEdges, callback=[lambda: self.rearSideFootHole(l), None, lambda: self.sideTopFeatures(l), None], ignore_widths=[1, 6], move="up", label="side2")

        # Front/back panels: top slot adds openings/finger holes; callbacks also add hitch features.
        self.rectangularWall(b, h, frontEdges, callback=[lambda: self.frontBottomFeatures(b), None, lambda: self.frontTopFeatures(b), None], ignore_widths=[1, 6], move="right", label="front")
        self.rectangularWall(b, h, frontEdges, callback=[lambda: self.backBottomFeatures(b), None, lambda: self.backTopFeatures(b), None], ignore_widths=[1, 6], move="up", label="back")

        self.renderHitchParts()

