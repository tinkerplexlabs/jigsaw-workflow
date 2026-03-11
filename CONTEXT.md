# Jigsaw Puzzle Toolkit - Project Context

## Project Overview

A Python toolkit for generating jigsaw puzzle SVG outlines, cutting images into puzzle pieces, and reassembling them. The end goal is creating puzzle packs (directories of puzzle pieces + metadata) that can be consumed by a jigsaw puzzle app.

## Directory: `/home/daniel/work/pieces`

Python venv at `./venv` with: `cairosvg`, `Pillow`, `numpy`, `scipy`.

## Pipeline / Workflow

The full puzzle creation pipeline is:

```
Input Image
    |
    v
gen_jigsaw.py          -- Generate SVG with jigsaw cut paths (Catmull-Rom splines)
    |                      Output: outline.svg (each cut is a separate <path> with class="horizontal"|"vertical")
    v
svg_to_ipuz.py         -- Convert SVG to ipuz format + split SVG
    |                      Output: layout.ipuz.json (with cutArrays), outline-split.svg
    v
extract_pieces.py      -- Cut image into pieces using SVG paths (NEW, replaces jigsaw_piece_extractor_exact.py)
    |                      Uses cairosvg + flood fill + scipy EDT for boundary assignment
    |                      Output: pieces/{row}_{col}.png (cropped to bounding box) + layout.ipuz.json (with pieces array)
    v
reassemble_puzzle.py   -- Reassemble pieces back into original image (verification tool)
                           Reads layout.ipuz.json with pieces+canvas fields, pastes cropped pieces at (x,y) positions
```

There is also:
- `create_puzzle_pack.py` -- Orchestrator that runs the full pipeline for multiple grid sizes
- `cut_image.sh` -- Convenience wrapper: gen_jigsaw.py + extract_pieces.py in one command

## Key Files

### `gen_jigsaw.py` - SVG Jigsaw Generator
- Generates jigsaw puzzle cut paths as SVG
- Uses Catmull-Rom splines converted to cubic bezier curves for smooth tab shapes
- ViewBox uses grid dimensions directly (e.g., 8x8 grid -> viewBox "0 0 8 8")
- Each cut line is a separate `<path>` element with `class="horizontal"` or `class="vertical"`
- Border edges (straight lines) are included in horizontal/vertical sets (first and last of each)
- `--grid COLS ROWS --seed N --tabsize 20 --jitter 4`
- Has unused `gen_db()` method for rounded-corner border (references undefined `self.corner_radius`)

### `svg_to_ipuz.py` - SVG to iPuz Converter
- Converts gen_jigsaw.py output SVG into:
  1. `layout.ipuz.json` with `cutArrays` (horizontal/vertical path data) and `pieceSettings`
  2. `outline-split.svg` (same paths re-emitted individually)
- Does NOT produce `pieces` array -- that comes from extract_pieces.py

### `extract_pieces.py` - Piece Extractor (CURRENT/PREFERRED)
- **This is the newer, correct extractor.** Replaces `jigsaw_piece_extractor_exact.py`.
- Handles two SVG formats:
  - "split" format: each cut in its own `<path>` element (from gen_jigsaw.py or svg_to_ipuz.py)
  - "combined" format: all cuts in one `<path>` with multiple M commands (splits on `(?=M\s*[\d.])`)
- Determines grid size by counting only interior cuts (those containing `C` bezier commands), not border lines
- Uses cairosvg to render cut lines at pixel resolution (stroke width: 3px in viewBox units)
- Paints solid black borders on rendered image edges to seal flood fill
- Flood fills from each cell center to identify piece regions
- Assigns boundary pixels (cut lines) to nearest piece using `scipy.ndimage.distance_transform_edt` (Euclidean distance, NOT BFS dilation -- BFS leaked through connected unclaimed corridors along borders)
- Outputs cropped pieces (bounding box only, not full canvas size) as RGBA PNGs
- Writes `layout.ipuz.json` with:
  ```json
  {
    "version": "http://ipuz.org/v2",
    "kind": ["http://ipuz.org/jigsaw#1"],
    "canvas": {"width": W, "height": H},
    "grid": {"rows": R, "cols": C},
    "pieces": [{"id": "0_0", "row": 0, "col": 0, "x": X, "y": Y, "width": W, "height": H}, ...]
  }
  ```

### `jigsaw_piece_extractor_exact.py` - LEGACY Piece Extractor
- **Older version. Still referenced by `create_puzzle_pack.py` but should be replaced.**
- Produces FULL-CANVAS-SIZE pieces (every piece PNG is img_width x img_height -- very wasteful)
- Uses `ImageFilter.MaxFilter(3)` dilation instead of proper EDT boundary assignment
- stroke-width="1" in viewBox units (very thick relative to image)
- Grid size calculation: `rows = len(horizontal_cuts) - 1` (works for split SVGs but fails on combined format)
- Does NOT output piece position metadata

