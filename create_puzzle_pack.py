#!/usr/bin/env python3

import argparse
import os
import json
import shutil
from pathlib import Path
from PIL import Image
import tempfile
import subprocess
import sys

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Create a complete puzzle pack from source images'
    )
    parser.add_argument('images', nargs='+', type=str, 
                        help='Input images to be converted into puzzles')
    parser.add_argument('--pack-name', type=str, default='My Puzzle Pack',
                        help='Name of the puzzle pack')
    parser.add_argument('--author', type=str, default='Anonymous',
                        help='Author of the puzzle pack')
    parser.add_argument('--description', type=str, default=None,
                        help='Description of the puzzle pack')
    parser.add_argument('--grid-sizes', nargs='+', type=lambda s: tuple(map(int, s.split('x'))),
                        default=[(2,2), (4,4), (8,8), (16,16), (32,32)],
                        help='Grid sizes to generate (e.g., 2x2 4x4 8x8)')
    parser.add_argument('-o', '--output', type=str, default='puzzle_pack',
                        help='Output directory for puzzle pack (default: puzzle_pack)')
    parser.add_argument('--padding', type=int, default=30,
                        help='Padding around pieces in pixels (default: 30)')
    parser.add_argument('--no-fixed-size', action='store_true',
                        help='Disable fixed-size output (default: enabled)')
    parser.add_argument('--debug', action='store_true',
                        help='Save debug images')
    parser.add_argument('--jitter', type=float, default=10.0,
                        help='Jitter percentage for SVG generation (default: 10.0)')
    parser.add_argument('--tabsize', type=float, default=22.0,
                        help='Tab size percentage for SVG generation (default: 22.0)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Base random seed for SVG generation (default: random)')
    parser.add_argument('--radius', type=float, default=3.0,
                        help='Corner radius for puzzle pieces (default: 3.0)')
    parser.add_argument('--extractor', type=str, default='jigsaw_piece_extractor.py',
                        help='Path to jigsaw piece extractor script')
    parser.add_argument('--gen-jigsaw', type=str, default='gen_jigsaw.py',
                        help='Path to jigsaw generator script')
    return parser.parse_args()


