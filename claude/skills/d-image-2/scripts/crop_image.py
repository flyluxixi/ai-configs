#!/usr/bin/env python3
"""从 PNG 裁剪矩形区域，像素零改变。纯标准库（zlib），无第三方依赖。

用途：从 d-image-2 生成的界面概念稿里裁出满意的插画/图标局部，再送 ChatGPT
网页版图生图转透明（codex 后端出不了透明，见 SKILL.md）。先裁宽松区域用 Read
查看、再收紧 box 迭代到准。
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

CH_BY_CT = {0: 1, 2: 3, 4: 2, 6: 4}  # PNG color type -> 通道数
CT_BY_CH = {1: 0, 2: 4, 3: 2, 4: 6}  # 通道数 -> PNG color type


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crop a rectangular region from a PNG (stdlib only).")
    parser.add_argument("--input", required=True, help="Source PNG path.")
    parser.add_argument("--output", required=True, help="Output PNG path.")
    parser.add_argument("--left", type=int, required=True, help="Left edge (px, inclusive).")
    parser.add_argument("--top", type=int, required=True, help="Top edge (px, inclusive).")
    parser.add_argument("--right", type=int, required=True, help="Right edge (px, exclusive).")
    parser.add_argument("--bottom", type=int, required=True, help="Bottom edge (px, exclusive).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output if it exists.")
    return parser.parse_args()


def read_png(path: str) -> tuple[int, int, int, bytes]:
    """解码 8-bit 非交错 PNG（处理全部 filter），返回 (w, h, channels, 像素字节)。"""
    d = Path(path).read_bytes()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        fail(f"not a PNG: {path}")
    w = struct.unpack(">I", d[16:20])[0]
    h = struct.unpack(">I", d[20:24])[0]
    bit_depth, color_type, interlace = d[24], d[25], d[28]
    if bit_depth != 8:
        fail(f"unsupported bit depth {bit_depth} (only 8-bit)")
    if color_type not in CH_BY_CT:
        fail(f"unsupported color type {color_type} (palette PNG not supported)")
    if interlace != 0:
        fail("interlaced PNG not supported")

    ch = CH_BY_CT[color_type]
    idat = b""
    i = 8
    while i < len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        typ = d[i + 4:i + 8]
        if typ == b"IDAT":
            idat += d[i + 8:i + 8 + ln]
        elif typ == b"IEND":
            break
        i += 12 + ln

    raw = zlib.decompress(idat)
    bpp = ch
    stride = w * bpp
    if len(raw) < (1 + stride) * h:
        fail("corrupt PNG: image data shorter than expected")

    out = bytearray()
    prev = bytearray(stride)
    pos = 0

    def paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    for _ in range(h):
        f = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) // 2)) & 255
            elif f == 4:
                line[x] = (line[x] + paeth(a, b, c)) & 255
            elif f != 0:
                fail(f"unknown PNG filter type {f}")
        out += line
        prev = line
    return w, h, ch, bytes(out)


def write_png(path: str, w: int, h: int, ch: int, px: bytes) -> None:
    """编码 8-bit 非交错 PNG（filter 0），color type 由通道数决定。"""
    color_type = CT_BY_CH[ch]
    stride = w * ch
    raw = b"".join(b"\x00" + px[y * stride:(y + 1) * stride] for y in range(h))

    def chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0)
    Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def crop_pixels(w: int, ch: int, px: bytes, left: int, top: int, right: int, bottom: int) -> tuple[int, int, bytes]:
    """从像素字节裁出子矩形，返回 (裁剪宽, 裁剪高, 裁剪像素)。"""
    stride = w * ch
    out = bytearray()
    for y in range(top, bottom):
        out += px[y * stride + left * ch:y * stride + right * ch]
    return right - left, bottom - top, bytes(out)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        fail(f"input not found: {input_path}")
    output_path = Path(args.output).expanduser()
    if output_path.exists() and not args.overwrite:
        fail(f"output file already exists: {output_path} (use --overwrite to replace it)")

    w, h, ch, px = read_png(str(input_path))
    left, top, right, bottom = args.left, args.top, args.right, args.bottom
    if not (0 <= left < right <= w and 0 <= top < bottom <= h):
        fail(
            f"invalid box ({left},{top},{right},{bottom}) for image {w}x{h}; "
            f"need 0<=left<right<={w} and 0<=top<bottom<={h}"
        )

    cw, chh, crop = crop_pixels(w, ch, px, left, top, right, bottom)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_png(str(output_path), cw, chh, ch, crop)
    print(f"cropped {w}x{h} -> {cw}x{chh} @ ({left},{top},{right},{bottom}) -> {output_path}")


if __name__ == "__main__":
    main()
