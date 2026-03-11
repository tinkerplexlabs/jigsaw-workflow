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

    viewbox = root.attrib.get("viewBox", "0 0 1024 1024").split()
    width, height = int(float(viewbox[2])), int(float(viewbox[3]))

    ns = {'svg': 'http://www.w3.org/2000/svg'}
    paths = root.findall(".//svg:path", ns)

    horizontal = []
    vertical = []

    for p in paths:
        d = p.attrib.get("d")
        cls = p.attrib.get("class", "")
        class_tokens = set(cls.strip().split())

        if "horizontal" in class_tokens:
            horizontal.append({"d": d})
        elif "vertical" in class_tokens:
            vertical.append({"d": d})

    return width, height, horizontal, vertical


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


def write_split_svg(output_svg, width, height, horizontal, vertical):
    with open(output_svg, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">\n')
        for p in horizontal:
            f.write(f'  <path d="{p["d"]}" class="horizontal" stroke="black" fill="none" stroke-width="1"/>\n')
        for p in vertical:
            f.write(f'  <path d="{p["d"]}" class="vertical" stroke="black" fill="none" stroke-width="1"/>\n')
        f.write('</svg>\n')
    print(f"Wrote split SVG to {output_svg}")


def main():
    args = parse_arguments()
    width, height, horizontal, vertical = extract_paths(args.input_svg)
    write_ipuz(args.output_json, width, height, horizontal, vertical)
    write_split_svg(args.output_svg, width, height, horizontal, vertical)


if __name__ == "__main__":
    main()