def create_puzzle_pack(args):
    """Create a complete puzzle pack from source images"""
    
    # Create output directory structure
    pack_path = Path(args.output)
    pack_path.mkdir(parents=True, exist_ok=True)
    
    # Create manifest
    manifest = {
        "name": args.pack_name,
        "version": "1.0",
        "author": args.author,
        "description": args.description or f"Jigsaw puzzle pack: {args.pack_name}",
        "puzzles": []
    }
    
    # Process each image
    for idx, image_path in enumerate(args.images):
        puzzle_idx = idx + 1
        print(f"\nProcessing puzzle {puzzle_idx}: {image_path}")
        
        # Create puzzle directory
        puzzle_dir = pack_path / f"puzzle_{puzzle_idx:02d}"
        puzzle_dir.mkdir(exist_ok=True)
        
        # Load and process the source image
        try:
            source_img = Image.open(image_path)
            img_width, img_height = source_img.size
            
            # Save preview image
            preview_path = puzzle_dir / "preview.jpg"
            preview_img = source_img.convert('RGB')
            preview_img.save(preview_path, quality=90)
            
            # Create puzzle info
            puzzle_info = {
                "id": f"puzzle_{puzzle_idx:02d}",
                "name": f"Puzzle {puzzle_idx}",
                "source_image": os.path.basename(image_path),
                "layouts": []
            }
            
            # Create layouts directory
            layouts_dir = puzzle_dir / "layouts"
            layouts_dir.mkdir(exist_ok=True)
            
            # Process each grid size
            for grid_size in args.grid_sizes:
                cols, rows = grid_size
                layout_name = f"{cols}x{rows}"
                print(f"  Creating layout {layout_name}")
                
                layout_dir = layouts_dir / layout_name
                layout_dir.mkdir(exist_ok=True)
                
                # Generate SVG using gen_jigsaw.py with image dimensions
                svg_path = layout_dir / "outline.svg"
                
                # Build the command with proper formatting and dimensions
                gen_jigsaw_cmd = [
                    sys.executable, args.gen_jigsaw,
                    '--grid', str(cols), str(rows),
                    '-o', str(svg_path),
                    '--jitter', str(args.jitter),
                    '--tabsize', str(args.tabsize),
                    '--width', str(img_width),    # Use image width
                    '--height', str(img_height),  # Use image height
                    '--radius', str(args.radius)
                ]
                
                if args.seed is not None:
                    layout_seed = args.seed + idx * 1000 + cols * 100 + rows
                    gen_jigsaw_cmd.extend(['--seed', str(layout_seed)])
                
                # Run gen_jigsaw.py
                try:
                    result = subprocess.run(gen_jigsaw_cmd, check=True, capture_output=True, text=True)
                    print(f"    Generated SVG for {layout_name}")
                except subprocess.CalledProcessError as e:
                    print(f"Error running gen_jigsaw.py: {e}")
                    print(f"Command: {' '.join(gen_jigsaw_cmd)}")
                    print(f"Stdout: {e.stdout}")
                    print(f"Stderr: {e.stderr}")
                    raise
                
                # Create temporary directory for pieces
                with tempfile.TemporaryDirectory() as temp_pieces_dir:
                    # Extract puzzle pieces using original extractor
                    extract_cmd = [
                        sys.executable, args.extractor,
                        image_path,
                        str(svg_path),
                        '-o', temp_pieces_dir,
                        '--prefix', 'piece',
                        '--padding', str(args.padding)
                    ]
                    
                    # Fixed-size is now default, only disable if specified
                    if not args.no_fixed_size:
                        extract_cmd.append('--fixed-size')
                    
                    if args.debug:
                        extract_cmd.append('--debug')
                    
                    # Run original extractor
                    try:
                        result = subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
                        print(f"    Extracted pieces for {layout_name}")
                    except subprocess.CalledProcessError as e:
                        print(f"Error running extractor: {e}")
                        print(f"Command: {' '.join(extract_cmd)}")
                        print(f"Stdout: {e.stdout}")
                        print(f"Stderr: {e.stderr}")
                        raise
                    
                    # Create pieces directory in layout
                    pieces_dir = layout_dir / "pieces"
                    pieces_dir.mkdir(exist_ok=True)
                    
                    # Copy and rename pieces
                    piece_count = 0
                    for temp_piece in Path(temp_pieces_dir).glob("piece_*_*.png"):
                        # Extract row and column from filename
                        parts = temp_piece.stem.split('_')
                        if len(parts) == 3:  # piece_ROW_COL
                            row = int(parts[1])
                            col = int(parts[2])
                            # Use COL_ROW format for puzzle pack
                            new_name = f"{col}_{row}.png"
                            new_path = pieces_dir / new_name
                            shutil.copy2(temp_piece, new_path)
                            piece_count += 1
                
                # Create preview with outline
                preview_outline_path = layout_dir / "preview-outline.png"
                create_preview_with_outline(str(preview_path), str(svg_path), 
                                          str(preview_outline_path))
                
                # Add layout info
                puzzle_info["layouts"].append({
                    "grid": layout_name,
                    "cols": cols,
                    "rows": rows,
                    "piece_count": piece_count
                })
                
                print(f"    Created {piece_count} pieces for {layout_name}")
            
            # Add puzzle to manifest
            manifest["puzzles"].append(puzzle_info)
            
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save manifest
    manifest_path = pack_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nPuzzle pack created successfully at: {pack_path}")
    print(f"Total puzzles: {len(manifest['puzzles'])}")


def create_preview_with_outline(image_path, svg_path, output_path):
    """Create a preview image with the jigsaw outline overlaid"""
    try:
        from cairosvg import svg2png
        import numpy as np
        
        # Load the image
        img = Image.open(image_path)
        
        # Create a temporary PNG from the SVG at the same size as the image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            svg2png(url=svg_path, write_to=tmp.name, 
                   output_width=img.width, output_height=img.height)
            
            # Load the SVG as an image
            svg_img = Image.open(tmp.name).convert('RGBA')
            
            # Create a mask from the black lines
            svg_array = np.array(svg_img)
            
            # Find black pixels (the lines)
            black_pixels = (svg_array[:,:,0] < 128) & (svg_array[:,:,1] < 128) & (svg_array[:,:,2] < 128)
            
            # Create an overlay with semi-transparent lines
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_array = np.array(overlay)
            
            # Set the line pixels to semi-transparent dark gray
            overlay_array[black_pixels] = [64, 64, 64, 192]  # Dark gray with alpha
            
            # Convert back to image
            overlay = Image.fromarray(overlay_array)
            
            # Composite the overlay onto the original image
            img_with_lines = Image.alpha_composite(img.convert('RGBA'), overlay)
            
            # Save the result
            img_with_lines.convert('RGB').save(output_path, quality=90)
            
        # Clean up
        os.unlink(tmp.name)
        
    except Exception as e:
        print(f"Error creating preview with outline: {e}")
        # Fallback: just copy the original image
        shutil.copy2(image_path, output_path)


def main():
    args = parse_arguments()
    create_puzzle_pack(args)


if __name__ == "__main__":
    main()