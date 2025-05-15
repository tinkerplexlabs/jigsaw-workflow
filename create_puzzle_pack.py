#!/usr/bin/env python3

import argparse
import os
import subprocess
import json
import shutil
import tempfile
import random
from datetime import datetime

def parse_arguments():
    """Parse command line arguments for the puzzle pack creator."""
    parser = argparse.ArgumentParser(
        description='Create a jigsaw puzzle pack with multiple layouts from an image'
    )
    parser.add_argument('image', type=str, help='Input image to create puzzles from')
    parser.add_argument('pack_name', type=str, help='Name of the puzzle pack')
    parser.add_argument('--grids', type=str, default='2x2,4x4,8x8',
                        help='Comma-separated list of grid sizes (e.g., 2x2,4x4,8x8)')
    parser.add_argument('--output', type=str, default='puzzle_packs',
                        help='Output directory for the puzzle pack')
    parser.add_argument('--author', type=str, default='',
                        help='Author name for the puzzle pack')
    parser.add_argument('--copyright', type=str, default='',
                        help='Copyright information for the puzzle pack')
    
    return parser.parse_args()

def create_directory_structure(base_dir, pack_name):
    """Create the necessary directory structure for the puzzle pack."""
    pack_dir = os.path.join(base_dir, pack_name)
    os.makedirs(pack_dir, exist_ok=True)
    return pack_dir

def create_manifest(pack_dir, pack_name, author, copyright_info, puzzles):
    """Create the manifest.json file for the puzzle pack."""
    manifest = {
        "name": pack_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "puzzles": puzzles
    }
    
    if author:
        manifest["author"] = author
    
    if copyright_info:
        manifest["copyright"] = copyright_info
    
    manifest_path = os.path.join(pack_dir, "manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Created manifest at {manifest_path}")

def generate_jigsaw_outline(output_dir, cols, rows, width, height, seed=None):
    """Generate a jigsaw outline SVG using gen_jigsaw.py."""
    if seed is None:
        seed = random.randint(1, 10000)
    
    output_svg = os.path.join(output_dir, "outline.svg")
    
    cmd = [
        "python3", "gen_jigsaw.py",
        "--grid", str(cols), str(rows),
        "--width", str(width),
        "--height", str(height),
        "--seed", str(seed),
        "-o", output_svg
    ]
    
    print(f"Generating jigsaw outline for {cols}x{rows} grid...")
    subprocess.run(cmd, check=True)
    
    return output_svg

def extract_puzzle_pieces(image_path, svg_path, output_dir, puzzle_name, layout_name):
    """Extract puzzle pieces using jigsaw_piece_extractor.py."""
    cmd = [
        "python3", "jigsaw_piece_extractor.py",
        image_path,
        svg_path,
        "-o", output_dir,
        "--puzzle-name", puzzle_name,
        "--layout-name", layout_name,
        "--format", "png",
        "--padding", "30",
        "--fixed-size"
    ]
    
    print(f"Extracting puzzle pieces for {layout_name} layout...")
    subprocess.run(cmd, check=True)

def get_image_dimensions(image_path):
    """Get the dimensions of an image using PIL."""
    from PIL import Image
    with Image.open(image_path) as img:
        return img.width, img.height

def create_puzzle_pack(image_path, pack_name, grids, output_dir, author, copyright_info):
    """Create a complete puzzle pack with specified grid sizes."""
    # Create the base pack directory
    pack_dir = create_directory_structure(output_dir, pack_name)
    
    # Get image dimensions to preserve aspect ratio
    img_width, img_height = get_image_dimensions(image_path)
    
    # Create a single puzzle with multiple layouts
    puzzle_name = "puzzle_01"
    puzzle_dir = os.path.join(pack_dir, puzzle_name)
    os.makedirs(puzzle_dir, exist_ok=True)
    
    # Copy the original image as preview
    from PIL import Image
    preview_path = os.path.join(puzzle_dir, "preview.jpg")
    with Image.open(image_path) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(preview_path, quality=90)
    
    # Create layouts directory
    layouts_dir = os.path.join(puzzle_dir, "layouts")
    os.makedirs(layouts_dir, exist_ok=True)
    
    # Parse grid sizes
    grid_sizes = []
    for grid in grids.split(','):
        if 'x' in grid:
            cols, rows = map(int, grid.split('x'))
            grid_sizes.append((cols, rows))
        else:
            # If only one number is provided, use it for both dimensions
            size = int(grid)
            grid_sizes.append((size, size))
    
    # Process each grid size
    layouts = []
    for cols, rows in grid_sizes:
        layout_name = f"{cols}x{rows}"
        print(f"\nProcessing layout: {layout_name}")
        
        # Create layout directory
        layout_dir = os.path.join(layouts_dir, layout_name)
        os.makedirs(layout_dir, exist_ok=True)
        
        # Generate jigsaw outline
        svg_path = generate_jigsaw_outline(layout_dir, cols, rows, img_width, img_height)
        
        # Extract puzzle pieces
        extract_puzzle_pieces(image_path, svg_path, output_dir, puzzle_name, layout_name)
        
        layouts.append(layout_name)
    
    # Create manifest.json
    puzzles = [{"name": puzzle_name, "layouts": layouts}]
    create_manifest(pack_dir, pack_name, author, copyright_info, puzzles)
    
    print(f"\nPuzzle pack created successfully at: {pack_dir}")
    return pack_dir

def create_zip_archive(pack_dir):
    """Create a zip archive of the puzzle pack."""
    shutil.make_archive(pack_dir, 'zip', os.path.dirname(pack_dir), os.path.basename(pack_dir))
    print(f"Created zip archive: {pack_dir}.zip")

def main():
    args = parse_arguments()
    
    # Validate input image
    if not os.path.exists(args.image):
        print(f"Error: Input image '{args.image}' does not exist.")
        return 1
    
    # Create the puzzle pack
    pack_dir = create_puzzle_pack(
        args.image,
        args.pack_name,
        args.grids,
        args.output,
        args.author,
        args.copyright
    )
    
    # Create a zip archive
    create_zip_archive(pack_dir)
    
    return 0

if __name__ == "__main__":
    exit(main())