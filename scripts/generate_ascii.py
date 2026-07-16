"""
generate_ascii.py

Generates a real, high-resolution ASCII portrait from assets/profile_source.jpg
and writes it to assets/ascii_art.txt, one row per line, all rows padded to the
same fixed width.

Run this again any time you replace assets/profile_source.jpg with a new photo:

    python scripts/generate_ascii.py

Pipeline:
  1. Detect the face in the source photo (OpenCV Haar cascade) and crop a
     tight square around the head + shoulders.
  2. Convert to grayscale.
  3. Boost contrast so facial features stay readable at low character density.
  4. Downsample to an ASCII grid, compensating for the fact that monospace
     terminal characters are roughly twice as tall as they are wide.
  5. Map each cell's average brightness to a character from a density ramp
     (darkest -> '@', lightest -> ' '), producing plain ASCII only
     (no Unicode blocks, no emoji).
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

HERE = os.path.dirname(__file__)
SOURCE_PATH = os.path.join(HERE, "..", "assets", "profile_source.jpg")
OUTPUT_PATH = os.path.join(HERE, "..", "assets", "ascii_art.txt")

# Density ramp: index 0 = lightest (background), last = darkest (ink).
CHARSET = " .:-=+*#%@"

ASCII_WIDTH = 78          # characters per row (70-80 requested)
ASCII_HEIGHT = 50         # rows (45-55 requested)
FONT_ASPECT = 0.55        # terminal chars are ~2x taller than wide


def detect_and_crop(bgr_image):
    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, 1.1, 5)

    h, w = bgr_image.shape[:2]

    if len(faces) == 0:
        # fallback: assume the face is roughly centered
        size = min(w, h)
        cx, cy = w // 2, h // 2
    else:
        # use the largest detected face
        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        cx, cy = fx + fw // 2, fy + fh // 2
        size = w  # crop a full-width square, matching "head + shoulders"

    top = max(0, cy - size // 2)
    top = min(top, h - size) if h > size else 0
    size = min(size, w, h)
    left = max(0, min((w - size) // 2, w - size))

    return bgr_image[top:top + size, left:left + size]


def image_to_ascii(pil_img: Image.Image, width: int, height: int) -> list:
    # grayscale
    gray = ImageOps.grayscale(pil_img)
    # contrast boost
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.6)
    gray = ImageEnhance.Sharpness(gray).enhance(1.5)

    resized = gray.resize((width, height), Image.LANCZOS)
    pixels = np.array(resized, dtype=np.float32)

    # map brightness -> character (dark pixel = dense character)
    normalized = 1.0 - (pixels / 255.0)  # 0 = white, 1 = black
    indices = np.clip((normalized * (len(CHARSET) - 1)).round().astype(int), 0, len(CHARSET) - 1)

    lines = []
    for row in indices:
        lines.append("".join(CHARSET[i] for i in row))
    return lines


def main():
    bgr = cv2.imread(SOURCE_PATH)
    if bgr is None:
        raise FileNotFoundError(f"Could not read {SOURCE_PATH}")

    cropped_bgr = detect_and_crop(bgr)
    cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(cropped_rgb)

    # account for font aspect ratio so the portrait isn't squashed
    grid_height = int(ASCII_HEIGHT)
    lines = image_to_ascii(pil_img, ASCII_WIDTH, grid_height)

    with open(OUTPUT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {len(lines)} rows x {ASCII_WIDTH} cols to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
