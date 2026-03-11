#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import sys
import tempfile

import cairosvg
from PIL import Image


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Reassemble a jigsaw puzzle from its pieces using layout.ipuz.json'
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


def draw_jigsaw_lines_on_image(image, svg_file, line_color='white', line_width=2, line_opacity=128, debug=False):
    """Draw jigsaw cut lines directly on a PIL Image using cairosvg to render the SVG."""
    temp_dir = tempfile.mkdtemp()
    try:
        with open(svg_file, 'r') as f:
            svg_content = f.read()

        paths = re.findall(r'<path[^>]*d="([^"]*)"[^>]*>', svg_content)

        viewbox_match = re.search(r'viewBox="([^"]*)"', svg_content)
        viewbox = viewbox_match.group(1) if viewbox_match else "0 0 2048 2048"

        width_match = re.search(r'width="([^"]*)"', svg_content)
        width = width_match.group(1).replace('mm', '').replace('px', '') if width_match else "2048"

        height_match = re.search(r'height="([^"]*)"', svg_content)
        height = height_match.group(1).replace('mm', '').replace('px', '') if height_match else "2048"

        color_map = {
            'black': '#000000', 'white': '#FFFFFF', 'red': '#FF0000',
            'green': '#00FF00', 'blue': '#0000FF', 'yellow': '#FFFF00',
            'cyan': '#00FFFF', 'magenta': '#FF00FF', 'gray': '#808080',
        }
        color_value = color_map.get(line_color.lower(), line_color)
        if not color_value.startswith('#'):
            color_value = '#FFFFFF'

        new_svg = f'<?xml version="1.0" encoding="UTF-8"?>\n'
        new_svg += f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{viewbox}">\n'
        for path_data in paths:
            new_svg += f'<path d="{path_data}" fill="none" stroke="{color_value}" stroke-width="{line_width}" stroke-opacity="{line_opacity/255}" />\n'
        new_svg += '</svg>'

        svg_path = os.path.join(temp_dir, 'overlay.svg')
        with open(svg_path, 'w') as f:
            f.write(new_svg)

        png_path = os.path.join(temp_dir, 'overlay.png')
        img_width, img_height = image.size
        cairosvg.svg2png(
            url=svg_path, write_to=png_path,
            output_width=img_width, output_height=img_height,
            background_color="rgba(0,0,0,0)"
        )

        overlay = Image.open(png_path).convert('RGBA')
        return Image.alpha_composite(image, overlay)
    except Exception as e:
        print(f"Error drawing jigsaw lines: {e}")
        return image
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def reassemble_puzzle(puzzle_pack, puzzle_name, grid_size, debug=False, verify=False,
                      output_file=None, jigsaw=None, line_color='white', line_width=2, line_opacity=128):
    """Reassemble the puzzle from cropped pieces using layout.ipuz.json."""
    puzzle_dir = os.path.join(puzzle_pack, puzzle_name)
    layout_dir = os.path.join(puzzle_dir, 'layouts', grid_size)
    pieces_dir = os.path.join(layout_dir, 'pieces')
    preview_path = os.path.join(puzzle_dir, 'preview.jpg')

    if output_file is None:
        output_file = os.path.join(layout_dir, 'reassembled.png')

    # Handle "auto" jigsaw option
    if jigsaw == "auto":
        jigsaw = os.path.join(layout_dir, 'outline.svg')
        if not os.path.isfile(jigsaw):
            print(f"Warning: outline SVG not found at {jigsaw}")
            jigsaw = None
    elif jigsaw and not os.path.isabs(jigsaw):
        for candidate in [os.path.join(os.getcwd(), jigsaw),
                          os.path.join(layout_dir, jigsaw),
                          os.path.join(puzzle_dir, jigsaw)]:
            if os.path.isfile(candidate):
                jigsaw = candidate
                break
        else:
            print(f"Warning: Could not find SVG file: {jigsaw}")
            jigsaw = None

    # Load layout metadata
    layout_file = os.path.join(layout_dir, 'layout.ipuz.json')
    if not os.path.isfile(layout_file):
        print(f"Error: {layout_file} not found")
        return False

    with open(layout_file, 'r') as f:
        layout_data = json.load(f)

    if 'pieces' not in layout_data or 'canvas' not in layout_data:
        print("Error: layout.ipuz.json missing 'pieces' or 'canvas'")
        return False

    canvas_width = layout_data['canvas']['width']
    canvas_height = layout_data['canvas']['height']

    print(f"Reassembling {len(layout_data['pieces'])} pieces onto {canvas_width}x{canvas_height} canvas")
    canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))

    placed = 0
    for piece_info in sorted(layout_data['pieces'], key=lambda p: (p['row'], p['col'])):
        pid = piece_info['id']
        piece_path = os.path.join(pieces_dir, f"{pid}.png")
        if not os.path.isfile(piece_path):
            print(f"  Warning: missing {pid}.png")
            continue
        piece_img = Image.open(piece_path).convert('RGBA')
        x, y = piece_info['x'], piece_info['y']
        canvas.paste(piece_img, (x, y), piece_img)
        placed += 1
        if debug:
            print(f"  Placed {pid} at ({x}, {y})")

    print(f"Placed {placed} pieces")

    # Add jigsaw cut lines if requested
    if jigsaw and os.path.isfile(jigsaw):
        print(f"Adding jigsaw cut lines from {jigsaw}")
        canvas = draw_jigsaw_lines_on_image(canvas, jigsaw, line_color, line_width, line_opacity, debug)

    # Save
    canvas.save(output_file)
    print(f"Reassembled puzzle saved to {output_file}")

    if verify and os.path.isfile(preview_path):
        preview = Image.open(preview_path)
        pw, ph = preview.size
        cw, ch = canvas.size
        if pw == cw and ph == ch:
            print(f"Verification: dimensions match ({cw}x{ch})")
        else:
            print(f"Verification: dimension mismatch - preview {pw}x{ph} vs canvas {cw}x{ch}")

    return True


def main():
    args = parse_arguments()
    if not reassemble_puzzle(
        args.puzzle_pack, args.puzzle, args.grid,
        args.debug, args.verify, args.output_file,
        args.jigsaw, args.line_color, args.line_width, args.line_opacity
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
