#!/usr/bin/env python3

import argparse
import os
import json
import numpy as np
from PIL import Image, ImageDraw
import math

# Disable DecompressionBombWarning for large images
Image.MAX_IMAGE_PIXELS = None

import tempfile
import sys
import re
from cairosvg import svg2png
import xml.etree.ElementTree as ET
import shutil

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Extract jigsaw puzzle pieces from an image using an SVG outline template'
    )
    parser.add_argument('image', type=str, help='Input image to be cut into puzzle pieces')
    parser.add_argument('svg', type=str, help='SVG file defining the jigsaw cuts')
    parser.add_argument('-o', '--output', type=str, default='pieces',
                        help='Output folder for the puzzle pieces (default: pieces)')
    parser.add_argument('--prefix', type=str, default='piece',
                        help='Prefix for output filenames (default: piece)')
    parser.add_argument('--format', type=str, default='png',
                        help='Output image format (default: png)')
    parser.add_argument('--padding', type=int, default=30,
                        help='Padding around pieces in pixels (default: 30)')
    parser.add_argument('--fixed-size', action='store_true',
                        help='Output all pieces with the same dimensions')
    parser.add_argument('--output-width', type=int, default=None,
                        help='Fixed width for output pieces (default: auto-calculated)')
    parser.add_argument('--output-height', type=int, default=None,
                        help='Fixed height for output pieces (default: auto-calculated)')
    parser.add_argument('--debug', action='store_true',
                        help='Save debug images')
    parser.add_argument('--puzzle-name', type=str, default='puzzle_01',
                        help='Name of the puzzle folder (default: puzzle_01)')
    parser.add_argument('--layout-name', type=str, default=None,
                        help='Name of the layout folder (default: derived from grid size)')
    parser.add_argument('--show-handles', action='store_true',
                        help='Draw a red crosshair on each piece at the handle pixel location')

    return parser.parse_args()

def get_svg_dimensions(svg_file):
    """Extract dimensions from SVG file"""
    tree = ET.parse(svg_file)
    root = tree.getroot()
    
    # Look for viewBox attribute
    if 'viewBox' in root.attrib:
        viewbox = root.attrib['viewBox'].split()
        width = float(viewbox[2])
        height = float(viewbox[3])
    else:
        # Look for width and height attributes
        width = height = None
        if 'width' in root.attrib:
            width_str = root.attrib['width']
            width = float(width_str.replace('mm', '').strip())
        if 'height' in root.attrib:
            height_str = root.attrib['height']
            height = float(height_str.replace('mm', '').strip())
        
        # Default values if nothing found
        if width is None: width = 300
        if height is None: height = 200
    
    return width, height

def determine_grid_size(svg_file):
    """Determine puzzle grid size from SVG file"""
    try:
        tree = ET.parse(svg_file)
        root = tree.getroot()
        
        # Get namespace
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Find path elements
        paths = root.findall('.//svg:path', ns)
        
        if len(paths) < 3:
            # Try without namespace
            paths = root.findall('.//path')
        
        if len(paths) < 3:
            print("Warning: Could not find enough paths in SVG file, using default grid size.")
            return 4, 4
        
        # Get horizontal and vertical divider paths
        h_path = v_path = None
        
        # Look for darkblue/darkred paths if available
        for path in paths:
            stroke = path.get('stroke', '').lower()
            if stroke == 'darkblue' or (h_path is None and stroke == 'black'):
                h_path = path
            elif stroke == 'darkred' or (v_path is None and h_path is not None and stroke == 'black'):
                v_path = path
        
        # If we couldn't find colored paths, use the first two paths
        if h_path is None and len(paths) > 0:
            h_path = paths[0]
        if v_path is None and len(paths) > 1:
            v_path = paths[1]
        
        # Count M commands to determine rows and columns
        rows = cols = None
        
        if h_path is not None and 'd' in h_path.attrib:
            h_path_data = h_path.attrib['d']
            # Count M commands to determine number of horizontal dividers
            h_dividers = h_path_data.count('M ')
            rows = h_dividers + 1
        
        if v_path is not None and 'd' in v_path.attrib:
            v_path_data = v_path.attrib['d']
            # Count M commands to determine number of vertical dividers
            v_dividers = v_path_data.count('M ')
            cols = v_dividers + 1
        
        # Default values if we couldn't determine
        if rows is None: rows = 4
        if cols is None: cols = 4
        
        # Get SVG dimensions
        width, height = get_svg_dimensions(svg_file)
        
        return cols, rows, width, height
        
    except Exception as e:
        print(f"Error determining grid size: {e}")
        # Default values if there's an error
        return 4, 4, 300, 200

