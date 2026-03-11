# Generate just SVG outlines for a puzzle pack
# python3 gen_jigsaw.py --pack-name "Cat" --num-puzzles 3 --grid-sizes 8x8 16x16 32x32 \
#     --author "Dan Shields" --description "Test images for default puzzle pack"


# Create a complete puzzle pack from images
python3 create_puzzle_pack.py cat1.png "Cat" \
    --author "Dan Shields" \
    --grids 8x8 \
    --output my_puzzle_pack

# # Use the bash script for complete pack creation with intro video
# ./create_puzzle_pack.sh "Holiday Puzzles" photo1.jpg photo2.jpg intro.mp4