### `reassemble_puzzle.py` - Puzzle Reassembler
- Reads `layout.ipuz.json` with `pieces` and `canvas` fields (no legacy fallbacks)
- Creates RGBA canvas, pastes each cropped piece at its (x, y) position
- Optional jigsaw line overlay using `--jigsaw auto` (renders outline.svg as colored lines on top)
- Supports `--verify` to check dimensions against preview.jpg
- Usage: `python reassemble_puzzle.py <pack_dir> --grid 8x8 [--jigsaw auto] [--output-file out.png]`

### `create_puzzle_pack.py` - Pack Orchestrator
- Creates puzzle packs with multiple grid sizes from a single image
- Normalizes input image to `TILE_SIZE * grid` dimensions (TILE_SIZE=256, base=2048 for 8x8)
- Runs: gen_jigsaw.py -> svg_to_ipuz.py -> jigsaw_piece_extractor_exact.py (LEGACY!)
- **Known issue: still calls `jigsaw_piece_extractor_exact.py` instead of `extract_pieces.py`**
- The layout.ipuz.json it produces (via svg_to_ipuz.py) has `cutArrays` but no `pieces` array
- Creates manifest.json, preview.jpg, and .zip archive

### `cut_image.sh` - Convenience Script
- Runs gen_jigsaw.py then extract_pieces.py (the NEW extractor) in sequence
- Usage: `./cut_image.sh <image> <output_dir> [--grid COLS ROWS] [--seed SEED]`

### Shell scripts
- `gen_sizes.sh` - Generates 8x8, 12x12, 15x15 SVGs with jitter=10
- `gen_pack.sh` - Old script referencing nonexistent `jigsaw_piece_extractor.py`

## Data Formats

### Puzzle Pack Directory Structure
```
pack_name/
  manifest.json           # Pack metadata
  puzzle_01/
    preview.jpg           # Full image preview
    layouts/
      8x8/
        outline.svg       # Jigsaw cut paths (from gen_jigsaw.py)
        outline-split.svg # Same paths, re-emitted individually (from svg_to_ipuz.py)
        layout.ipuz.json  # Metadata: cutArrays + pieces positions
        pieces/
          0_0.png         # Cropped piece images (row_col.png)
          0_1.png
          ...
      12x12/
        ...
```

### layout.ipuz.json (two producers, should be merged)
- **From svg_to_ipuz.py**: has `cutArrays` (path data), `pieceSettings`, `canvas` -- no `pieces`
- **From extract_pieces.py**: has `canvas`, `grid`, `pieces` (bounding box positions) -- no `cutArrays`
- `reassemble_puzzle.py` requires the version with `pieces` and `canvas`

## Known Issues / Potential Follow-ups

1. **`create_puzzle_pack.py` uses the legacy extractor** (`jigsaw_piece_extractor_exact.py`) instead of the newer `extract_pieces.py`. Should be updated.

2. **Two separate layout.ipuz.json files are produced** by `svg_to_ipuz.py` and `extract_pieces.py` in the `create_puzzle_pack.py` pipeline. The svg_to_ipuz.py version has `cutArrays`; the extract_pieces.py version has `pieces`. These could be merged into one file.

3. **`gen_jigsaw.py` has an unused `gen_db()` method** that references undefined `self.corner_radius`.

4. **`gen_pack.sh` references nonexistent `jigsaw_piece_extractor.py`** (old name).

## History of Bugs Fixed (for context)

- **ZeroDivisionError in extract_pieces.py**: SVG parsing couldn't count grid dimensions from SVGs with all cuts in one `<path>` element. Fixed by splitting `d` attributes on M commands and counting only interior cuts (containing `C`).

- **Flood fill boundary leaking**: Edge pieces spanned the full image height because BFS dilation propagated through connected unclaimed border strips. Fixed by replacing BFS with `scipy.ndimage.distance_transform_edt` which assigns each unclaimed pixel to the nearest claimed pixel by Euclidean (not geodesic) distance.

- **Reassemble incompatible with cropped pieces**: Old reassembler expected full-canvas-size pieces. Fixed by adding piece position metadata to layout.ipuz.json and rewriting reassembler to paste cropped pieces at (x, y) offsets.

## Dependencies

```
cairosvg    # SVG rendering (bezier curves)
Pillow      # Image manipulation
numpy       # Array operations for masks
scipy       # distance_transform_edt for boundary pixel assignment
```
