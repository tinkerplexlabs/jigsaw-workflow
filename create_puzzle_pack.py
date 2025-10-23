#!/usr/bin/env python3

import argparse
import os
import subprocess
import json
import shutil
import tempfile
import random
from datetime import datetime
from PIL import Image

def parse_arguments():
    parser = argparse.ArgumentParser(description='Create a jigsaw puzzle pack with multiple layouts from an image')
    parser.add_argument('image', type=str, help='Input image to create puzzles from')
    parser.add_argument('pack_name', type=str, help='Name of the puzzle pack')
    parser.add_argument('--grids', type=str, default='2x2,4x4,8x8', help='Comma-separated list of grid sizes')
    parser.add_argument('--output', type=str, default='puzzle_packs', help='Output directory for the puzzle pack')
    parser.add_argument('--author', type=str, default='', help='Author name')
    parser.add_argument('--copyright', type=str, default='', help='Copyright info')
    return parser.parse_args()

def create_directory_structure(base_dir, pack_name):
    pack_dir = os.path.join(base_dir, pack_name)
    os.makedirs(pack_dir, exist_ok=True)
    return pack_dir

def create_manifest(pack_dir, pack_name, author, copyright_info, puzzles):
    manifest = {
        "name": pack_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "puzzles": puzzles
    }
    if author:
        manifest["author"] = author
    if copyright_info:
        manifest["copyright"] = copyright_info
    with open(os.path.join(pack_dir, "manifest.json"), 'w') as f:
        json.dump(manifest, f, indent=2)

def normalize_input_image(image_path, target_size=2048):
    """
    Normalize input image to target_size x target_size.
    
    This ensures consistent canvas dimensions across all puzzle generation steps,
    preventing scale mismatches between the SVG layout (which uses TILE_SIZE * grid_size)
    and the actual piece images extracted from the source image.
    
    Args:
        image_path: Path to the original input image
        target_size: Target dimensions (default 2048x2048 for 8x8 grid with 256px tiles)
    
    Returns:
        Path to the normalized temporary image file
    """
    with Image.open(image_path) as img:
        orig_width, orig_height = img.size
        
        # If already correct size, just convert to RGBA and save
        if orig_width == target_size and orig_height == target_size:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            temp_path = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
            img.save(temp_path)
            print(f"  Input image already {target_size}x{target_size}, using as-is")
            return temp_path
        
        # Resize to target dimensions
        print(f"  Resizing input image from {orig_width}x{orig_height} to {target_size}x{target_size}")
        
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # High-quality resize using Lanczos resampling
        resized = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Save to temporary file
        temp_path = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
        resized.save(temp_path)
        
        return temp_path

def generate_jigsaw_outline(output_dir, cols, rows, width, height, seed=None):
    if seed is None:
        seed = random.randint(1, 10000)
    outline_svg = os.path.join(output_dir, "outline.svg")
    subprocess.run([
        "python3", "gen_jigsaw.py",
        "--grid", str(cols), str(rows),
        "--width", str(width),
        "--height", str(height),
        "--seed", str(seed),
        "-o", outline_svg
    ], check=True)
    return outline_svg

def convert_outline_to_ipuz(outline_svg, layout_dir):
    outline_split_svg = os.path.join(layout_dir, "outline-split.svg")
    ipuz_json = os.path.join(layout_dir, "layout.ipuz.json")
    subprocess.run([
        "python3", "svg_to_ipuz.py", outline_svg,
        "--output_svg", outline_split_svg,
        "--output_json", ipuz_json
    ], check=True)
    return outline_split_svg, ipuz_json

def extract_puzzle_pieces(image_path, split_svg, output_dir, puzzle_name, layout_name):
    subprocess.run([
        "python3", "jigsaw_piece_extractor_exact.py",
        image_path,
        split_svg,
        "--output", output_dir
    ], check=True)

