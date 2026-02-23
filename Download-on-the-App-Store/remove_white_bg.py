#!/usr/bin/env python3
"""Remove white background from PNGs - use floodfill from corners to preserve
white logo/text (only remove background white connected to edges)."""
import os
from PIL import Image, ImageDraw

PNG_DIR = os.path.join(os.path.dirname(__file__), "black_lockup_all_png")

for name in os.listdir(PNG_DIR):
    if not name.endswith(".png"):
        continue
    path = os.path.join(PNG_DIR, name)
    try:
        img = Image.open(path).convert("RGBA")
        w, h = img.size
        # Floodfill from corners - only removes white connected to edges
        # (preserves white Apple logo/text in center)
        for seed in [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]:
            try:
                ImageDraw.floodfill(img, seed, (0, 0, 0, 0), thresh=20)
            except (ValueError, OSError):
                pass  # Corner might not be white
        img.save(path)
        print(f"OK: {name}")
    except Exception as e:
        print(f"FAIL: {name} - {e}")

print("Done. White backgrounds removed.")
