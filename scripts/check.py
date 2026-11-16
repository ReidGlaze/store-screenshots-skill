#!/usr/bin/env python3
"""Check screenshot files against App Store / Google Play requirements before upload.

  check.py appstore-iphone-6.9 <dir-or-file> [...]
  check.py appstore-iphone-6.3 <dir-or-file> [...]
  check.py appstore-ipad-13    <dir-or-file> [...]
  check.py play-phone          <dir-or-file> [...]
  check.py play-tablet         <dir-or-file> [...]
  check.py play-feature        <file>

Checks pixel size, format, alpha channel, file size and file count.
Exits 1 if anything fails. Uses only the Python standard library.
"""
import os
import struct
import sys

MB = 1024 * 1024
EXACT = {
    # name: (allowed (w, h) list, min count, max count)
    "appstore-iphone-6.9": ([(1320, 2868), (2868, 1320), (1290, 2796), (2796, 1290), (1260, 2736), (2736, 1260)], 1, 10),
    "appstore-iphone-6.3": ([(1206, 2622), (2622, 1206), (1179, 2556), (2556, 1179)], 1, 10),
    "appstore-ipad-13": ([(2064, 2752), (2752, 2064), (2048, 2732), (2732, 2048)], 1, 10),
    "play-feature": ([(1024, 500)], 1, 1),
}
RANGE = {
    # name: (min side, max side, min count, max count, max bytes)
    "play-phone": (320, 3840, 2, 8, 8 * MB),
    "play-tablet": (320, 3840, 1, 8, 8 * MB),
}


def read_image(path):
    """Return (format, width, height, has_alpha)."""
    with open(path, "rb") as f:
        head = f.read(32)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h, _depth, color = struct.unpack(">IIBB", head[16:26])
            alpha = color in (4, 6)
            if not alpha:  # palette or RGB can still carry a tRNS chunk
                f.seek(8)
                while True:
                    chunk = f.read(8)
                    if len(chunk) < 8:
                        break
                    length, kind = struct.unpack(">I4s", chunk)
                    if kind == b"tRNS":
                        alpha = True
                        break
                    if kind == b"IDAT":
                        break
                    f.seek(length + 4, 1)
            return "PNG", w, h, alpha
        if head[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                marker = f.read(4)
                if len(marker) < 4:
                    break
                tag, length = struct.unpack(">HH", marker)
                if 0xFFC0 <= tag <= 0xFFCF and tag not in (0xFFC4, 0xFFC8, 0xFFCC):
                    _p, h, w = struct.unpack(">BHH", f.read(5))
                    return "JPEG", w, h, False
                f.seek(length - 2, 1)
    return None, 0, 0, False


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in list(EXACT) + list(RANGE):
        print(__doc__)
        return 1
    kind = sys.argv[1]
    files = []
    for p in sys.argv[2:]:
        if os.path.isdir(p):
            files += sorted(
                os.path.join(p, n) for n in os.listdir(p)
                if n.lower().endswith((".png", ".jpg", ".jpeg")) and not n.startswith(".")
            )
        else:
            files.append(p)
    bad = 0
    for path in files:
        fmt, w, h, alpha = read_image(path)
        size = os.path.getsize(path)
        problems = []
        if fmt is None:
            problems.append("not a PNG or JPEG")
        else:
            if kind in EXACT:
                if (w, h) not in EXACT[kind][0]:
                    allowed = ", ".join("%dx%d" % s for s in EXACT[kind][0])
                    problems.append("size not allowed (allowed: %s)" % allowed)
                if kind == "play-feature" and size > 15 * MB:
                    problems.append("over 15 MB")
            else:
                lo, hi, _, _, max_bytes = RANGE[kind]
                if min(w, h) < lo or max(w, h) > hi:
                    problems.append("each side must be %d-%d px" % (lo, hi))
                if max(w, h) > 2 * min(w, h):
                    problems.append("long side is more than twice the short side")
                if size > max_bytes:
                    problems.append("over %d MB" % (max_bytes // MB))
            if alpha:
                problems.append("has an alpha channel (flatten it)")
        status = "FAIL" if problems else "ok"
        bad += bool(problems)
        print("%-4s %s  %s %dx%d %.1f MB%s" % (
            status, os.path.basename(path), fmt or "?", w, h, size / MB,
            "  <- " + "; ".join(problems) if problems else ""))
    lo_n, hi_n = (EXACT[kind][1], EXACT[kind][2]) if kind in EXACT else (RANGE[kind][2], RANGE[kind][3])
    if not lo_n <= len(files) <= hi_n:
        print("FAIL %d file(s); %s needs %d to %d" % (len(files), kind, lo_n, hi_n))
        bad += 1
    print("%s: %d file(s), %s" % (kind, len(files), "all pass" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
