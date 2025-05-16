#!/usr/bin/env python3

import argparse
import os
import json
import sys
from PIL import Image, ImageDraw

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
    
    return parser.parse_args()


def validate_paths(puzzle_pack, puzzle_name, grid_size):
    """Validate that necessary paths and files exist."""
    # [Unchanged validation code]
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


def reassemble_puzzle(puzzle_pack, puzzle_name, grid_size, debug=False, verify=False, output_file=None):
    """Reassemble the puzzle from pieces using solution.json.
    
    This simplified version assumes all pieces are full-sized transparent PNGs
    that just need to be overlaid on top of each other.
    """
    # Construct paths
    puzzle_dir = os.path.join(puzzle_pack, puzzle_name)
    layout_dir = os.path.join(puzzle_dir, 'layouts', grid_size)
    pieces_dir = os.path.join(layout_dir, 'pieces')
    solution_file = os.path.join(pieces_dir, 'solution.json')
    preview_path = os.path.join(puzzle_dir, 'preview.jpg')
    
    # Set default output file if not specified
    if output_file is None:
        output_file = os.path.join(layout_dir, 'reassembled.png')
    
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
    
    # Save the reassembled puzzle
    try:
        canvas.save(output_file)
        print(f"Reassembled puzzle saved to {output_file}")
        
        # Verify against preview if requested
        if verify and os.path.isfile(preview_path):
            # Compare dimensions
            with Image.open(preview_path) as preview:
                preview_width, preview_height = preview.size
                print(f"Preview dimensions: {preview_width}x{preview_height}")
                print(f"Canvas dimensions: {canvas.width}x{canvas.height}")
                
                if preview_width != canvas.width or preview_height != canvas.height:
                    print("⚠️ Warning: Dimensions of reassembled image do not match preview image!")
                    print(f"  Difference: ({canvas.width - preview_width}, {canvas.height - preview_height})")
                else:
                    print("✅ Dimensions match exactly!")
        
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
    if not reassemble_puzzle(args.puzzle_pack, args.puzzle, args.grid, args.debug, args.verify, args.output_file):
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())