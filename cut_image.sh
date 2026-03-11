#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 <image> <output_dir> [--grid COLS ROWS] [--seed SEED] [--tabsize SIZE] [--jitter JITTER]"
    echo ""
    echo "Generate a jigsaw SVG and cut an image into pieces."
    echo ""
    echo "Arguments:"
    echo "  image        Input image (PNG or JPG)"
    echo "  output_dir   Directory for output (pieces go in output_dir/pieces/)"
    echo ""
    echo "Options:"
    echo "  --grid COLS ROWS   Grid size (default: 4 4)"
    echo "  --seed SEED        Random seed for reproducible cuts"
    echo "  --tabsize SIZE     Tab size percentage (default: 20.0)"
    echo "  --jitter JITTER    Jitter percentage (default: 4.0)"
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

IMAGE="$1"
OUTPUT_DIR="$2"
shift 2

if [ ! -f "$IMAGE" ]; then
    echo "Error: image '$IMAGE' not found"
    exit 1
fi

# Defaults
COLS=4
ROWS=4
SEED=""
TABSIZE=20.0
JITTER=4.0

# Parse optional args
while [ $# -gt 0 ]; do
    case "$1" in
        --grid)
            COLS="$2"
            ROWS="$3"
            shift 3
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        --tabsize)
            TABSIZE="$2"
            shift 2
            ;;
        --jitter)
            JITTER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SVG_PATH="$OUTPUT_DIR/outline.svg"

mkdir -p "$OUTPUT_DIR"

# Build seed arg
SEED_ARG=""
if [ -n "$SEED" ]; then
    SEED_ARG="--seed $SEED"
fi

echo "=== Generating ${COLS}x${ROWS} jigsaw SVG ==="
python3 "$SCRIPT_DIR/gen_jigsaw.py" \
    --grid "$COLS" "$ROWS" \
    --tabsize "$TABSIZE" \
    --jitter "$JITTER" \
    $SEED_ARG \
    -o "$SVG_PATH"

echo ""
echo "=== Extracting pieces ==="
python3 "$SCRIPT_DIR/extract_pieces.py" \
    "$IMAGE" \
    "$SVG_PATH" \
    --output "$OUTPUT_DIR"

echo ""
echo "Done. Pieces in $OUTPUT_DIR/pieces/"
