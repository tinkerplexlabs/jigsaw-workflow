#!/usr/bin/env python3
"""
FastAPI service for generating jigsaw puzzle packs.

Accepts an image upload + parameters, runs the puzzle pipeline,
and returns a .zip file containing the puzzle pack.
"""

import os
import shutil
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse

from create_puzzle_pack import create_puzzle_pack, create_zip_archive

app = FastAPI(title="Puzzle Pack Generator")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate(
    image: UploadFile = File(...),
    pack_name: str = Form("Puzzle"),
    grids: str = Form("8x8,12x12,15x15"),
    author: str = Form(""),
    copyright: str = Form(""),
):
    """Generate a puzzle pack from an uploaded image.

    Returns the .zip archive directly as a download.
    """
    work_dir = tempfile.mkdtemp(prefix="puzzle_")
    try:
        # Save uploaded image to temp file
        image_path = os.path.join(work_dir, image.filename or "input.png")
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)

        # Run the pipeline
        output_dir = os.path.join(work_dir, "output")
        pack_dir = create_puzzle_pack(
            image_path, pack_name, grids, output_dir, author, copyright
        )
        create_zip_archive(pack_dir)

        zip_path = f"{pack_dir}.zip"
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{pack_name}.zip",
            background=_cleanup(work_dir),
        )
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise


def _cleanup(work_dir: str):
    """Background task to clean up temp files after response is sent."""
    from starlette.background import BackgroundTask

    return BackgroundTask(shutil.rmtree, work_dir, True)
