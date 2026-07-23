"""Image load/save — resolution & aspect preserved, no metadata written.

Load: 8/16-bit and alpha supported, normalized to float32 [0,1] RGB.
Save: 8-bit, clean (no EXIF/metadata — cv2.imwrite writes minimal). PNG keeps
alpha; JPEG applies an optional re-encode loop.
"""

import hashlib
import os

import cv2
import numpy as np

from . import ops

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def seed_from_path(path):
    """Derive a deterministic 32-bit seed from the file NAME (basename). The
    same image gets the same grain even if the folder changes.
    """
    name = os.path.basename(str(path))
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2 ** 32 - 1)


def load_image(path):
    """Load an image as float32 [0,1] RGB. Returns (rgb, alpha); alpha is None
    if absent. Bit depth is normalized automatically.
    """
    data = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if data is None:
        raise FileNotFoundError(f"Could not read image: {path}")

    if data.ndim == 2:
        data = cv2.cvtColor(data, cv2.COLOR_GRAY2BGR)

    alpha = None
    if data.shape[2] == 4:
        alpha = data[..., 3].copy()
        data = data[..., :3]

    if data.dtype == np.uint16:
        scale = 65535.0
    elif data.dtype == np.uint8:
        scale = 255.0
    else:  # float (EXR/HDR etc.) — assumed already [0,1]
        scale = 1.0

    rgb = cv2.cvtColor(data, cv2.COLOR_BGR2RGB).astype(np.float32) / scale
    return rgb, alpha


def save_image(path, rgb, alpha=None, jpeg_quality=95, jpeg_cycles=0):
    """Save float32 [0,1] RGB as 8-bit. If the extension is JPEG, apply the
    re-encode loop (jpeg_cycles); if PNG, re-attach alpha and skip the loop.
    """
    path = str(path)
    u8 = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)
    ext = os.path.splitext(path)[1].lower()

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    if ext in (".jpg", ".jpeg"):
        if jpeg_cycles > 0:
            bgr = ops.jpeg_cycle(bgr, jpeg_quality, jpeg_cycles)
        cv2.imwrite(path, bgr, [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)])
    else:
        if alpha is not None:
            a8 = alpha
            if a8.dtype == np.uint16:
                a8 = (a8 / 257.0 + 0.5).astype(np.uint8)
            elif a8.dtype != np.uint8:
                a8 = np.clip(a8 * 255.0 + 0.5, 0, 255).astype(np.uint8)
            bgr = np.dstack([bgr, a8])
        cv2.imwrite(path, bgr)


def encode_image(rgb, ext=".jpg", jpeg_quality=95, jpeg_cycles=0):
    """Encode float32 [0,1] RGB to in-memory bytes (for the API). No file write."""
    u8 = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)
    if ext.lower() in (".jpg", ".jpeg"):
        if jpeg_cycles > 0:
            bgr = ops.jpeg_cycle(bgr, jpeg_quality, jpeg_cycles)
        ok, buf = cv2.imencode(".jpg", bgr,
                               [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)])
    else:
        ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("Failed to encode image.")
    return buf.tobytes()


def decode_image(data):
    """Decode in-memory bytes to float32 [0,1] RGB (for the API)."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image (invalid data).")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def list_images(folder):
    """Return supported image files in a folder, sorted."""
    out = [os.path.join(folder, f) for f in os.listdir(folder)
           if f.lower().endswith(IMAGE_EXTS)]
    return sorted(out)
