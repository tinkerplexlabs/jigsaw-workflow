#!/usr/bin/env python3

import argparse
import math
import random


class JigsawGenerator:
    def __init__(self, xn, yn, tab_size, jitter, seed):
        self.width = xn
        self.height = yn
        self.xn = xn
        self.yn = yn
        self.t = tab_size / 200.0
        self.j = jitter / 100.0
        self.seed = seed
        self.offset = 0.0
        
        # Initialize variables needed for puzzle generation
        self.a = 0
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 0
        self.flip = False
        self.xi = 0
        self.yi = 0
        self.vertical = False
        
        # Set random seed
        random.seed(self.seed)
        
    def random(self):
        """Replacement for the JavaScript random function based on sine"""
        x = math.sin(self.seed) * 10000
        self.seed += 1
        return x - math.floor(x)
    
    def uniform(self, min_val, max_val):
        """Generate a random number in the range [min_val, max_val]"""
        r = self.random()
        return min_val + r * (max_val - min_val)
    
    def rbool(self):
        """Random boolean"""
        return self.random() > 0.5
    
    def first(self):
        """Initialize the first tab"""
        self.e = self.uniform(-self.j, self.j)
        self.next()
        
    def next(self):
        """Calculate parameters for the next tab"""
        flip_old = self.flip
        self.flip = self.rbool()
        self.a = -self.e if self.flip == flip_old else self.e
        self.b = self.uniform(-self.j, self.j)
        self.c = self.uniform(-self.j, self.j)
        self.d = self.uniform(-self.j, self.j)
        self.e = self.uniform(-self.j, self.j)
    
    def sl(self):
        """Segment length"""
        return self.height / self.yn if self.vertical else self.width / self.xn
    
    def sw(self):
        """Segment width"""
        return self.width / self.xn if self.vertical else self.height / self.yn
    
    def ol(self):
        """Offset length"""
        return self.offset + self.sl() * (self.yi if self.vertical else self.xi)
    
    def ow(self):
        """Offset width"""
        return self.offset + self.sw() * (self.xi if self.vertical else self.yi)
    
    def l(self, v):
        """Calculate length coordinate"""
        ret = self.ol() + self.sl() * v
        return round(ret * 100) / 100
    
    def w(self, v):
        """Calculate width coordinate"""
        multiplier = -1.0 if self.flip else 1.0
        ret = self.ow() + self.sw() * v * multiplier
        return round(ret * 100) / 100
    
    # Anchor points for each cell edge (all lie ON the curve)
    def _cell_anchors(self):
        """Return the 10 anchor points for the current cell edge in (l, w) form."""
        return [
            (self.l(0.0),                      self.w(0.0)),
            (self.l(0.2),                      self.w(self.a)),
            (self.l(0.5 + self.b + self.d),    self.w(-self.t + self.c)),
            (self.l(0.5 - self.t + self.b),    self.w(self.t + self.c)),
            (self.l(0.5 - 2*self.t + self.b - self.d), self.w(3*self.t + self.c)),
            (self.l(0.5 + 2*self.t + self.b - self.d), self.w(3*self.t + self.c)),
            (self.l(0.5 + self.t + self.b),    self.w(self.t + self.c)),
            (self.l(0.5 + self.b + self.d),    self.w(-self.t + self.c)),
            (self.l(0.8),                      self.w(self.e)),
            (self.l(1.0),                      self.w(0.0)),
        ]

    @staticmethod
    def _catmull_rom_path(anchors, swap=False):
        """Generate an SVG path through *anchors* using Catmull-Rom → cubic bezier.

        If *swap* is True the (l, w) pairs are emitted as (w, l) — used for
        vertical cuts where the length axis is y.
        """
        def fmt(l, w):
            x, y = (w, l) if swap else (l, w)
            return f"{round(x * 100) / 100} {round(y * 100) / 100}"

        n = len(anchors)
        al, aw = anchors[0]
        x0, y0 = (aw, al) if swap else (al, aw)
        path = f"M {round(x0*100)/100},{round(y0*100)/100} "

        for i in range(n - 1):
            # Tangent at anchor i
            if i == 0:
                tl0 = anchors[1][0] - anchors[0][0]
                tw0 = anchors[1][1] - anchors[0][1]
            else:
                tl0 = (anchors[i + 1][0] - anchors[i - 1][0]) / 2
                tw0 = (anchors[i + 1][1] - anchors[i - 1][1]) / 2

            # Tangent at anchor i+1
            if i + 1 == n - 1:
                tl1 = anchors[n - 1][0] - anchors[n - 2][0]
                tw1 = anchors[n - 1][1] - anchors[n - 2][1]
            else:
                tl1 = (anchors[i + 2][0] - anchors[i][0]) / 2
                tw1 = (anchors[i + 2][1] - anchors[i][1]) / 2

            # Convert to cubic bezier control points
            cp1 = (anchors[i][0] + tl0 / 3,     anchors[i][1] + tw0 / 3)
            cp2 = (anchors[i + 1][0] - tl1 / 3, anchors[i + 1][1] - tw1 / 3)

            path += (f"C {fmt(*cp1)} {fmt(*cp2)} "
                     f"{fmt(*anchors[i + 1])} ")

        return path

    def gen_dh(self):
        """Generate horizontal dividers (including top and bottom border edges)"""
        paths = []
        self.vertical = False

        paths.append(f"M 0,0 L {self.width},0 ")

        for self.yi in range(1, self.yn):
            self.xi = 0
            self.first()

            # Collect anchor points across all cells in this row
            anchors = []
            for self.xi in range(0, self.xn):
                pts = self._cell_anchors()
                if self.xi == 0:
                    anchors.extend(pts)
                else:
                    anchors.extend(pts[1:])  # p0 duplicates previous p9
                self.next()

            paths.append(self._catmull_rom_path(anchors, swap=False))

        paths.append(f"M 0,{self.height} L {self.width},{self.height} ")
        return paths

    def gen_dv(self):
        """Generate vertical dividers (including left and right border edges)"""
        paths = []
        self.vertical = True

        paths.append(f"M 0,0 L 0,{self.height} ")

        for self.xi in range(1, self.xn):
            self.yi = 0
            self.first()

            anchors = []
            for self.yi in range(0, self.yn):
                pts = self._cell_anchors()
                if self.yi == 0:
                    anchors.extend(pts)
                else:
                    anchors.extend(pts[1:])
                self.next()

            paths.append(self._catmull_rom_path(anchors, swap=True))

        paths.append(f"M {self.width},0 L {self.width},{self.height} ")
        return paths
    
    def gen_db(self):
        """Generate border"""
        path = f"M {self.offset + self.corner_radius} {self.offset} "
        path += f"L {self.offset + self.width - self.corner_radius} {self.offset} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset + self.width} {self.offset + self.corner_radius} ")
        path += f"L {self.offset + self.width} {self.offset + self.height - self.corner_radius} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset + self.width - self.corner_radius} {self.offset + self.height} ")
        path += f"L {self.offset + self.corner_radius} {self.offset + self.height} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset} {self.offset + self.height - self.corner_radius} ")
        path += f"L {self.offset} {self.offset + self.corner_radius} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset + self.corner_radius} {self.offset} ")
        
        return path
    
    def generate_svg(self):
        """Generate the complete SVG file content"""
        # Reset seed to ensure consistent results
        random.seed(self.seed)
        self.seed = self.seed
        
        # SVG header
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" version="1.0" '
               f'viewBox="0 0 {self.width} {self.height}">\n')

        for d in self.gen_dh():
            svg += f'  <path d="{d}" class="horizontal" fill="none" stroke="black" stroke-width="0.01"/>\n'

        for d in self.gen_dv():
            svg += f'  <path d="{d}" class="vertical" fill="none" stroke="black" stroke-width="0.01"/>\n'

        svg += '</svg>\n'
        return svg