def get_image_dimensions(image_path):
    with Image.open(image_path) as img:
        return img.width, img.height

def create_puzzle_pack(image_path, pack_name, grids, output_dir, author, copyright_info):
    pack_dir = create_directory_structure(output_dir, pack_name)
    
    # Define standard tile size in pixels
    TILE_SIZE = 256
    BASE_CANVAS_SIZE = 2048  # Standard base size for 8x8 grid (8 * 256)
    
    # Normalize input image to BASE_CANVAS_SIZE to ensure consistent scaling
    print(f"\nNormalizing input image to {BASE_CANVAS_SIZE}x{BASE_CANVAS_SIZE}...")
    normalized_image_path = normalize_input_image(image_path, BASE_CANVAS_SIZE)
    
    try:
        puzzle_name = "puzzle_01"
        puzzle_dir = os.path.join(pack_dir, puzzle_name)
        os.makedirs(puzzle_dir, exist_ok=True)
        layouts_dir = os.path.join(puzzle_dir, "layouts")
        os.makedirs(layouts_dir, exist_ok=True)

        # Create preview from original image (for best quality)
        preview_path = os.path.join(puzzle_dir, "preview.jpg")
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(preview_path, quality=90)

        grid_sizes = [(int(g.split('x')[0]), int(g.split('x')[1])) if 'x' in g else (int(g), int(g)) for g in grids.split(',')]
        layouts = []
        
        for cols, rows in grid_sizes:
            layout_name = f"{cols}x{rows}"
            layout_dir = os.path.join(layouts_dir, layout_name)
            os.makedirs(layout_dir, exist_ok=True)
            print(f"\nProcessing layout: {layout_name}")
            
            # Calculate canvas dimensions based on grid size and standard tile size
            canvas_width = cols * TILE_SIZE
            canvas_height = rows * TILE_SIZE
            
            print(f"  Grid: {cols}x{rows}, Canvas: {canvas_width}x{canvas_height}px")
            
            # For grids larger than 8x8, we need to scale up the normalized image
            if canvas_width != BASE_CANVAS_SIZE or canvas_height != BASE_CANVAS_SIZE:
                print(f"  Scaling normalized image to {canvas_width}x{canvas_height} for this layout...")
                with Image.open(normalized_image_path) as norm_img:
                    scaled_img = norm_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                    scaled_temp_path = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
                    scaled_img.save(scaled_temp_path)
                
                layout_image_path = scaled_temp_path
            else:
                layout_image_path = normalized_image_path
            
            try:
                outline_svg = generate_jigsaw_outline(layout_dir, cols, rows, canvas_width, canvas_height)
                split_svg, ipuz_json = convert_outline_to_ipuz(outline_svg, layout_dir)
                extract_puzzle_pieces(layout_image_path, split_svg, layout_dir, puzzle_name, layout_name)
                layouts.append(layout_name)
            finally:
                # Clean up scaled image if we created one
                if layout_image_path != normalized_image_path and os.path.exists(layout_image_path):
                    os.unlink(layout_image_path)

        create_manifest(pack_dir, pack_name, author, copyright_info, [{"name": puzzle_name, "layouts": layouts}])
        return pack_dir
        
    finally:
        # Clean up normalized image
        if os.path.exists(normalized_image_path):
            os.unlink(normalized_image_path)

def create_zip_archive(pack_dir):
    shutil.make_archive(pack_dir, 'zip', os.path.dirname(pack_dir), os.path.basename(pack_dir))
    print(f"Created zip archive: {pack_dir}.zip")

def main():
    args = parse_arguments()
    if not os.path.exists(args.image):
        print(f"Error: Input image '{args.image}' does not exist.")
        return 1
    pack_dir = create_puzzle_pack(args.image, args.pack_name, args.grids, args.output, args.author, args.copyright)
    create_zip_archive(pack_dir)
    return 0

if __name__ == "__main__":
    exit(main())
