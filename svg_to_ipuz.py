#!/usr/bin/env python3

import argparse
import json
import xml.etree.ElementTree as ET

def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert jigsaw SVG to ipuz format")
    parser.add_argument("input_svg", help="Input SVG file")
    parser.add_argument("--output_json", default="output.ipuz.json", help="Output ipuz JSON file")
    parser.add_argument("--output_svg", default="output-split.svg", help="Output split SVG file")
    return parser.parse_args()


def extract_paths(svg_path):
    tree = ET.parse(svg_path)
    root = tree.getroot()

    width = root.attrib.get("width", "1024").replace("mm", "").replace("px", "")
    height = root.attrib.get("height", "1024").replace("mm", "").replace("px", "")
    width, height = int(float(width)), int(float(height))

    ns = {'svg': 'http://www.w3.org/2000/svg'}
    paths = root.findall(".//svg:path", ns)

    horizontal = []
    vertical = []
    border = None

    def split_multi_path(d):
        # Splits 'M x y ... M x y ...' into ['M x y ...', 'M x y ...']
        if not d.startswith('M '):
            return [d]
        segments = d.split('M ')[1:]
        return ["M " + s.strip() for s in segments if s.strip()]

    for p in paths:
        d = p.attrib.get("d")
        cls = p.attrib.get("class", "")
        class_tokens = set(cls.strip().split())

        if "border" in class_tokens:
            border = d
        elif "horizontal" in class_tokens:
            for seg in split_multi_path(d):
                horizontal.append({"d": seg})
        elif "vertical" in class_tokens:
            for seg in split_multi_path(d):
                vertical.append({"d": seg})

    return width, height, horizontal, vertical, border


def write_ipuz(output_json, width, height, horizontal, vertical):
    ipuz = {
        "version": "http://ipuz.org/v2",
        "kind": ["http://ipuz.org/jigsaw#1"],
        "canvas": {
            "width": width,
            "height": height
        },
        "cutArrays": [
            {"orientation": "horizontal", "paths": horizontal},
            {"orientation": "vertical", "paths": vertical}
        ],
        "pieceSettings": {
            "snapMethod": "bezier-fit",
            "allowRotation": False
        }
    }

    with open(output_json, "w") as f:
        json.dump(ipuz, f, indent=2)
    print(f"Wrote ipuz to {output_json}")


def write_split_svg(output_svg, width, height, horizontal, vertical, border):
    with open(output_svg, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n')
        for p in horizontal:
            f.write(f'  <path d="{p["d"]}" class="horizontal" stroke="black" fill="none" stroke-width="1"/>\n')
        for p in vertical:
            f.write(f'  <path d="{p["d"]}" class="vertical" stroke="black" fill="none" stroke-width="1"/>\n')
        if border:
            f.write(f'  <path d="{border}" class="border" stroke="black" fill="none" stroke-width="1"/>\n')
        f.write('</svg>\n')
    print(f"Wrote split SVG to {output_svg}")


def main():
    args = parse_arguments()
    width, height, horizontal, vertical, border = extract_paths(args.input_svg)
    write_ipuz(args.output_json, width, height, horizontal, vertical)
    write_split_svg(args.output_svg, width, height, horizontal, vertical, border)


if __name__ == "__main__":
    main()
