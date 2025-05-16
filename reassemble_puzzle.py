#!/usr/bin/env python3

import argparse
import os
import json
import sys
import tempfile
from PIL import Image, ImageDraw
import cairosvg

def parse_arguments():
    """Parse command line arguments for the puzzle reassembler."""
    parser = argparse.ArgumentParser(
        description='Reassemble a jigsaw puzzle from its pieces using solution.json'
    )
    parser.add_argument('puzzle_pack', type=str, help='Path to the puzzle pack directory')
    parser.add_argument('--grid', type=str, required=True,
                        help='Grid size to reassemble (e.g., 2x2, 8x8)')
    parser.add_argument('--puzzle', type=str, default='puzzle_01',
                        help='Puzzle name to reassemble (default: puzzle_01)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    parser.add_argument('--verify', action='store_true',
                        help='Verify the reassembled puzzle against the original preview image')
    parser.add_argument('--output-file', type=str, default=None,
                        help='Custom output filename for the reassembled puzzle')
    parser.add_argument('--jigsaw', type=str, default=None,
                        help='Draw jigsaw cut lines using the specified SVG file (or "auto" to use outline.svg)')
    parser.add_argument('--line-color', type=str, default='white',
                        help='Color of jigsaw cut lines (default: white)')
    parser.add_argument('--line-width', type=int, default=2,
                        help='Width of jigsaw cut lines in pixels (default: 2)')
    parser.add_argument('--line-opacity', type=int, default=128,
                        help='Opacity of jigsaw cut lines (0-255, default: 128)')
    
    return parser.parse_args()


def validate_paths(puzzle_pack, puzzle_name, grid_size):
    """Validate that necessary paths and files exist."""
    # [Validation code unchanged]
    return True


def load_solution(solution_file):
    """Load and parse the solution.json file."""
    try:
        with open(solution_file, 'r') as f:
            solution_data = json.load(f)
        return solution_data
    except Exception as e:
        print(f"Error loading solution file: {e}")
        return None


def create_simple_svg(svg_file, line_color, line_width, line_opacity, temp_dir):
    """
    Create a new simple SVG file with the same paths as the original but with custom styling.
    This approach avoids parsing/modifying the original SVG which can lead to XML errors.
    """
    try:
        # Read the original SVG to extract path data
        with open(svg_file, 'r') as f:
            svg_content = f.read()
        
        # Extract paths using regex
        import re
        path_pattern = r'<path[^>]*d="([^"]*)"[^>]*>'
        paths = re.findall(path_pattern, svg_content)
        
        # Extract dimensions from SVG
        viewbox_pattern = r'viewBox="([^"]*)"'
        width_pattern = r'width="([^"]*)"'
        height_pattern = r'height="([^"]*)"'
        
        # Get viewBox
        viewbox = "0 0 2048 2048"  # Default
        viewbox_match = re.search(viewbox_pattern, svg_content)
        if viewbox_match:
            viewbox = viewbox_match.group(1)
        
        # Get width and height
        width = "2048"  # Default
        height = "2048"  # Default
        
        width_match = re.search(width_pattern, svg_content)
        if width_match:
            width = width_match.group(1).replace('mm', '').replace('px', '')
        
        height_match = re.search(height_pattern, svg_content)
        if height_match:
            height = height_match.group(1).replace('mm', '').replace('px', '')
        
        # Convert color to hex if it's a named color
        color_map = {
            'black': '#000000',
            'white': '#FFFFFF',
            'red': '#FF0000',
            'green': '#00FF00',
            'blue': '#0000FF',
            'yellow': '#FFFF00',
            'cyan': '#00FFFF',
            'magenta': '#FF00FF',
            'gray': '#808080',
            'grey': '#808080'
        }
        
        color_value = color_map.get(line_color.lower(), line_color)
        if not color_value.startswith('#'):
            color_value = '#FFFFFF'  # Default to white
        
        # Create a new SVG with the same paths but custom styling
        new_svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{viewbox}">
