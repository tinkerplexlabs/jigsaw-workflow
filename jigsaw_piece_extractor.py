#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
from cairosvg import svg2png

# --- Argument Parsing ---

def parse_arguments():
    parser = argparse.ArgumentParser(description="Extract puzzle pieces from an image using ipuz or split-path SVG format")
    parser.add_argument("image", help="Input image (e.g. PNG)")
    parser.add_argument("layout", help="Puzzle layout file: .ipuz.json or split SVG")
    parser.add_argument("--output", default="pieces", help="Output folder for pieces")
    return parser.parse_args()

# --- SVG Parsing and Cut Extraction ---

def extract_paths_from_svg(svg_file):
    tree = ET.parse(svg_file)
    root = tree.getroot()
    width = int(float(root.attrib.get("width", "1024").replace("mm", "").replace("px", "")))
    height = int(float(root.attrib.get("height", "1024").replace("mm", "").replace("px", "")))
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    hpaths, vpaths = [], []
    border = None

    for p in root.findall(".//svg:path", ns):
        cls = p.attrib.get("class", "")
        classes = set(cls.strip().split())
        if "border" in classes:
            border = p.attrib['d']
        elif "horizontal" in classes:
            hpaths.append(p.attrib['d'])
        elif "vertical" in classes:
            vpaths.append(p.attrib['d'])

    return hpaths, vpaths, border, width, height

# --- IPUZ Parsing ---

def extract_paths_from_ipuz(ipuz_path):
    with open(ipuz_path) as f:
        data = json.load(f)
    canvas = data.get("canvas", {"width": 1024, "height": 1024})
    width, height = canvas["width"], canvas["height"]
    hpaths = []
    vpaths = []
    border = None
    for entry in data["cutArrays"]:
        if entry["orientation"] == "horizontal":
            hpaths.extend(p["d"] for p in entry["paths"])
        elif entry["orientation"] == "vertical":
            vpaths.extend(p["d"] for p in entry["paths"])
    return hpaths, vpaths, border, width, height

# --- SVG Cut Builder ---

def build_cut_svg(cut_d, width, height):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <path d="{cut_d}" stroke="black" stroke-width="1" fill="none"/>
</svg>'''

# --- Main Extraction Logic ---

def main():
    args = parse_arguments()
    img = Image.open(args.image).convert("RGBA")
    img_w, img_h = img.size
    ext = os.path.splitext(args.layout)[1]

    if ext == ".json":
        hcuts, vcuts, border_d, layout_w, layout_h = extract_paths_from_ipuz(args.layout)
    elif ext == ".svg":
        hcuts, vcuts, border_d, layout_w, layout_h = extract_paths_from_svg(args.layout)
    else:
        raise ValueError("Unsupported layout format")

    rows = len(hcuts) + 1
    cols = len(vcuts) + 1
    print(f"Grid detected: {cols}x{rows}  Layout: {layout_w}x{layout_h}  Image: {img_w}x{img_h}")

    cell_w = img_w // cols
    cell_h = img_h // rows

    tempdir = tempfile.mkdtemp()
    os.makedirs(args.output, exist_ok=True)

    pieces_dir = os.path.join(args.output, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)

    for row in range(rows):
        for col in range(cols):
            mask = Image.new("L", img.size, 255)

            for direction, cuts, idx in [
                ("above", hcuts, row - 1),
                ("below", hcuts, row if row < rows - 1 else -1),
                ("left", vcuts, col - 1),
                ("right", vcuts, col if col < cols - 1 else -1)
            ]:
                if idx >= 0 and idx < len(cuts):
                    cut_path = cuts[idx]
                elif direction == "below" and idx == -1:
                    cut_path = f"M 0 {img_h} L {img_w} {img_h}"
                elif direction == "right" and idx == -1:
                    cut_path = f"M {img_w} 0 L {img_w} {img_h}"
                else:
                    continue

                svg = build_cut_svg(cut_path, layout_w, layout_h)
                svg_path = os.path.join(tempdir, f"{direction}_{row}_{col}.svg")
                png_path = svg_path.replace(".svg", ".png")
                with open(svg_path, "w") as f:
                    f.write(svg)
                svg2png(url=svg_path, write_to=png_path, output_width=img_w, output_height=img_h)
                cut = Image.open(png_path).convert("L")
                np_cut = np.array(cut) < 128
                np_mask = np.array(mask)
                if direction == "above":
                    for x in range(img_w):
                        pts = np.where(np_cut[:, x])[0]
                        if len(pts):
                            np_mask[:pts[0], x] = 0
                elif direction == "below":
                    for x in range(img_w):
                        pts = np.where(np_cut[:, x])[0]
                        if len(pts):
                            np_mask[pts[-1]:, x] = 0
                elif direction == "left":
                    for y in range(img_h):
                        pts = np.where(np_cut[y, :])[0]
                        if len(pts):
                            np_mask[y, :pts[0]] = 0
                elif direction == "right":
                    for y in range(img_h):
                        pts = np.where(np_cut[y, :])[0]
                        if len(pts):
                            np_mask[y, pts[-1]:] = 0
                mask = Image.fromarray(np_mask)

            piece = Image.new("RGBA", img.size, (0, 0, 0, 0))
            piece.paste(img, (0, 0), mask)
            pieces_dir = os.path.join(args.output, "pieces")
            os.makedirs(pieces_dir, exist_ok=True)
            outpath = os.path.join(pieces_dir, f"{row}_{col}.png")
            piece.save(outpath)
            print(f"Saved {outpath}")

    shutil.rmtree(tempdir)

if __name__ == "__main__":
    main()
