#!/usr/bin/env python3
"""
Extract puzzle pieces from an image using jigsaw cut paths from an SVG.

Uses cairosvg to render cut lines with native bezier support, then
flood-fills from each cell center to identify piece regions.  Boundary
pixels (the rendered cut lines) are assigned to the nearest piece so
that every pixel is accounted for exactly once.
"""

import argparse
import hashlib
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import deque

import cairosvg
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract puzzle pieces from an image using SVG cut paths"
    )
    parser.add_argument("image", help="Input image (PNG or JPG)")
    parser.add_argument("svg", help="Jigsaw SVG file with horizontal/vertical cut paths")
    parser.add_argument("--output", default="pieces", help="Output directory (default: pieces)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# SVG parsing
# ---------------------------------------------------------------------------

def _split_subpaths(d):
    """Split a d attribute with multiple M commands into individual subpaths."""
    parts = re.split(r"(?=M\s*[\d.])", d.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_interior_cut(d):
    """Return True if the subpath is an interior cut (has curves), not a border line."""
    return "C" in d


def parse_svg(svg_path):
    """Extract viewBox dimensions and classified cut paths from SVG.

    Handles both combined format (all cuts in one <path> element) and
    split format (each cut in its own <path> element).  Border lines
    (straight M…L paths without curves) are included for rendering but
    excluded from the grid-size count.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    viewbox = root.attrib.get("viewBox", "0 0 1 1").split()
    vb_width, vb_height = float(viewbox[2]), float(viewbox[3])

    ns = {"svg": "http://www.w3.org/2000/svg"}
    horizontal, vertical, border = [], [], []

    for path in root.findall(".//svg:path", ns):
        d = path.attrib.get("d", "")
        cls = set(path.attrib.get("class", "").split())
        if "horizontal" in cls:
            horizontal.extend(_split_subpaths(d))
        elif "vertical" in cls:
            vertical.extend(_split_subpaths(d))
        elif "border" in cls:
            border.append(d)

    # Count only interior cuts (curves) for grid dimensions
    h_interior = [p for p in horizontal if _is_interior_cut(p)]
    v_interior = [p for p in vertical if _is_interior_cut(p)]
    rows = len(h_interior) + 1
    cols = len(v_interior) + 1

    return vb_width, vb_height, horizontal, vertical, border, rows, cols


# ---------------------------------------------------------------------------
# Cut-line rendering via cairosvg
# ---------------------------------------------------------------------------

def render_cut_lines(svg_path, vb_w, vb_h, h_paths, v_paths, b_paths, target_w, target_h):
    """Render all cut paths as thin black lines on a white background.

    Uses cairosvg for native bezier rendering — curves are smooth and exact.
    Returns a grayscale numpy array (target_h, target_w).
    """
    # Stroke width: 3 pixels in viewBox units — thick enough to seal
    # the narrow neck gaps where tab curves double back on themselves.
    # Boundary pixels are reclaimed by the dilation step after flood fill.
    sw = 3.0 * vb_w / target_w

    svg_parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{vb_w}" height="{vb_h}"'
        f' viewBox="0 0 {vb_w} {vb_h}">',
        f'  <rect width="{vb_w}" height="{vb_h}" fill="white"/>',
    ]

    for d in h_paths:
        svg_parts.append(
            f'  <path d="{d}" stroke="black" stroke-width="{sw}" fill="none"/>'
        )
    for d in v_paths:
        svg_parts.append(
            f'  <path d="{d}" stroke="black" stroke-width="{sw}" fill="none"/>'
        )
    for d in b_paths:
        svg_parts.append(
            f'  <path d="{d}" stroke="black" stroke-width="{sw}" fill="none"/>'
        )

    svg_parts.append("</svg>")
    svg_content = "\n".join(svg_parts)

    png_data = cairosvg.svg2png(
        bytestring=svg_content.encode("utf-8"),
        output_width=target_w,
        output_height=target_h,
    )

    grid = np.array(Image.open(io.BytesIO(png_data)).convert("L"))

    # Paint solid black borders so flood fills can't escape at image edges
    # even if the SVG has no explicit border path.
    bw = max(2, int(sw * target_w / vb_w) + 1)
    grid[:bw, :] = 0
    grid[-bw:, :] = 0
    grid[:, :bw] = 0
    grid[:, -bw:] = 0

    return grid


# ---------------------------------------------------------------------------
# Flood fill
# ---------------------------------------------------------------------------

def flood_fill(grid, seed_y, seed_x, threshold=128):
    """Flood-fill from seed on white pixels (value > threshold).

    Returns a boolean mask of the filled region.
    """
    h, w = grid.shape
    mask = np.zeros((h, w), dtype=bool)

    if grid[seed_y, seed_x] <= threshold:
        return mask

    queue = deque([(seed_y, seed_x)])
    mask[seed_y, seed_x] = True

    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not mask[ny, nx] and grid[ny, nx] > threshold:
                mask[ny, nx] = True
                queue.append((ny, nx))

    return mask


# ---------------------------------------------------------------------------
# Piece extraction
# ---------------------------------------------------------------------------

def extract_pieces(image_path, svg_path, output_dir):
    img = Image.open(image_path).convert("RGBA")
    img_w, img_h = img.size
    img_array = np.array(img)

    vb_w, vb_h, h_paths, v_paths, b_paths, rows, cols = parse_svg(svg_path)

    print(f"Grid: {cols}x{rows}, Image: {img_w}x{img_h}")

    # Render cuts using cairosvg — native bezier curves, no polyline approx.
    print("Rendering cut lines (cairosvg)...")
    grid = render_cut_lines(svg_path, vb_w, vb_h, h_paths, v_paths, b_paths, img_w, img_h)

    # Flood-fill each piece from its grid-cell center
    cell_w = img_w / cols
    cell_h = img_h / rows

    pieces_dir = os.path.join(output_dir, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)

    print("Flood-filling pieces...")
    piece_masks = {}
    claimed = np.zeros((img_h, img_w), dtype=bool)

    for r in range(rows):
        for c in range(cols):
            seed_x = int((c + 0.5) * cell_w)
            seed_y = int((r + 0.5) * cell_h)
            mask = flood_fill(grid, seed_y, seed_x)
            piece_masks[(r, c)] = mask
            claimed |= mask

    # Assign unclaimed pixels (cut-line pixels) to nearest piece via Euclidean
    # distance transform.  Unlike BFS dilation, this prevents propagation
    # through connected unclaimed corridors (e.g. border strips).
    unclaimed_count = (~claimed).sum()
    print(f"Assigning {unclaimed_count} boundary pixels...")

    if unclaimed_count > 0:
        cell_map = np.full((img_h, img_w), -1, dtype=np.int32)
        keys = list(piece_masks.keys())
        for idx, key in enumerate(keys):
            cell_map[piece_masks[key]] = idx

        # For each unclaimed pixel, find the nearest claimed pixel's piece
        _, nearest_idx = distance_transform_edt(~claimed, return_distances=True, return_indices=True)
        unclaimed_ys, unclaimed_xs = np.where(~claimed)
        nearest_ys = nearest_idx[0][unclaimed_ys, unclaimed_xs]
        nearest_xs = nearest_idx[1][unclaimed_ys, unclaimed_xs]
        cell_map[unclaimed_ys, unclaimed_xs] = cell_map[nearest_ys, nearest_xs]

        for idx, key in enumerate(keys):
            piece_masks[key] |= (cell_map == idx)

    # Save pieces and collect metadata
    print("Extracting pieces...")
    piece_meta = []
    opt_pieces = {}
    full_canvas_bytes = img_w * img_h * 4  # hypothetical full-canvas RGBA per piece
    total_original_bytes = 0
    total_optimized_bytes = 0

    for (r, c), mask in piece_masks.items():
        ys, xs = np.where(mask)
        if len(ys) == 0:
            continue

        y0, y1 = ys.min(), ys.max() + 1
        x0, x1 = xs.min(), xs.max() + 1
        crop_mask = mask[y0:y1, x0:x1]

        piece = np.zeros((y1 - y0, x1 - x0, 4), dtype=np.uint8)
        piece[crop_mask] = img_array[y0:y1, x0:x1][crop_mask]

        piece_img = Image.fromarray(piece, "RGBA")
        piece_path = os.path.join(pieces_dir, f"{r}_{c}.png")
        piece_img.save(piece_path)
        print(f"  {r}_{c}.png ({x1 - x0}x{y1 - y0})")

        piece_id = f"{r}_{c}"
        pw, ph = int(x1 - x0), int(y1 - y0)
        cropped_bytes = pw * ph * 4

        piece_meta.append({
            "id": piece_id,
            "row": r,
            "col": c,
            "x": int(x0),
            "y": int(y0),
            "width": pw,
            "height": ph,
        })

        opt_pieces[piece_id] = {
            "bounds": {
                "left": int(x0),
                "top": int(y0),
                "right": int(x1),
                "bottom": int(y1),
                "width": pw,
                "height": ph,
            },
            "canvas_size": {"width": img_w, "height": img_h},
            "content_hash": hashlib.sha256(piece_img.tobytes()).hexdigest()[:8],
            "cropped_filename": f"{piece_id}.png",
        }

        total_original_bytes += full_canvas_bytes
        total_optimized_bytes += cropped_bytes

    # Write layout.ipuz.json with cut paths and piece positions.
    # If an existing file exists (e.g. from svg_to_ipuz.py with cutArrays),
    # merge our pieces/canvas/grid into it rather than overwriting.
    ipuz_path = os.path.join(output_dir, "layout.ipuz.json")
    if os.path.exists(ipuz_path):
        with open(ipuz_path) as f:
            ipuz = json.load(f)
        print(f"Merging piece data into existing {ipuz_path}")
    else:
        ipuz = {
            "version": "http://ipuz.org/v2",
            "kind": ["http://ipuz.org/jigsaw#1"],
        }
    ipuz["canvas"] = {"width": img_w, "height": img_h}
    ipuz["grid"] = {"rows": rows, "cols": cols}
    ipuz["pieces"] = sorted(piece_meta, key=lambda p: (p["row"], p["col"]))

    with open(ipuz_path, "w") as f:
        json.dump(ipuz, f, indent=2)
    print(f"Wrote layout metadata to {ipuz_path}")

    # Write optimization_metadata.json (compatible with puzzlenook format)
    bytes_saved = total_original_bytes - total_optimized_bytes
    opt_meta = {
        "version": "1.0",
        "canvas_size": {"width": img_w, "height": img_h},
        "pieces": opt_pieces,
        "statistics": {
            "memory_reduction_percent": (bytes_saved / total_original_bytes * 100) if total_original_bytes > 0 else 0.0,
            "total_pieces": len(opt_pieces),
            "original_total_bytes": total_original_bytes,
            "optimized_total_bytes": total_optimized_bytes,
            "bytes_saved": bytes_saved,
        },
    }
    opt_path = os.path.join(output_dir, "optimization_metadata.json")
    with open(opt_path, "w") as f:
        json.dump(opt_meta, f, indent=2)
    print(f"Wrote optimization metadata to {opt_path}")

    print(f"\nExtracted {rows * cols} pieces to {pieces_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_arguments()

    if not os.path.exists(args.image):
        print(f"Error: '{args.image}' not found")
        return 1
    if not os.path.exists(args.svg):
        print(f"Error: '{args.svg}' not found")
        return 1

    extract_pieces(args.image, args.svg, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