'''
        
        # Add each path with custom styling
        for path_data in paths:
            new_svg_content += f'<path d="{path_data}" fill="none" stroke="{color_value}" stroke-width="{line_width}" stroke-opacity="{line_opacity/255}" />\n'
        
        new_svg_content += '</svg>'
        
        # Write to a new file
        new_svg_path = os.path.join(temp_dir, 'simple_' + os.path.basename(svg_file))
        with open(new_svg_path, 'w') as f:
            f.write(new_svg_content)
        
        return new_svg_path
    
    except Exception as e:
        print(f"Error creating simple SVG: {e}")
        import traceback
        traceback.print_exc()
        return svg_file  # Return the original file on error


def draw_jigsaw_lines_on_image(image, svg_file, line_color='white', line_width=2, line_opacity=128, debug=False):
    """
    Draw jigsaw cut lines directly on a PIL Image using cairosvg to render the SVG.
    """
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create a simple SVG with desired styling
        simple_svg = create_simple_svg(svg_file, line_color, line_width, line_opacity, temp_dir)
        
        if debug:
            print(f"Created simple SVG: {simple_svg}")
            
            # Save a copy of the simple SVG for inspection
            import shutil
            debug_svg = os.path.splitext(svg_file)[0] + '_simple.svg'
            shutil.copy(simple_svg, debug_svg)
            print(f"Saved debug SVG to: {debug_svg}")
        
        # Render the SVG to a temporary PNG file
        temp_png = os.path.join(temp_dir, 'overlay.png')
        
        # Get image dimensions
        img_width, img_height = image.size
        
        # Render SVG to PNG with transparent background
        cairosvg.svg2png(
            url=simple_svg,
            write_to=temp_png,
            output_width=img_width,
            output_height=img_height,
            background_color="rgba(0,0,0,0)"  # Transparent background
        )
        
        # Load the overlay image
        overlay = Image.open(temp_png).convert('RGBA')
        
        if debug:
            debug_png = os.path.splitext(svg_file)[0] + '_overlay.png'
            overlay.save(debug_png)
            print(f"Saved debug overlay to: {debug_png}")
        
        # Create a composite of the original image and the overlay
        result = Image.alpha_composite(image, overlay)
        
        # Clean up temporary files
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass
        
        return result
    
    except Exception as e:
        print(f"Error drawing jigsaw lines: {e}")
        import traceback
        traceback.print_exc()
        return image  # Return the original image on error


def verify_puzzle_against_preview(reassembled, preview_path):
    """Compare the reassembled puzzle with the original preview image"""
    try:
        # Load preview image
        preview = Image.open(preview_path)
        
        # Simple dimension check
        preview_width, preview_height = preview.size
        reassembled_width, reassembled_height = reassembled.size
        
        print(f"Preview dimensions: {preview_width}x{preview_height}")
        print(f"Canvas dimensions: {reassembled_width}x{reassembled_height}")
                
        if preview_width != reassembled_width or preview_height != reassembled_height:
            print("⚠️ Warning: Dimensions of reassembled image do not match preview image!")
            print(f"  Difference: ({reassembled_width - preview_width}, {reassembled_height - preview_height})")
        else:
            print("✅ Dimensions match exactly!")
        
        return preview_width == reassembled_width and preview_height == reassembled_height
    
    except Exception as e:
        print(f"Error verifying against preview: {e}")
        return False


def reassemble_puzzle(puzzle_pack, puzzle_name, grid_size, debug=False, verify=False, 
                    output_file=None, jigsaw=None, line_color='white', line_width=2, line_opacity=128):
    """Reassemble the puzzle from pieces using solution.json with optional jigsaw outlines."""
    # Construct paths
    puzzle_dir = os.path.join(puzzle_pack, puzzle_name)
    layout_dir = os.path.join(puzzle_dir, 'layouts', grid_size)
    pieces_dir = os.path.join(layout_dir, 'pieces')
    solution_file = os.path.join(pieces_dir, 'solution.json')
    preview_path = os.path.join(puzzle_dir, 'preview.jpg')
    
    # Set default output file if not specified
    if output_file is None:
        output_file = os.path.join(layout_dir, 'reassembled.png')
    
    # Handle "auto" jigsaw option
    if jigsaw == "auto":
        jigsaw = os.path.join(layout_dir, 'outline.svg')
        print(f"Auto-detected SVG path: {jigsaw}")
        if not os.path.isfile(jigsaw):
            print(f"Warning: Auto-detected outline SVG not found at {jigsaw}")
            jigsaw = None
    elif jigsaw and not os.path.isabs(jigsaw):
        # Try to resolve relative path
        potential_paths = [
            os.path.join(os.getcwd(), jigsaw),
            os.path.join(layout_dir, jigsaw),
            os.path.join(puzzle_dir, jigsaw)
        ]
        for path in potential_paths:
            if os.path.isfile(path):
                jigsaw = path
                print(f"Using SVG at: {jigsaw}")
                break
        else:
            print(f"Warning: Could not find SVG file at {jigsaw}. Tried paths:")
            for path in potential_paths:
                print(f"  - {path}")
            jigsaw = None
    
    # Load solution data
    solution_data = load_solution(solution_file)
    if not solution_data:
        return False
    
    print(f"Loaded solution data with {len(solution_data)} pieces")
    
    # Get all pieces
    pieces = {}
    first_piece = None
    
    for piece_key, piece_info in solution_data.items():
        piece_path = os.path.join(pieces_dir, f"{piece_key}.png")
        if os.path.isfile(piece_path):
            try:
                piece_img = Image.open(piece_path)
                pieces[piece_key] = piece_img
                
                # Keep track of the first piece to get dimensions
                if first_piece is None:
                    first_piece = piece_img
            except Exception as e:
                print(f"Error opening piece '{piece_path}': {e}")
    
    if not pieces:
        print("Error: No valid pieces found")
        return False
    
    # Get original image dimensions
    if first_piece:
        # Use the first piece's dimensions
        canvas_width, canvas_height = first_piece.size
    elif os.path.isfile(preview_path):
        # Fallback to preview dimensions
        with Image.open(preview_path) as preview_img:
            canvas_width, canvas_height = preview_img.size
    else:
        print("Error: Could not determine canvas dimensions")
        return False
    
    print(f"Creating canvas with dimensions: {canvas_width}x{canvas_height}")
    
    # Create a transparent canvas
    canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
    
    # Sort pieces by row and column
    sorted_pieces = []
    for piece_key in pieces:
        parts = piece_key.split('_')
        if len(parts) == 2:
            try:
                row, col = int(parts[0]), int(parts[1])
                sorted_pieces.append((row, col, piece_key))
            except ValueError:
                sorted_pieces.append((999, 999, piece_key))
    
    # Sort by row, then column
    sorted_pieces.sort()
    
    # Overlay each piece on the canvas
    for row, col, piece_key in sorted_pieces:
        piece_img = pieces[piece_key]
        
        # Simply overlay at exact position (0,0)
        canvas.paste(piece_img, (0, 0), piece_img)
        
        print(f"Overlaid piece {piece_key}")
    
    # Add jigsaw cut lines if requested
    if jigsaw and os.path.isfile(jigsaw):
        print(f"Adding jigsaw cut lines from {jigsaw}")
        # Save the canvas before adding lines (for debugging)
        if debug:
            debug_canvas_path = os.path.splitext(output_file)[0] + '_no_lines.png'
            canvas.save(debug_canvas_path)
            print(f"Saved canvas without lines to {debug_canvas_path}")
        
        # Draw jigsaw lines with semi-transparency
        canvas = draw_jigsaw_lines_on_image(
            canvas, 
            jigsaw, 
            line_color, 
            line_width, 
            line_opacity,
            debug
        )
    
    # Save the reassembled puzzle
    try:
        canvas.save(output_file)
        print(f"Reassembled puzzle saved to {output_file}")
        
        # Verify against preview if requested
        if verify and os.path.isfile(preview_path):
            if verify_puzzle_against_preview(canvas, preview_path):
                print("✅ Verification successful: Dimensions match preview image")
            else:
                print("⚠️ Verification warning: Dimensions do not match preview image")
        
        return True
    except Exception as e:
        print(f"Error saving reassembled puzzle: {e}")
        return False


def main():
    """Main entry point for the puzzle reassembler."""
    args = parse_arguments()
    
    # Validate paths
    if not validate_paths(args.puzzle_pack, args.puzzle, args.grid):
        return 1
    
    # Reassemble the puzzle
    if not reassemble_puzzle(
        args.puzzle_pack, args.puzzle, args.grid, 
        args.debug, args.verify, args.output_file,
        args.jigsaw, args.line_color, args.line_width, args.line_opacity
    ):
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())