def create_horizontal_cut_svg(svg_file, temp_dir, row, rows, direction):
    """Create an SVG file that shows a single horizontal cut line
    direction: 'above' or 'below'
    """
    # Get SVG dimensions
    width, height = get_svg_dimensions(svg_file)
    
    # Parse the original SVG to get the paths
    with open(svg_file, 'r') as f:
        svg_content = f.read()
    
    # Extract path elements
    path_pattern = r'<path[^>]*d="([^"]*)"[^>]*>'
    paths = re.findall(path_pattern, svg_content)
    
    if len(paths) < 3:
        print("Not enough paths found in the SVG file")
        return None
    
    # Get the horizontal divider paths
    h_paths = paths[0]
    
    # Split the horizontal paths into segments
    h_segments = h_paths.split('M ')
    h_segments = [seg for seg in h_segments if seg.strip()]
    
    # Get the segment for this row
    if direction == 'above' and row > 0:
        segment_index = row - 1
    elif direction == 'below' and row < rows - 1:
        segment_index = row
    else:
        # This is an edge piece with no cut on this side
        return None
    
    if segment_index < len(h_segments):
        segment = h_segments[segment_index]
    else:
        print(f"Segment index {segment_index} out of range for horizontal segments")
        return None
    
    # Create a new SVG with just this cut line
    cut_svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <path d="M {segment}" stroke="black" stroke-width="1" fill="none"/>
</svg>'''
    
    # Write the SVG file
    cut_svg_path = os.path.join(temp_dir, f"h_cut_{row}_{direction}.svg")
    with open(cut_svg_path, 'w') as f:
        f.write(cut_svg)
    
    return cut_svg_path

def create_vertical_cut_svg(svg_file, temp_dir, col, cols, direction):
    """Create an SVG file that shows a single vertical cut line
    direction: 'left' or 'right'
    """
    # Get SVG dimensions
    width, height = get_svg_dimensions(svg_file)
    
    # Parse the original SVG to get the paths
    with open(svg_file, 'r') as f:
        svg_content = f.read()
    
    # Extract path elements
    path_pattern = r'<path[^>]*d="([^"]*)"[^>]*>'
    paths = re.findall(path_pattern, svg_content)
    
    if len(paths) < 3:
        print("Not enough paths found in the SVG file")
        return None
    
    # Get the vertical divider paths
    v_paths = paths[1]
    
    # Split the vertical paths into segments
    v_segments = v_paths.split('M ')
    v_segments = [seg for seg in v_segments if seg.strip()]
    
    # Get the segment for this column
    if direction == 'left' and col > 0:
        segment_index = col - 1
    elif direction == 'right' and col < cols - 1:
        segment_index = col
    else:
        # This is an edge piece with no cut on this side
        return None
    
    if segment_index < len(v_segments):
        segment = v_segments[segment_index]
    else:
        print(f"Segment index {segment_index} out of range for vertical segments")
        return None
    
    # Create a new SVG with just this cut line
    cut_svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <path d="M {segment}" stroke="black" stroke-width="1" fill="none"/>
</svg>'''
    
    # Write the SVG file
    cut_svg_path = os.path.join(temp_dir, f"v_cut_{col}_{direction}.svg")
    with open(cut_svg_path, 'w') as f:
        f.write(cut_svg)
    
    return cut_svg_path

