#!/usr/bin/env python3
"""The World in One Image - Friday 20 November 2026 (final edition).

A pure-stdlib procedural front page: masthead, a where-it-happened locator
strip, a big lead story with a deferral timeline, a five-stat by-the-numbers
strip, six story panels with enriched scenes, a ticker and a footer, drawn
by a small software rasterizer into a 1024x1024 PNG. No network, no fonts
on disk, no copied image: every pixel is computed here, deterministically,
so two runs write identical bytes.

Run:  MAKEFUN_OUTPUT_DIR=. python3 main.py
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ------------------------------------------------------------------ palette
PAPER = (247, 242, 231)
CREAM = (250, 246, 236)
INK = (20, 20, 20)
BLACK = (12, 12, 14)
WHITE = (255, 255, 255)
RED = (192, 57, 43)
DARKRED = (140, 30, 22)
GOLD = (212, 160, 23)
NAVY = (20, 38, 74)
TEAL = (14, 124, 123)
SKY = (135, 190, 220)
ORANGE = (230, 126, 34)
GREEN = (39, 174, 96)
DARKGREEN = (20, 60, 44)
PURPLE = (108, 52, 131)
MAGENTA = (194, 52, 130)
GREY = (120, 120, 118)
LIGHTGREY = (220, 216, 205)
SAND = (210, 180, 140)
NIGHT = (8, 16, 40)
DUSK = (60, 24, 16)


# ------------------------------------------------------------------ sheet
class Sheet:
    """An RGB framebuffer with filled-shape primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def box(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def frame(self, x, y, w, h, c, t=1):
        self.box(x, y, w, t, c)
        self.box(x, y + h - t, w, t, c)
        self.box(x, y, t, h, c)
        self.box(x + w - t, y, t, h, c)

    def seg(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = t // 2
        while True:
            for a in range(-half, half + 1):
                for b in range(-half, half + 1):
                    self.put(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def spot(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            if abs(yy - cy) > r:
                continue
            dx = int((r * r - (yy - cy) ** 2) ** 0.5)
            self.box(cx - dx, yy, 2 * dx + 1, 1, c)

    def loop(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            for a in range(360):
                rad = math.radians(a)
                self.put(cx + int(rr * math.cos(rad)),
                         cy + int(rr * math.sin(rad)), c)

    def shape(self, pts, c):
        """Scanline fill of a simple polygon."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        n = len(pts)
        for yy in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    f = (yy - y0) / (y1 - y0)
                    xs.append(x0 + f * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.box(int(xs[k]), yy, int(xs[k + 1]) - int(xs[k]) + 1, 1, c)

    def oval(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            t = 1.0 - ((yy - cy) / ry) ** 2
            if t < 0:
                continue
            dx = int(rx * (t ** 0.5))
            self.box(cx - dx, yy, 2 * dx + 1, 1, c)


def save_png(sh, path):
    raw = bytearray()
    stride = sh.w * 3
    for y in range(sh.h):
        raw.append(0)
        raw += sh.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def block(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", sh.w, sh.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += block(b"IHDR", ihdr)
    png += block(b"IDAT", comp)
    png += block(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ------------------------------------------------------------------ 5x7 font
# One glyph per line: 7 rows of 5 bits joined by "/", "#" replaced by "1".
# Hand-drawn for this entry; uppercase only (input is uppercased).
GLYPHS = {
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01110/10001/10000/10000/10000/10001/01110",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01110/10001/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "01110/00100/00100/00100/00100/00100/01110",
    "J": "00111/00010/00010/00010/00010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10101/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10101/10101/11011/10001",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    "0": "01110/10001/10011/10101/11001/10001/01110",
    "1": "00100/01100/00100/00100/00100/00100/01110",
    "2": "01110/10001/00001/00110/01000/10000/11111",
    "3": "11111/00010/00100/00010/00001/10001/01110",
    "4": "00010/00110/01010/10010/11111/00010/00010",
    "5": "11111/10000/11110/00001/00001/10001/01110",
    "6": "00110/01000/10000/11110/10001/10001/01110",
    "7": "11111/00001/00010/00100/01000/01000/01000",
    "8": "01110/10001/10001/01110/10001/10001/01110",
    "9": "01110/10001/10001/01111/00001/00010/01100",
    ".": "00000/00000/00000/00000/00000/01100/01100",
    ",": "00000/00000/00000/00000/01100/00100/01000",
    ":": "00000/01100/01100/00000/01100/01100/00000",
    ";": "00000/01100/01100/00000/01100/00100/01000",
    "!": "00100/00100/00100/00100/00100/00000/00100",
    "?": "01110/10001/00001/00110/00100/00000/00100",
    "'": "00100/00100/01000/00000/00000/00000/00000",
    '"': "01010/01010/00000/00000/00000/00000/00000",
    "-": "00000/00000/00000/01110/00000/00000/00000",
    "\u2014": "00000/00000/00000/11111/00000/00000/00000",
    "/": "00001/00010/00010/00100/01000/01000/10000",
    "(": "00010/00100/01000/01000/01000/00100/00010",
    ")": "01000/00100/00010/00010/00010/00100/01000",
    "%": "11001/11010/00010/00100/01000/01011/10011",
    "$": "00100/01111/10100/01110/00101/11110/00100",
    "&": "01100/10010/10100/01000/10101/10010/01101",
    "+": "00000/00100/00100/11111/00100/00100/00000",
    "=": "00000/00000/11111/00000/11111/00000/00000",
    "*": "00000/10101/01110/10101/00000/00000/00000",
    "\u2022": "00000/00000/01100/01100/00000/00000/00000",
    " ": "00000/00000/00000/00000/00000/00000/00000",
}


def measure(s, k):
    return len(s) * 6 * k - k


def write(sh, x, y, s, k, color):
    """Draw text at scale k; input is uppercased, unknown chars are blank."""
    cx = x
    for ch in s.upper():
        rows = GLYPHS.get(ch, GLYPHS[" "]).split("/")
        for r in range(7):
            row = rows[r]
            for c in range(5):
                if row[c] == "1":
                    sh.box(cx + c * k, y + r * k, k, k, color)
        cx += 6 * k
    return cx


def write_mid(sh, cx, y, s, k, color):
    write(sh, cx - measure(s, k) // 2, y, s, k, color)


def split_words(s, max_chars):
    words = s.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(sh, x, y, s, k, color, max_chars, leading=None):
    if leading is None:
        leading = 9 * k
    yy = y
    for line in split_words(s, max_chars):
        write(sh, x, yy, line, k, color)
        yy += leading
    return yy


# ------------------------------------------------------------------ scenes
def starfield(sh, x, y, w, h, seed, n, color=WHITE):
    s = seed
    for _ in range(n):
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        sx = x + s % w
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        sy = y + s % h
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        r = 1 if s % 5 else 2
        sh.spot(sx, sy, r, color)


def masthead(sh):
    sh.box(0, 0, W, 92, BLACK)
    sh.box(0, 88, W, 4, GOLD)
    write(sh, 24, 24, "THE WORLD TODAY", 5, WHITE)
    write(sh, 24, 60, "ONE DAY  •  ONE IMAGE  •  EVERY STORY THAT MATTERED  •  FINAL EDITION", 2, GOLD)
    write(sh, W - 24 - measure("FRIDAY 20 NOVEMBER 2026", 3), 28, "FRIDAY 20 NOVEMBER 2026", 3, WHITE)
    write(sh, W - 24 - measure("make.fun", 2), 62, "make.fun", 2, LIGHTGREY)


def locator(sh):
    y = 96
    sh.box(0, y, W, 32, CREAM)
    sh.box(0, 94, W, 2, INK)
    sh.box(0, 126, W, 2, INK)
    write(sh, 16, y + 10, "WHERE IT HAPPENED", 1, GREY)
    places = [
        (170, "WASHINGTON", RED),
        (310, "SPACE", NAVY),
        (450, "ODISHA", TEAL),
        (590, "KYIV", DARKRED),
        (730, "RIYADH", ORANGE),
        (870, "ANTALYA", GREEN),
    ]
    for lx, lab, col in places:
        sh.spot(lx, y + 16, 5, col)
        write(sh, lx + 10, y + 10, lab, 1, INK)


def lead(sh):
    x, y, w, h = 16, 136, W - 32, 236
    sh.box(x, y, w, h, CREAM)
    sh.frame(x, y, w, h, INK, 2)
    sh.box(x, y, w, 34, RED)
    write(sh, x + 14, y + 9, "THE LEAD  •  WASHINGTON", 2, WHITE)
    tx = x + 18
    write(sh, tx, y + 48, "TRUMP PUTS IRAN", 5, INK)
    write(sh, tx, y + 94, "WAR DECISION OFF", 5, INK)
    write(sh, tx, y + 140, "TO 2027", 5, INK)
    write(sh, tx, y + 178, "No rush, says the president - he will", 2, INK)
    write(sh, tx, y + 196, "'see what happens' after Jan 1, pushing", 2, INK)
    write(sh, tx, y + 214, "the year's biggest decision into 2027.", 2, INK)
    # visual, right: big 2027, a clock, a countdown, a deferral timeline
    vx, vy, vw, vh = 600, 152, 392, 204
    sh.box(vx, vy, vw, vh, NAVY)
    sh.frame(vx, vy, vw, vh, GOLD, 2)
    write(sh, vx + 22, vy + 14, "2027", 7, GOLD)
    ccx, ccy = 916, 196
    sh.spot(ccx, ccy, 30, WHITE)
    sh.loop(ccx, ccy, 30, INK, 3)
    for ang, ln in ((90, 20), (0, 15)):
        rad = math.radians(ang - 90)
        sh.seg(ccx, ccy, ccx + int(ln * math.cos(rad)), ccy + int(ln * math.sin(rad)), INK, 3)
    sh.spot(ccx, ccy, 4, RED)
    write(sh, vx + 22, vy + 78, "DECISION", 2, WHITE)
    write(sh, vx + 22, vy + 100, "DEFERRED", 2, WHITE)
    write(sh, vx + 22, vy + 122, "42 DAYS TO JAN 1", 1, GOLD)
    ty = vy + 168
    sh.seg(vx + 20, ty, vx + 372, ty, GOLD, 3)
    sh.shape([(vx + 360, ty - 8), (vx + 376, ty), (vx + 360, ty + 8)], GOLD)
    for dx, lab, dot in ((20, "NOV 20", GOLD), (176, "JAN 1", GOLD), (350, "2027", RED)):
        cx = vx + dx
        sh.spot(cx, ty, 7 if dot is RED else 6, dot)
        write(sh, cx - measure(lab, 1) // 2, ty + 12, lab, 1, WHITE)


def fit_scale(num, bw):
    """Largest of scale 3 / 2 that fits the number inside the cell."""
    return 3 if measure(num, 3) <= bw - 8 else 2


def numbers_strip(sh):
    y, h = 380, 60
    stats = [
        ("300,000", "EVACUATED IN ODISHA", TEAL),
        ("$1.8BN", "GTA 6 SALES RECORD", PURPLE),
        ("1 LIGHT-DAY", "VOYAGER 1 FROM EARTH", NAVY),
        ("$120BN", "CLIMATE FINANCE PLEDGED", GREEN),
        ("$1TN", "S. KOREA EXPORTS", ORANGE),
    ]
    bw, gap = 192, 8
    for i, (num, lab, col) in enumerate(stats):
        x = 16 + i * (bw + gap)
        sh.box(x, y, bw, h, CREAM)
        sh.frame(x, y, bw, h, INK, 1)
        sh.box(x, y, bw, 4, col)
        k = fit_scale(num, bw)
        write_mid(sh, x + bw // 2, y + 13, num, k, INK)
        write_mid(sh, x + bw // 2, y + 40, lab, 1, GREY)


def panel_frame(sh, x, y, w, h, strip, kicker):
    sh.box(x, y, w, h, CREAM)
    sh.frame(x, y, w, h, INK, 2)
    sh.box(x, y, w, 30, strip)
    write(sh, x + 10, y + 8, kicker, 2, WHITE)


def panel_voyager(sh, x, y, w, h):
    panel_frame(sh, x, y, w, h, NAVY, "SPACE  •  NASA")
    sh.box(x + 8, y + 38, w - 16, 96, NIGHT)
    starfield(sh, x + 8, y + 38, w - 16, 96, 12345, 40)
    # small sun, top left, with rays
    sh.spot(x + 30, y + 58, 8, GOLD)
    for dx, dy in ((-12, -8), (12, -8), (-12, 8), (12, 8)):
        sh.seg(x + 30, y + 58, x + 30 + dx, y + 58 + dy, GOLD, 1)
    # Earth, bottom left, with green patches
    sh.spot(x + 52, y + 108, 26, (40, 110, 190))
    sh.oval(x + 44, y + 102, 8, 5, GREEN)
    sh.oval(x + 60, y + 114, 7, 4, GREEN)
    sh.oval(x + 56, y + 92, 5, 3, GREEN)
    # dashed trajectory to the probe
    for i in range(0, 150, 14):
        sh.box(x + 120 + i, y + 74, 8, 3, GOLD)
    # probe: body + dish + antenna, plus a small comet top right
    sh.box(x + 236, y + 66, 34, 18, LIGHTGREY)
    sh.shape([(x + 270, y + 64), (x + 292, y + 54), (x + 292, y + 94), (x + 270, y + 86)], GOLD)
    sh.seg(x + 222, y + 75, x + 236, y + 75, LIGHTGREY, 2)
    sh.spot(x + 236, y + 75, 3, RED)
    sh.spot(x + 296, y + 50, 3, WHITE)
    sh.seg(x + 296, y + 50, x + 282, y + 58, WHITE, 1)
    sh.seg(x + 296, y + 50, x + 284, y + 44, WHITE, 1)
    write(sh, x + 18, y + 146, "VOYAGER 1 CROSSES", 2, INK)
    write(sh, x + 18, y + 166, "ONE LIGHT-DAY", 2, INK)
    para(sh, x + 18, y + 190, "NASA confirms the probe is now a full light-day from Earth.", 1, INK, 46)


def panel_gta(sh, x, y, w, h):
    panel_frame(sh, x, y, w, h, PURPLE, "CULTURE  •  GAMES")
    # sunset bands + sun + beach strip at the bottom of the scene
    sh.box(x + 8, y + 38, w - 16, 34, ORANGE)
    sh.box(x + 8, y + 72, w - 16, 32, MAGENTA)
    sh.box(x + 8, y + 104, w - 16, 22, (46, 12, 70))
    sh.box(x + 8, y + 126, w - 16, 8, SAND)
    sh.spot(x + 250, y + 66, 16, GOLD)
    # skyline silhouette with lit windows
    base = y + 126
    for bx, bh in ((8, 34), (40, 58), (78, 44), (116, 70), (160, 52), (200, 64), (244, 40), (280, 56)):
        sh.box(x + bx, base - bh, 30, bh, BLACK)
    for wx, wy in ((48, y + 96), (124, y + 84), (168, y + 100), (208, y + 88), (252, y + 104), (288, y + 92)):
        sh.box(wx, wy, 3, 3, GOLD)
        sh.box(wx + 8, wy + 6, 3, 3, GOLD)
    # neon VI with a magenta drop shadow
    write(sh, x + 94, y + 44, "VI", 6, MAGENTA)
    write(sh, x + 96, y + 46, "VI", 6, WHITE)
    # two palm silhouettes
    for px in (x + 30, x + 292):
        sh.seg(px, base, px + 4, base - 34, BLACK, 3)
        for dx, dy in ((-16, -12), (-6, -18), (8, -18), (18, -10)):
            sh.seg(px + 4, base - 34, px + 4 + dx, base - 34 + dy, BLACK, 2)
    write(sh, x + 18, y + 146, "GTA 6 SALES PASS", 2, INK)
    write(sh, x + 18, y + 166, "$1.8 BILLION", 2, INK)
    para(sh, x + 18, y + 190, "Already past The Odyssey's global box-office run.", 1, INK, 46)


def panel_cyclone(sh, x, y, w, h):
    panel_frame(sh, x, y, w, h, TEAL, "WEATHER  •  INDIA")
    sh.box(x + 8, y + 38, w - 16, 96, (16, 60, 80))
    # outer band, then the main spiral
    cx, cy = x + 150, y + 86
    for k in range(0, 720, 12):
        r = 10 + k * 0.075
        a = math.radians(k + 40)
        px = cx + int(r * math.cos(a))
        py = cy + int(r * math.sin(a) * 0.8)
        sh.spot(px, py, 2, SKY)
    for k in range(0, 540, 6):
        r = 4 + k * 0.09
        a = math.radians(k)
        px = cx + int(r * math.cos(a))
        py = cy + int(r * math.sin(a) * 0.8)
        sh.spot(px, py, 3, WHITE if k % 36 < 18 else SKY)
    sh.spot(cx, cy, 8, TEAL)
    # rain streaks
    for rx in range(x + 20, x + w - 20, 26):
        sh.seg(rx, y + 44, rx - 8, y + 64, SKY, 1)
    # coastline + waves
    sh.shape([(x + 8, y + 134), (x + 120, y + 118), (x + 220, y + 134), (x + 312, y + 122),
              (x + 312, y + 134), (x + 8, y + 134)], SAND)
    for wx in range(x + 20, x + w - 20, 34):
        sh.seg(wx, y + 126, wx + 12, y + 124, WHITE, 1)
    write(sh, x + 18, y + 146, "CYCLONE AKVAN:", 2, INK)
    write(sh, x + 18, y + 166, "300,000 EVACUATED", 2, INK)
    para(sh, x + 18, y + 190, "Odisha braces as the storm nears India's east coast.", 1, INK, 46)


def panel_kyiv(sh, x, y, w, h):
    panel_frame(sh, x, y, w, h, DARKRED, "WAR  •  UKRAINE")
    sh.box(x + 8, y + 38, w - 16, 96, DUSK)
    sh.box(x + 8, y + 38, w - 16, 30, (120, 50, 24))
    sh.box(x + 8, y + 68, w - 16, 28, (90, 36, 20))
    # moon, top right
    sh.spot(x + 280, y + 56, 11, LIGHTGREY)
    sh.spot(x + 276, y + 53, 3, GREY)
    # skyline
    base = y + 134
    for bx, bh in ((8, 40), (48, 62), (92, 48), (140, 70), (190, 54), (240, 66), (284, 44)):
        sh.box(x + bx, base - bh, 34, bh, BLACK)
    # fire glows at two building bases
    for fx, fy in ((x + 62, y + 128), (x + 206, y + 128)):
        sh.spot(fx, fy, 8, ORANGE)
        sh.spot(fx, fy, 4, GOLD)
    # smoke puffs above three buildings
    sh.spot(x + 62, y + 62, 10, (150, 150, 148))
    sh.spot(x + 158, y + 56, 12, (150, 150, 148))
    sh.spot(x + 256, y + 64, 9, (150, 150, 148))
    # four missile trails
    for tx0, ty0 in ((40, 44), (110, 40), (180, 46), (250, 42)):
        sh.seg(x + tx0, y + ty0, x + tx0 - 26, y + ty0 + 40, GOLD, 2)
        sh.spot(x + tx0, y + ty0, 4, GOLD)
        sh.spot(x + tx0, y + ty0, 2, WHITE)
    write(sh, x + 18, y + 146, "KYIV HIT BY FOUR", 2, INK)
    write(sh, x + 18, y + 166, "BALLISTIC MISSILES", 2, INK)
    para(sh, x + 18, y + 190, "Europe says it is ready for talks with Russia on ending the war.", 1, INK, 46)


def panel_gulf(sh, x, y, w, h):
    panel_frame(sh, x, y, w, h, ORANGE, "ENERGY  •  THE GULF")
    sh.box(x + 8, y + 38, w - 16, 96, (24, 20, 34))
    starfield(sh, x + 8, y + 38, w - 16, 60, 777, 18)
    sh.spot(x + 268, y + 62, 12, LIGHTGREY)
    # flare stack at the right, tower at the left
    sh.box(x + 288, y + 70, 6, 64, BLACK)
    sh.spot(x + 291, y + 66, 5, ORANGE)
    sh.spot(x + 291, y + 66, 2, GOLD)
    sh.box(x + 40, y + 64, 26, 70, BLACK)
    sh.shape([(x + 46, y + 64), (x + 60, y + 48), (x + 66, y + 64)], BLACK)
    sh.spot(x + 60, y + 42, 6, ORANGE)
    sh.spot(x + 60, y + 42, 3, GOLD)
    # tanker on waves, with its own fire; a small dhow at the left
    sh.box(x + 130, y + 104, 150, 18, (90, 30, 30))
    sh.box(x + 150, y + 88, 40, 16, (140, 50, 50))
    sh.box(x + 200, y + 92, 50, 12, (140, 50, 50))
    sh.spot(x + 170, y + 82, 6, ORANGE)
    sh.spot(x + 170, y + 82, 3, GOLD)
    sh.box(x + 84, y + 112, 30, 8, (60, 40, 40))
    sh.seg(x + 99, y + 112, x + 99, y + 96, (60, 40, 40), 2)
    sh.box(x + 8, y + 126, w - 16, 8, (40, 70, 110))
    for wx in range(x + 16, x + w - 24, 30):
        sh.seg(wx, y + 129, wx + 10, y + 129, WHITE, 1)
    write(sh, x + 18, y + 146, "HOUTHI STRIKES HIT", 2, INK)
    write(sh, x + 18, y + 166, "RIYADH AND A TANKER", 2, INK)
    para(sh, x + 18, y + 190, "A Saudi landmark is damaged; a tanker burns after hitting a mine off Hormuz.", 1, INK, 46)


def panel_cop(sh, x, y, w, h):
    panel_frame(sh, x, y, w, h, GREEN, "CLIMATE  •  ANTALYA")
    sh.box(x + 8, y + 38, w - 16, 96, DARKGREEN)
    # sun rays from the top right
    for rx in range(0, 5):
        sh.seg(x + w - 16, y + 38 + rx * 20, x + w - 110, y + 60 + rx * 20, (120, 200, 120), 2)
    # globe
    sh.spot(x + 70, y + 86, 40, (40, 110, 190))
    sh.oval(x + 58, y + 76, 14, 9, GREEN)
    sh.oval(x + 82, y + 96, 12, 8, GREEN)
    sh.oval(x + 66, y + 100, 8, 6, GREEN)
    # solar panel rows, bottom left of the scene
    for px, py in ((x + 130, y + 112), (x + 172, y + 112)):
        sh.box(px, py, 38, 18, (20, 40, 90))
        sh.seg(px + 12, py, px + 12, py + 18, (120, 160, 220), 1)
        sh.seg(px + 25, py, px + 25, py + 18, (120, 160, 220), 1)
        sh.seg(px, py + 9, px + 38, py + 9, (120, 160, 220), 1)
    # leaf
    sh.shape([(x + 190, y + 60), (x + 230, y + 70), (x + 240, y + 104), (x + 200, y + 118), (x + 186, y + 92)], GREEN)
    sh.seg(x + 190, y + 60, x + 240, y + 104, DARKGREEN, 2)
    # wind turbine, right edge
    sh.seg(x + 292, y + 130, x + 292, y + 84, LIGHTGREY, 2)
    for ang in (90, 210, 330):
        rad = math.radians(ang - 90)
        sh.seg(x + 292, y + 84, x + 292 + int(16 * math.cos(rad)), y + 84 + int(16 * math.sin(rad)), LIGHTGREY, 2)
    # small Turkish flag, top right
    fx, fy = x + w - 56, y + 44
    sh.box(fx, fy, 34, 22, RED)
    sh.spot(fx + 13, fy + 11, 7, WHITE)
    sh.spot(fx + 15, fy + 11, 6, RED)
    sh.spot(fx + 24, fy + 11, 2, WHITE)
    write(sh, x + 18, y + 146, "COP31 CLOSES IN", 2, INK)
    write(sh, x + 18, y + 166, "ANTALYA", 2, INK)
    para(sh, x + 18, y + 190, "Draft urges a fossil-fuel exit and $120bn in climate finance.", 1, INK, 46)


def ticker(sh):
    y = 896
    sh.box(0, y, W, 52, DARKRED)
    write(sh, 16, y + 14, "ALSO TODAY", 2, GOLD)
    msg = ("HAYABUSA2 LANDING OFF  •  GENOA AIRPORT SHUT BY DRONES  •  S. KOREA EXPORTS TOP "
           "$1 TRILLION  •  MIGRANT BOAT SINKS OFF SENEGAL")
    write(sh, 16, y + 32, msg, 1, WHITE)


def footer(sh):
    write_mid(sh, W // 2, 962, "FRIDAY 20 NOVEMBER 2026  •  DRAWN ENTIRELY BY CODE  •  make.fun", 2, GREY)
    sh.box(0, 1016, W, 8, GOLD)


def compose():
    sh = Sheet(W, H, PAPER)
    masthead(sh)
    locator(sh)
    lead(sh)
    numbers_strip(sh)
    gx, gy = 16, 448
    cw, chh, gap = 325, 216, 8
    panels = [panel_voyager, panel_gta, panel_cyclone, panel_kyiv, panel_gulf, panel_cop]
    for i, fn in enumerate(panels):
        px = gx + (i % 3) * (cw + gap)
        py = gy + (i // 3) * (chh + gap)
        fn(sh, px, py, cw, chh)
    ticker(sh)
    footer(sh)
    return sh


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = save_png(compose(), path)
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
