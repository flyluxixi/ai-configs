#!/usr/bin/env python3
"""crop_image.py 的离线单元测试（纯标准库，无网络）。

运行：python3 test_crop_image.py
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("crop", Path(__file__).with_name("crop_image.py"))
crop = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crop)


class TestPngRoundtrip(unittest.TestCase):
    def test_rgb_roundtrip_preserves_pixels_and_colortype(self):
        # 3x2 RGB，已知像素
        w, h, ch = 3, 2, 3
        px = bytes([10, 10, 10, 20, 20, 20, 30, 30, 30,
                    40, 40, 40, 50, 50, 50, 60, 60, 60])
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "t.png")
            crop.write_png(p, w, h, ch, px)
            # color type 必须是 2 (RGB)，不能是 0 (灰度)——这是曾经的 bug
            self.assertEqual(Path(p).read_bytes()[25], 2)
            self.assertEqual(crop.read_png(p), (w, h, ch, px))

    def test_rgba_roundtrip(self):
        w, h, ch = 2, 2, 4
        px = bytes([1, 2, 3, 255, 4, 5, 6, 0,
                    7, 8, 9, 128, 10, 11, 12, 64])
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "t.png")
            crop.write_png(p, w, h, ch, px)
            self.assertEqual(Path(p).read_bytes()[25], 6)  # RGBA
            self.assertEqual(crop.read_png(p), (w, h, ch, px))


class TestCropPixels(unittest.TestCase):
    def test_crop_subrect(self):
        # 3x2 RGB，裁出右下 2x2（列1-2，行0-1）
        w, ch = 3, 3
        px = bytes([10, 10, 10, 20, 20, 20, 30, 30, 30,
                    40, 40, 40, 50, 50, 50, 60, 60, 60])
        cw, chh, out = crop.crop_pixels(w, ch, px, left=1, top=0, right=3, bottom=2)
        self.assertEqual((cw, chh), (2, 2))
        self.assertEqual(out, bytes([20, 20, 20, 30, 30, 30, 50, 50, 50, 60, 60, 60]))


class TestCropEndToEnd(unittest.TestCase):
    def test_write_crop_read_matches_source_region(self):
        w, h, ch = 4, 3, 3
        # 每像素用唯一值，便于核对
        px = bytes(v for i in range(w * h) for v in (i, i, i))
        with tempfile.TemporaryDirectory() as d:
            src = str(Path(d) / "src.png")
            crop.write_png(src, w, h, ch, px)
            rw, rh, rch, rpx = crop.read_png(src)
            cw, chh, cpx = crop.crop_pixels(rw, rch, rpx, 1, 1, 3, 3)
            dst = str(Path(d) / "out.png")
            crop.write_png(dst, cw, chh, rch, cpx)
            ow, oh, och, opx = crop.read_png(dst)
            self.assertEqual((ow, oh, och), (2, 2, 3))
            # 期望：原图 (1,1)(2,1)(1,2)(2,2) 四个像素，索引 = y*w+x = 5,6,9,10
            self.assertEqual(opx, bytes(v for idx in (5, 6, 9, 10) for v in (idx, idx, idx)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