def create_border_cut_svg(svg_file, temp_dir, row, col, rows, cols):
    """Create an SVG file that shows the border cut lines for edge pieces"""
    # Get SVG dimensions
    width, height = get_svg_dimensions(svg_file)
    
    # Parse the original SVG to get the paths
    with open(svg_file, 'r') as f:
        svg_content = f.read()
    
    # Extract path elements
    path_pattern = r'<path[^>]*d="([^"]*)"[^>]*>'
    paths = re.findall(path_pattern, svg_content)
    
    if len(paths) < 3:
        print("Not enough paths found in the SVG file")
        return None
    
    # Get the border path
    border = paths[2]
    
    # Create a new SVG with just the border
    cut_svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <path d="{border}" stroke="black" stroke-width="1" fill="none"/>
</svg>'''
    
    # Write the SVG file
    cut_svg_path = os.path.join(temp_dir, f"border_cut.svg")
    with open(cut_svg_path, 'w') as f:
        f.write(cut_svg)
    
    return cut_svg_path

def create_cut_masks(svg_file, temp_dir, row, col, rows, cols, img_width, img_height, debug=False):
    """Create mask images for the four cuts around a piece"""
    cut_masks = {}
    
    # Create horizontal cut above this piece
    h_above_svg = create_horizontal_cut_svg(svg_file, temp_dir, row, rows, 'above')
    if h_above_svg:
        h_above_png = os.path.join(temp_dir, f"h_above_{row}_{col}.png")
        svg2png(url=h_above_svg, write_to=h_above_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['above'] = h_above_png
    
    # Create horizontal cut below this piece
    h_below_svg = create_horizontal_cut_svg(svg_file, temp_dir, row, rows, 'below')
    if h_below_svg:
        h_below_png = os.path.join(temp_dir, f"h_below_{row}_{col}.png")
        svg2png(url=h_below_svg, write_to=h_below_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['below'] = h_below_png
    
    # Create vertical cut to the left of this piece
    v_left_svg = create_vertical_cut_svg(svg_file, temp_dir, col, cols, 'left')
    if v_left_svg:
        v_left_png = os.path.join(temp_dir, f"v_left_{row}_{col}.png")
        svg2png(url=v_left_svg, write_to=v_left_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['left'] = v_left_png
    
    # Create vertical cut to the right of this piece
    v_right_svg = create_vertical_cut_svg(svg_file, temp_dir, col, cols, 'right')
    if v_right_svg:
        v_right_png = os.path.join(temp_dir, f"v_right_{row}_{col}.png")
        svg2png(url=v_right_svg, write_to=v_right_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['right'] = v_right_png
    
    # Create border cut for edge pieces
    if row == 0 or row == rows - 1 or col == 0 or col == cols - 1:
        border_svg = create_border_cut_svg(svg_file, temp_dir, row, col, rows, cols)
        if border_svg:
            border_png = os.path.join(temp_dir, f"border_{row}_{col}.png")
            svg2png(url=border_svg, write_to=border_png, 
                  output_width=img_width, output_height=img_height)
            cut_masks['border'] = border_png
    
    return cut_masks

def center_and_resize_image(image, target_width, target_height):
    """Center an image in a new image of the specified dimensions"""
    # Create a new transparent image with the target dimensions
    new_image = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
    
    # Calculate the position to center the original image
    x_offset = (target_width - image.width) // 2
    y_offset = (target_height - image.height) // 2
    
    # Paste the original image onto the new image
    new_image.paste(image, (x_offset, y_offset))
    
    return new_image

def ensure_centered_piece(piece_img, padding=30):
    """
    Ensure the piece is centered within its PNG image.
    Adds padding and centers the piece.
    """
    # Find the bounding box of non-transparent pixels
    bbox = piece_img.getbbox()
    if not bbox:
        return piece_img  # Return original if no bounding box
    
    # Crop to the bounding box
    cropped = piece_img.crop(bbox)
    
    # Calculate dimensions for the new centered image
    width = bbox[2] - bbox[0] + (padding * 2)
    height = bbox[3] - bbox[1] + (padding * 2)
    
    # Create a new transparent image
    centered = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    # Paste the cropped piece in the center
    paste_x = padding
    paste_y = padding
    centered.paste(cropped, (paste_x, paste_y))
    
    return centered

# This is the key function that needs to change
def extract_puzzle_pieces(input_image, svg_file, output_folder, prefix="piece", format="png", 
                         padding=0, fixed_size=True, output_width=None, output_height=None, 
                         debug=False, puzzle_name="puzzle_01", layout_name=None, show_handles=False):
    """Extract puzzle pieces by applying four cuts to each piece position"""
    
    # Create output directory
    os.makedirs(output_folder, exist_ok=True)
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    debug_dir = os.path.join(output_folder, "debug") if debug else None
    
    if debug:
        os.makedirs(debug_dir, exist_ok=True)
    else:
        # Always create debug dir for special pieces
        debug_dir = os.path.join(temp_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
    
    try:
        # Determine grid size
        cols, rows, svg_width, svg_height = determine_grid_size(svg_file)
        print(f"Detected puzzle grid: {cols} columns x {rows} rows")
        
        # Set layout name if not provided
        if layout_name is None:
            layout_name = f"{cols}x{rows}"
        
        # Create puzzle pack directory structure
        puzzle_dir = os.path.join(output_folder, puzzle_name)
        layouts_dir = os.path.join(puzzle_dir, "layouts")
        layout_dir = os.path.join(layouts_dir, layout_name)
        pieces_dir = os.path.join(layout_dir, "pieces")
        
        os.makedirs(puzzle_dir, exist_ok=True)
        os.makedirs(layouts_dir, exist_ok=True)
        os.makedirs(layout_dir, exist_ok=True)
        os.makedirs(pieces_dir, exist_ok=True)
        
        # Copy SVG file to layout directory
        shutil.copy(svg_file, os.path.join(layout_dir, "outline.svg"))
        
        # Open input image
        input_img = Image.open(input_image)
        img_width, img_height = input_img.size
        
        # Save a preview image
        preview_img = input_img.copy()
        if preview_img.mode != 'RGB':
            preview_img = preview_img.convert('RGB')
        preview_img.save(os.path.join(puzzle_dir, "preview.jpg"), quality=90)
        
        # Convert input image to RGBA if it's not already
        if input_img.mode != 'RGBA':
            input_img = input_img.convert('RGBA')
        
        # Calculate cell dimensions in pixels
        cell_width = img_width / cols
        cell_height = img_height / rows
        
        # IMPORTANT: Process all pieces independently without the allocation map
        # This ensures each piece gets its correct shape, even if they overlap
        for row in range(rows):
            for col in range(cols):
                print(f"Processing piece at position ({row}, {col})")
                
                # Create cut masks for this piece
                cut_masks = create_cut_masks(svg_file, temp_dir, row, col, rows, cols, 
                                          img_width, img_height, debug)
                
                # Start with a full white mask
                piece_mask = np.ones((img_height, img_width), dtype=np.uint8) * 255
                
                # Apply each cut mask
                for direction, mask_path in cut_masks.items():
                    # Load the cut mask
                    cut_mask = Image.open(mask_path).convert('L')
                    cut_array = np.array(cut_mask)
                    
                    # Threshold to ensure clean black/white
                    cut_array = (cut_array > 128).astype(np.uint8) * 255
                    
                    # Create a binary mask for the black pixels (the cut line)
                    cut_line = (cut_array == 0)
                    
                    # For each cut, we need to determine which side to keep
                    # and which side to discard
                    if direction == 'above':
                        # Keep pixels below the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for x in range(img_width):
                            # Find the first black pixel (cut line) from top to bottom
                            cut_point = None
                            for y in range(img_height):
                                if cut_line[y, x]:
                                    cut_point = y
                                    break
                            
                            if cut_point is not None:
                                # Discard all pixels above the cut
                                discard_pixels[:cut_point, x] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'below':
                        # Keep pixels above the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for x in range(img_width):
                            # Find the first black pixel (cut line) from bottom to top
                            cut_points = []
                            for y in range(img_height - 1, -1, -1):
                                if cut_line[y, x]:
                                    cut_points.append(y)
                            
                            if cut_points:
                                # Use the topmost cut point
                                cut_point = min(cut_points)
                                # Discard all pixels below the cut
                                discard_pixels[cut_point:, x] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'left':
                        # Keep pixels to the right of the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for y in range(img_height):
                            # Find the first black pixel (cut line) from left to right
                            cut_point = None
                            for x in range(img_width):
                                if cut_line[y, x]:
                                    cut_point = x
                                    break
                            
                            if cut_point is not None:
                                # Discard all pixels to the left of the cut
                                discard_pixels[y, :cut_point] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'right':
                        # Keep pixels to the left of the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for y in range(img_height):
                            # Find the first black pixel (cut line) from right to left
                            cut_point = None
                            for x in range(img_width - 1, -1, -1):
                                if cut_line[y, x]:
                                    cut_point = x
                                    break
                            
                            if cut_point is not None:
                                # Discard all pixels to the right of the cut
                                discard_pixels[y, cut_point:] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'border':
                        # For border pieces, handle each edge separately
                        if row == 0:  # Top edge
                            # Improved approach for top edge pieces
                            # Keep pixels below the border, but don't discard too much
                            
                            discard_pixels = np.zeros_like(cut_line)
                            for x in range(img_width):
                                # Find all black pixels (border line) in this column
                                border_indices = np.where(cut_line[:, x])[0]
                                
                                if len(border_indices) > 0:
                                    # Find the topmost border pixel
                                    # but only look in the top quarter of the image
                                    top_quarter = int(img_height * 0.25)
                                    top_border_pixels = [y for y in border_indices if y < top_quarter]
                                    
                                    if top_border_pixels:
                                        # Use the highest (topmost) border point
                                        # This ensures we keep the bulk of the piece
                                        border_point = min(top_border_pixels)
                                        # Only discard a small amount above this point
                                        safe_margin = max(5, int(cell_height * 0.05))  # 5% of cell height minimum
                                        if border_point > safe_margin:
                                            discard_pixels[:max(0, border_point - safe_margin), x] = True
                                    else:
                                        # If no border pixels in top quarter, just discard a few rows
                                        discard_pixels[:2, x] = True
                                else:
                                    # If no border pixels in this column, be very conservative
                                    discard_pixels[:2, x] = True
                            
                            # Apply the discard mask to the piece mask
                            piece_mask[discard_pixels] = 0
                        
                        if row == rows - 1:  # Bottom edge
                            # For bottom edge, just remove a few pixels at the bottom
                            # Be conservative to ensure we keep the piece content
                            piece_mask[-5:, :] = 0
                        
                        if col == 0:  # Left edge
                            # For left edge, just remove a few pixels at the left
                            piece_mask[:, :5] = 0
                        
                        if col == cols - 1:  # Right edge
                            # For right edge, just remove a few pixels at the right
                            piece_mask[:, -5:] = 0
                
                # IMPORTANT: Special check for top row pieces
                if row == 0:
                    # Make sure there are some non-zero pixels in the mask
                    if np.sum(piece_mask) == 0:
                        print(f"WARNING: No non-zero pixels in mask for top row piece ({row}, {col})")
                        # Force some pixels in this piece's cell area
                        start_y = int(row * cell_height)
                        end_y = int((row + 1) * cell_height)
                        start_x = int(col * cell_width)
                        end_x = int((col + 1) * cell_width)
                        
                        # Create a mask for this cell
                        cell_mask = np.zeros_like(piece_mask)
                        cell_mask[start_y:end_y, start_x:end_x] = 255
                        
                        # Use this as the piece mask
                        piece_mask = cell_mask
                
                # Convert mask to PIL
                mask_img = Image.fromarray(piece_mask)
                
                # Save mask for debugging
                if debug:
                    mask_img.save(os.path.join(debug_dir, f"piece_mask_{row}_{col}.png"))
                
                # Create the piece by applying the mask to the input image
                piece_img = Image.new('RGBA', input_img.size, (0, 0, 0, 0))
                piece_img.paste(input_img, (0, 0), mask_img)
                
                # Find the bounding box to see if we got a valid piece
                bbox = piece_img.getbbox()
                if not bbox:
                    print(f"WARNING: Piece {row}_{col} is empty! Creating a fallback.")
                    # Create a small fallback piece
                    start_y = int(row * cell_height)
                    end_y = int((row + 1) * cell_height)
                    start_x = int(col * cell_width)
                    end_x = int((col + 1) * cell_width)
                    
                    # Create a small square mask in the cell area
                    fallback_mask = np.zeros((img_height, img_width), dtype=np.uint8)
                    center_y = (start_y + end_y) // 2
                    center_x = (start_x + end_x) // 2
                    size = min(cell_width, cell_height) // 4
                    y1, y2 = max(0, int(center_y - size)), min(img_height, int(center_y + size))
                    x1, x2 = max(0, int(center_x - size)), min(img_width, int(center_x + size))
                    fallback_mask[y1:y2, x1:x2] = 255
                    
                    # Create the fallback piece
                    fallback_mask_img = Image.fromarray(fallback_mask)
                    piece_img = Image.new('RGBA', input_img.size, (0, 0, 0, 0))
                    piece_img.paste(input_img, (0, 0), fallback_mask_img)
                
                # Save the full-sized piece
                output_path = os.path.join(pieces_dir, f"{row}_{col}.png")
                piece_img.save(output_path)
                
                print(f"Created piece {row},{col} at {output_path}")
        
        # Create solution.json - Each piece has row and column info
        solution_data = {}
        for row in range(rows):
            for col in range(cols):
                piece_key = f"{row}_{col}"
                solution_data[piece_key] = {
                    "row": int(row),
                    "col": int(col)
                }
        
        # Save solution data as JSON
        solution_path = os.path.join(pieces_dir, "solution.json")
        with open(solution_path, 'w') as f:
            json.dump(solution_data, f, indent=2)
        
        print(f"Saved solution data to {solution_path}")
        
        # Create manifest.json in puzzle directory
        manifest = {
            "name": puzzle_name,
            "layouts": [layout_name],
            "pieces_count": rows * cols,
            "grid_size": {
                "rows": rows,
                "cols": cols
            },
            "image_dimensions": {
                "width": img_width,
                "height": img_height
            },
            "created_at": os.path.basename(input_image)
        }
        
        with open(os.path.join(puzzle_dir, "manifest.json"), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Successfully extracted {rows*cols} puzzle pieces to {pieces_dir}")
        
    except Exception as e:
        print(f"Error extracting puzzle pieces: {e}")
        import traceback
        traceback.print_exc()
        debug = True
    
    finally:
        # Clean up temp files unless debug is True
        if not debug:
            shutil.rmtree(temp_dir)
        else:
            print(f"Debug files saved to {debug_dir if debug_dir else temp_dir}")
                        
def main():
    args = parse_arguments()
    
    # Create the full puzzle pack directory structure
    output_folder = args.output
    puzzle_name = args.puzzle_name
    layout_name = args.layout_name
    
    if layout_name is None:
        # Determine grid size from SVG
        cols, rows, _, _ = determine_grid_size(args.svg)
        layout_name = f"{cols}x{rows}"
    
    # Extract puzzle pieces with bounding box based positioning
    extract_puzzle_pieces(
        args.image, args.svg, output_folder, 
        args.prefix, args.format, args.padding, 
        args.fixed_size, args.output_width, args.output_height,
        args.debug, puzzle_name, layout_name, args.show_handles
    )

if __name__ == "__main__":
    main()