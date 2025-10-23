#!/usr/bin/env python3
"""
Exact jigsaw piece extractor with smooth curve rendering.

Uses a simple and reliable flood-fill approach: render all cut lines,
then flood-fill from the center of each piece. This guarantees correct
piece boundaries with smooth anti-aliased edges.
"""

import argparse
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import cairosvg
import io
import numpy as np
from collections import deque


def parse_arguments():
    """Parse command line arguments - maintains same interface as jigsaw_piece_extractor.py"""
    parser = argparse.ArgumentParser(
        description="Extract puzzle pieces with exact smooth curve rendering from SVG outline"
    )
    parser.add_argument("image", help="Input image (e.g. PNG or JPG)")
    parser.add_argument("layout", help="Puzzle outline SVG file")
    parser.add_argument("--output", default="pieces", help="Output folder for pieces")
    return parser.parse_args()


def extract_svg_info(svg_file):
    """Extract dimensions and cut paths from the SVG outline file"""
    tree = ET.parse(svg_file)
    root = tree.getroot()
    
    # Extract dimensions
    width = float(root.attrib.get("width", "1024").replace("mm", "").replace("px", ""))
    height = float(root.attrib.get("height", "1024").replace("mm", "").replace("px", ""))
    
    # SVG namespace
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    # Extract horizontal and vertical cut paths
    horizontal_paths = []
    vertical_paths = []
    
    for path in root.findall(".//svg:path", ns):
        cls = path.attrib.get("class", "")
        path_d = path.attrib.get("d", "")
        
        if "horizontal" in cls:
            horizontal_paths.append(path_d)
        elif "vertical" in cls:
            vertical_paths.append(path_d)
    
    return {
        'width': int(width),
        'height': int(height),
        'horizontal_cuts': horizontal_paths,
        'vertical_cuts': vertical_paths
    }


def render_grid_with_cuts(svg_info, target_width, target_height):
    """
    Render an image showing all the cut lines as black lines on white background.
    The cuts should be rendered as infinitely thin (no stroke width).
    """
    width = svg_info['width']
    height = svg_info['height']
    
    # Build SVG with all cuts
    svg_parts = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="white"/>''']
    
    # Add all horizontal cuts as filled shapes (very thin)
    for h_path in svg_info['horizontal_cuts']:
        # Render as stroke with minimal width for anti-aliasing
        svg_parts.append(f'  <path d="{h_path}" stroke="black" stroke-width="1" fill="none"/>')
    
    # Add all vertical cuts as filled shapes (very thin)
    for v_path in svg_info['vertical_cuts']:
        svg_parts.append(f'  <path d="{v_path}" stroke="black" stroke-width="1" fill="none"/>')
    
    svg_parts.append('</svg>')
    svg_content = '\n'.join(svg_parts)
    
    # Render to image
    png_data = cairosvg.svg2png(
        bytestring=svg_content.encode('utf-8'),
        output_width=target_width,
        output_height=target_height
    )
    
    grid_image = Image.open(io.BytesIO(png_data)).convert('L')
    return grid_image


def flood_fill_piece(grid_array, seed_x, seed_y, target_width, target_height):
    """
    Flood fill from a seed point to find all pixels belonging to a piece.
    Returns a boolean mask array.
    """
    mask = np.zeros((target_height, target_width), dtype=bool)
    visited = np.zeros((target_height, target_width), dtype=bool)
    
    # Threshold for what counts as "white" (not a cut line)
    # Use 200 to allow for anti-aliased edges
    WHITE_THRESHOLD = 200
    
    queue = deque([(seed_y, seed_x)])
    visited[seed_y, seed_x] = True
    
    while queue:
        y, x = queue.popleft()
        
        # If this pixel is white (not a cut line), include it
        if grid_array[y, x] > WHITE_THRESHOLD:
            mask[y, x] = True
            
            # Add neighbors (4-connected)
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if (0 <= ny < target_height and 0 <= nx < target_width and 
                    not visited[ny, nx]):
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        else:
            # Hit a cut line - mark as boundary
            mask[y, x] = False
    
    return mask


def create_piece_mask_flood_fill(svg_info, row, col, rows, cols, grid_array, target_width, target_height):
    """
    Create a mask for a piece by flood-filling from its center point.
    """
    piece_width = target_width / cols
    piece_height = target_height / rows
    
    # Calculate seed point at the center of this piece's grid cell
    seed_x = int((col + 0.5) * piece_width)
    seed_y = int((row + 0.5) * piece_height)
    
    # Flood fill to find all pixels in this piece
    mask_array = flood_fill_piece(grid_array, seed_x, seed_y, target_width, target_height)
    
    # Convert to grayscale image (255 for piece, 0 for background)
    mask_image = Image.fromarray((mask_array * 255).astype(np.uint8), mode='L')
    
    # Apply slight dilation to include anti-aliased edge pixels
    # This ensures we don't lose the smooth edges
    from PIL import ImageFilter
    mask_image = mask_image.filter(ImageFilter.MaxFilter(3))
    
    return mask_image


def extract_pieces_exact(image_path, svg_file, output_dir):
    """
    Extract puzzle pieces using flood-fill approach for reliable boundary detection.
    """
    # Load the input image
    img = Image.open(image_path).convert("RGBA")
    img_width, img_height = img.size
    
    # Parse SVG to get cut information
    svg_info = extract_svg_info(svg_file)
    svg_width = svg_info['width']
    svg_height = svg_info['height']
    
    # Calculate grid dimensions
    rows = len(svg_info['horizontal_cuts']) + 1
    cols = len(svg_info['vertical_cuts']) + 1
    
    print(f"Extracting {rows}×{cols} puzzle pieces")
    print(f"SVG dimensions: {svg_width}×{svg_height}")
    print(f"Image dimensions: {img_width}×{img_height}")
    
    # Render the grid with all cuts
    print("Rendering cut lines...")
    grid_image = render_grid_with_cuts(svg_info, img_width, img_height)
    grid_array = np.array(grid_image)
    
    # Create output directory
    pieces_dir = os.path.join(output_dir, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)
    
    # Extract each piece
    for row in range(rows):
        for col in range(cols):
            print(f"Processing piece {row}_{col}...", end=" ")
            
            # Create mask using flood fill
            mask = create_piece_mask_flood_fill(
                svg_info, row, col, rows, cols, 
                grid_array, img_width, img_height
            )
            
            # Create piece image with transparent background
            piece = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            piece.paste(img, (0, 0), mask)
            
            # Save piece
            piece_filename = f"{row}_{col}.png"
            piece_path = os.path.join(pieces_dir, piece_filename)
            piece.save(piece_path)
            
            print(f"✓")
    
    print(f"\nSuccessfully extracted {rows * cols} pieces to {pieces_dir}")


def main():
    args = parse_arguments()
    
    # Validate inputs
    if not os.path.exists(args.image):
        print(f"Error: Image file '{args.image}' not found")
        return 1
    
    if not os.path.exists(args.layout):
        print(f"Error: Layout file '{args.layout}' not found")
        return 1
    
    # Extract pieces
    extract_pieces_exact(args.image, args.layout, args.output)
    
    return 0


if __name__ == "__main__":
    exit(main())
