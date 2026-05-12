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


class Trailer(Boxes):
    """Trailer with Lid, optional side-openings, optional lid, axle hole, and hitch-joints."""

    description = """X is length in direction of the hitch, Y is width, H is height. The trailer has a lid and optional side-openings.
    The side-openings can be customized with the Openings* parameters. If MakeStackable is true, the trailer will have a lip on the bottom and stabilizers on the sides to make it stackable."""
    ui_group = "Box"

    def __init__(self) -> None:
        """Register geometry options and default generator behavior."""
        Boxes.__init__(self)

        # Finger-joint and stackable-edge defaults for this generator.
        self.addSettingsArgs(edges.FingerJointSettings, bottom_lip=1.0)
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
        self.argparser.add_argument("--LidArucoDictionary", action="store", type=str, default="DICT_5X5_100", help="OpenCV ArUco dictionary name")
        self.argparser.add_argument("--LidArucoSize", action="store", type=float, default=32.0, help="overall marker size on lid in mm")
        self.argparser.add_argument("--LidArucoPixels", action="store", type=int, default=200, help="marker raster size used for ArUco sampling")
        self.argparser.add_argument("--LidArucoOffsetX", action="store", type=float, default=0.0, help="marker X offset from lid center in mm")
        self.argparser.add_argument("--LidArucoOffsetY", action="store", type=float, default=0.0, help="marker Y offset from lid center in mm")

        self.argparser.add_argument("--AxleDiameter", action="store", type=float, default=3.0, help="diameter of the axle hole in mm")

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

    def rearSideFootHole(self, width):
        """Place a round axle hole in the rear side foot."""
        stack = self.edges['s'].settings
        d = self.AxleDiameter
        self.hole(width - (d+1), -stack.height / 1, d=d)

    def _getArucoImage(self):
        """Return official OpenCV ArUco marker image and cell count."""
        try:
            import cv2
        except Exception as exc:
            raise RuntimeError("AddLidArucoEtching requires OpenCV (opencv-contrib-python).") from exc

        if not hasattr(cv2, "aruco"):
            raise RuntimeError("OpenCV ArUco module is unavailable. Install opencv-contrib-python.")

        dictionary_name = str(self.LidArucoDictionary).upper()
        dictionary_id = getattr(cv2.aruco, dictionary_name, None)
        if dictionary_id is None:
            raise ValueError(f"Unknown ArUco dictionary: {self.LidArucoDictionary}")

        dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        marker_count = dictionary.bytesList.shape[0]
        marker_id = int(self.LidArucoId) % marker_count
        pixels = max(40, int(self.LidArucoPixels))
        border_bits = 1
        image = cv2.aruco.generateImageMarker(dictionary, marker_id, pixels, borderBits=border_bits)
        cells = dictionary.markerSize + 2 * border_bits
        return image, cells

    def lidArucoEtching(self, lid_w, lid_h):
        """Etch an official ArUco marker on the lid using annotation color geometry."""
        if not (self.AddLid and self.AddLidArucoEtching):
            return

        image, cells = self._getArucoImage()
        requested_size = float(self.LidArucoSize)
        size = min(requested_size, lid_w - 2.0, lid_h - 2.0)
        if size <= 0:
            return

        module = size / cells
        ox = (lid_w - size) / 2.0 + float(self.LidArucoOffsetX)
        oy = (lid_h - size) / 2.0 + float(self.LidArucoOffsetY)

        # Callback origin for edge 0 is shifted by edge startWidth; move back into panel space.
        base_y = -(self.edges['f'].startWidth() + self.burn)
        with self.saved_context():
            self.moveTo(0, base_y)
            for row in range(cells):
                for col in range(cells):
                    sample_row = cells - 1 - row
                    py = int((sample_row + 0.5) * image.shape[0] / cells)
                    px = int((col + 0.5) * image.shape[1] / cells)
                    if image[py, px] < 128:
                        self.rectangularHole(
                            ox + col * module,
                            oy + row * module,
                            module,
                            module,
                            r=0,
                            center_x=False,
                            center_y=False,
                            color=Color.ANNOTATIONS,
                        )

    def render(self):
        """Generate all parts: bottom, walls, optional lid, and feature cutouts."""
        l, b, h = self.x, self.y, self.h

        self.rectangularWall(l, b, "ffff", move="up", label="Bottom")
        if self.AddLid:
            self.rectangularWall(l, b, "ffff", callback=[lambda: self.lidArucoEtching(l, b), None, None, None], move="up", label="Lid")

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

        # Front/back panels: top slot adds opening + lid finger holes.
        self.rectangularWall(b, h, frontEdges, callback=[None, None, lambda: self.frontTopFeatures(b), None], ignore_widths=[1, 6], move="right", label="front")
        self.rectangularWall(b, h, frontEdges, callback=[None, None, lambda: self.frontTopFeatures(b), None], ignore_widths=[1, 6], move="up", label="back")

