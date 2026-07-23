import subprocess
import sys

import numpy as np

import postfx
from postfx import imgio


def test_process_file_end_to_end(tmp_path, rgb_image):
    src = tmp_path / "in.png"
    dst = tmp_path / "out" / "in.png"
    imgio.save_image(src, rgb_image)
    result = postfx.process_file(src, dst, theme="portra_400",
                                 scene="day_outdoor", strength=1.0)
    assert str(result) == str(dst)
    back, _ = imgio.load_image(dst)
    assert back.shape == rgb_image.shape


def test_process_file_same_input_same_output(tmp_path, rgb_image):
    src = tmp_path / "same.png"
    imgio.save_image(src, rgb_image)
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    postfx.process_file(src, a, theme="cinestill_800t", scene="night_flash")
    postfx.process_file(src, b, theme="cinestill_800t", scene="night_flash")
    ia, _ = imgio.load_image(a)
    ib, _ = imgio.load_image(b)
    assert np.array_equal(ia, ib)             # determinism: identical output


def test_cli_list_runs():
    out = subprocess.run([sys.executable, "-m", "postfx", "list"],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert "portra_400" in out.stdout
    assert "night_flash" in out.stdout
