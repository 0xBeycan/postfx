import numpy as np

from postfx import imgio


def test_seed_from_path_deterministic_and_basename_based():
    s1 = imgio.seed_from_path("/a/b/c/photo.png")
    s2 = imgio.seed_from_path("/completely/different/photo.png")
    s3 = imgio.seed_from_path("/a/b/c/other.png")
    assert s1 == s2                      # same file name => same seed (portable)
    assert s1 != s3
    assert 0 <= s1 < 2 ** 32


def test_save_load_roundtrip_preserves_resolution(tmp_path, rgb_image):
    out = tmp_path / "sub" / "x.png"
    imgio.save_image(out, rgb_image)
    assert out.exists()
    back, alpha = imgio.load_image(out)
    assert back.shape == rgb_image.shape
    assert np.abs(back - rgb_image).max() < 0.02   # 8-bit rounding tolerance


def test_png_preserves_alpha(tmp_path):
    rgb = np.random.default_rng(0).random((32, 24, 3)).astype(np.float32)
    alpha = (np.random.default_rng(1).random((32, 24)) * 255).astype(np.uint8)
    out = tmp_path / "a.png"
    imgio.save_image(out, rgb, alpha=alpha)
    back, back_alpha = imgio.load_image(out)
    assert back_alpha is not None
    assert back_alpha.shape == (32, 24)


def test_encode_decode_roundtrip(rgb_image):
    data = imgio.encode_image(rgb_image, ext=".png")
    back = imgio.decode_image(data)
    assert back.shape == rgb_image.shape
    assert np.abs(back - rgb_image).max() < 0.02


def test_jpeg_output_extension(tmp_path, rgb_image):
    out = tmp_path / "x.jpg"
    imgio.save_image(out, rgb_image, jpeg_quality=80, jpeg_cycles=1)
    assert out.exists()
    back, _ = imgio.load_image(out)
    assert back.shape == rgb_image.shape
