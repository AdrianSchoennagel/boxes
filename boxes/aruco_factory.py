from __future__ import annotations

"""Utilities for generating and drawing OpenCV ArUco markers in Boxes.

This module mirrors the split used for QR support by keeping marker creation
and rendering helpers out of individual generators.
"""

from boxes.Color import Color

ARUCO_DICTIONARY_CHOICES = (
    "DICT_4X4_50",
    "DICT_4X4_100",
    "DICT_4X4_250",
    "DICT_4X4_1000",
    "DICT_5X5_50",
    "DICT_5X5_100",
    "DICT_5X5_250",
    "DICT_5X5_1000",
    "DICT_6X6_50",
    "DICT_6X6_100",
    "DICT_6X6_250",
    "DICT_6X6_1000",
    "DICT_7X7_50",
    "DICT_7X7_100",
    "DICT_7X7_250",
    "DICT_7X7_1000",
    "DICT_ARUCO_ORIGINAL",
)


def _get_aruco_image(dictionary_name: str, marker_id: int, pixels: int = 200, border_bits: int = 1):
    """Return an official OpenCV ArUco marker raster and module-cell count.

    The returned `cells` value includes the marker border bits so callers can
    map raster samples back to module-sized rectangles.
    """
    try:
        import cv2
    except Exception as exc:
        raise RuntimeError("AddLidArucoEtching requires OpenCV (opencv-contrib-python).") from exc

    if not hasattr(cv2, "aruco"):
        raise RuntimeError("OpenCV ArUco module is unavailable. Install opencv-contrib-python.")

    dictionary_name = str(dictionary_name).upper()
    dictionary_id = getattr(cv2.aruco, dictionary_name, None)
    if dictionary_id is None:
        raise ValueError(f"Unknown ArUco dictionary: {dictionary_name}")

    dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
    marker_count = dictionary.bytesList.shape[0]
    # Keep IDs in range for the selected dictionary.
    marker_id = int(marker_id) % marker_count
    image = cv2.aruco.generateImageMarker(dictionary, marker_id, max(40, int(pixels)), borderBits=border_bits)
    cells = dictionary.markerSize + 2 * border_bits
    return image, cells


def _draw_aruco_marker(ctx, image, cells: int, x: float, y: float, size: float) -> None:
    """Draw marker dark modules as context rectangles at target position/size."""
    module = size / cells
    for row in range(cells):
        for col in range(cells):
            # Convert module coordinates to raster sample coordinates.
            sample_row = cells - 1 - row
            py = int((sample_row + 0.5) * image.shape[0] / cells)
            px = int((col + 0.5) * image.shape[1] / cells)
            if image[py, px] < 128:
                ctx.rectangle(
                    x + col * module,
                    y + row * module,
                    module,
                    module,
                )


def etch_aruco(
    box,
    panel_w: float,
    panel_h: float,
    dictionary_name: str,
    marker_id: int,
    marker_size: float,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    callback_edge_char: str | None = None,
) -> None:
    """Generate and etch an ArUco marker on a panel in one call.

    This helper handles marker generation, panel fitting, optional callback-edge
    coordinate correction, and color switching to etching.

    ---
    Args:
        box: The Boxes instance to draw on.
        panel_w: Width of the target panel in mm.
        panel_h: Height of the target panel in mm.
        dictionary_name: OpenCV ArUco dictionary name (e.g. "DICT_5X5_100").
        marker_id: Numeric marker ID within the selected dictionary.
        marker_size: Overall marker size on the panel in mm.
        offset_x: Marker X offset from panel center in mm (default 0).
        offset_y: Marker Y offset from panel center in mm (default 0).
        callback_edge_char: Optional edge character for callback coordinate correction.
    """
    image, cells = _get_aruco_image(dictionary_name, marker_id)
    size = min(float(marker_size), panel_w - 2.0, panel_h - 2.0)
    if size <= 0:
        return

    ox = (panel_w - size) / 2.0 + float(offset_x)
    oy = (panel_h - size) / 2.0 + float(offset_y)

    with box.saved_context():
        if callback_edge_char is not None:
            # rectangularWall callbacks are offset by edge start width.
            base_y = -(box.edges[callback_edge_char].startWidth() + box.burn)
            box.moveTo(0, base_y)
        box.set_source_color(Color.ETCHING)
        _draw_aruco_marker(box.ctx, image, cells, ox, oy, size)
        # Restore default drawing color expected by most generators.
        box.set_source_color(Color.BLACK)