def main():
    parser = argparse.ArgumentParser(description='Generate a jigsaw puzzle SVG file')
    parser.add_argument('--grid', nargs=2, type=int, default=[15, 10], metavar=('COLS', 'ROWS'),
                        help='Number of columns and rows (default: 15 10)')
    parser.add_argument('-o', '--output', type=str, default='jigsaw.svg',
                        help='Output SVG file (default: jigsaw.svg)')
    parser.add_argument('--jitter', type=float, default=4.0,
                        help='Jitter percentage (default: 4.0)')
    parser.add_argument('--tabsize', type=float, default=20.0,
                        help='Tab size percentage (default: 20.0)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed (default: random)')

    args = parser.parse_args()

    # Use current time as seed if none provided
    if args.seed is None:
        args.seed = int(random.random() * 10000)

    # Create jigsaw generator
    jigsaw = JigsawGenerator(
        xn=args.grid[0],
        yn=args.grid[1],
        tab_size=args.tabsize,
        jitter=args.jitter,
        seed=args.seed,
    )

    # Generate SVG content
    svg_content = jigsaw.generate_svg()

    # Save to file
    with open(args.output, 'w') as f:
        f.write(svg_content)

    print(f"Jigsaw puzzle saved to {args.output}")
    print(f"Grid: {args.grid[0]} x {args.grid[1]}")
    print(f"Seed: {args.seed}")


if __name__ == "__main__":
    main()
