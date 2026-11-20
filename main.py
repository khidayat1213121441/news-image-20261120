#!/usr/bin/env python3
"""The World in One Image - Friday 20 November 2026 (late edition).

A pure-stdlib procedural front page: masthead, a big lead story with a
deferral timeline, a by-the-numbers strip, six story panels, a ticker and
a footer, drawn by a small software rasterizer into a 1024x1024 PNG.
No network, no fonts on disk, no copied image: every pixel is computed
here, deterministically, so two runs write identical bytes.

Run:  MAKEFUN_OUTPUT_DIR=. python3 main.py
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
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


# ---------------------------------------------------------------- canvas
class Canvas:
    """An RGB framebuffer with a few filled-shape primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def fill(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, c, t=1):
        self.fill(x, y, w, t, c)
        self.fill(x, y + h - t, w, t, c)
        self.fill(x, y, t, h, c)
        self.fill(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for a in range(-(t // 2), t // 2 + 1):
                for b in range(-(t // 2), t // 2 + 1):
                    self.set(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            if abs(yy - cy) > r:
                continue
            dx = int((r * r - (yy - cy) ** 2) ** 0.5)
            self.fill(cx - dx, yy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            for a in range(0, 360):
                x = cx + int(rr * math.cos(math.radians(a)))
                y = cy + int(rr * math.sin(math.radians(a)))
                self.set(x, y, c)

    def poly(self, pts, c):
        """Scanline fill of a simple polygon."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for yy in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    t = (yy - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.fill(int(xs[k]), yy, int(xs[k + 1]) - int(xs[k]) + 1, 1, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            t = 1.0 - ((yy - cy) / ry) ** 2
            if t < 0:
                continue
            dx = int(rx * (t ** 0.5))
            self.fill(cx - dx, yy, 2 * dx + 1, 1, c)


def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, '#' = on. Hand-drawn for this entry.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "\u2014": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "\u2022": ("00000", "00000", "01100", "01100", "00000", "00000", "00000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, color):
    """Draw uppercase text (lowercase is uppercased) at scale."""
    cx = x
    for ch in s.upper():
        g = FONT.get(ch, FONT[" "])
        for r in range(7):
            row = g[r]
            for c in range(5):
                if row[c] == "1":
                    cv.fill(cx + c * scale, y + r * scale, scale, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(cv, cx, y, s, scale, color):
    draw_text(cv, cx - text_w(s, scale) // 2, y, s, scale, color)


def wrap_text(s, max_chars):
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


def draw_wrapped(cv, x, y, s, scale, color, max_chars, leading=None):
    if leading is None:
        leading = 9 * scale
    yy = y
    for line in wrap_text(s, max_chars):
        draw_text(cv, x, yy, line, scale, color)
        yy += leading
    return yy

# ---------------------------------------------------------------- scenes
def stars(cv, x, y, w, h, seed, n, color=WHITE):
    s = seed
    for _ in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        sx = x + s % w
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        sy = y + s % h
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        r = 1 if s % 5 else 2
        cv.disc(sx, sy, r, color)


def masthead(cv):
    cv.fill(0, 0, W, 92, BLACK)
    cv.fill(0, 88, W, 4, GOLD)
    draw_text(cv, 24, 24, "THE WORLD TODAY", 5, WHITE)
    draw_text(cv, 24, 60, "ONE DAY  •  ONE IMAGE  •  EVERY STORY THAT MATTERED  •  LATE EDITION", 2, GOLD)
    draw_text(cv, W - 24 - text_w("FRIDAY 20 NOVEMBER 2026", 3), 28, "FRIDAY 20 NOVEMBER 2026", 3, WHITE)
    draw_text(cv, W - 24 - text_w("make.fun", 2), 62, "make.fun", 2, LIGHTGREY)

def lead(cv):
    x, y, w, h = 16, 104, W - 32, 252
    cv.fill(x, y, w, h, CREAM)
    cv.rect(x, y, w, h, INK, 2)
    cv.fill(x, y, w, 34, RED)
    draw_text(cv, x + 14, y + 9, "THE LEAD  •  WASHINGTON", 2, WHITE)
    # headline, left column (fixed lines, no wrapping)
    tx = x + 18
    draw_text(cv, tx, y + 52, "TRUMP PUTS IRAN", 5, INK)
    draw_text(cv, tx, y + 100, "WAR DECISION OFF", 5, INK)
    draw_text(cv, tx, y + 148, "TO 2027", 5, INK)
    draw_text(cv, tx, y + 192, "No rush, says the president - he will", 2, INK)
    draw_text(cv, tx, y + 212, "'see what happens' after Jan 1, pushing", 2, INK)
    draw_text(cv, tx, y + 232, "the year's biggest decision into 2027.", 2, INK)
    # visual, right: big 2027, a clock, and a deferral timeline
    vx, vy, vw, vh = 600, 120, 392, 220
    cv.fill(vx, vy, vw, vh, NAVY)
    cv.rect(vx, vy, vw, vh, GOLD, 2)
    draw_text(cv, vx + 22, vy + 16, "2027", 7, GOLD)
    # clock dial, top right
    ccx, ccy = 920, 178
    cv.disc(ccx, ccy, 34, WHITE)
    cv.ring(ccx, ccy, 34, INK, 3)
    for ang, ln in ((90, 24), (0, 18)):
        rad = math.radians(ang - 90)
        cv.line(ccx, ccy, ccx + int(ln * math.cos(rad)), ccy + int(ln * math.sin(rad)), INK, 3)
    cv.disc(ccx, ccy, 4, RED)
    draw_text(cv, vx + 22, vy + 80, "DECISION", 2, WHITE)
    draw_text(cv, vx + 22, vy + 102, "DEFERRED", 2, WHITE)
    # timeline: today -> Jan 1 -> 2027
    ty = vy + 180
    cv.line(vx + 20, ty, vx + 372, ty, GOLD, 3)
    cv.poly([(vx + 360, ty - 8), (vx + 376, ty), (vx + 360, ty + 8)], GOLD)
    for dx, lab, dot in ((20, "NOV 20", GOLD), (176, "JAN 1", GOLD), (350, "2027", RED)):
        cx = vx + dx
        cv.disc(cx, ty, 7 if dot is RED else 6, dot)
        draw_text(cv, cx - text_w(lab, 1) // 2, ty + 12, lab, 1, WHITE)


def numbers_strip(cv):
    y, h = 368, 64
    stats = [
        ("300,000", "EVACUATED IN ODISHA", TEAL),
        ("$1.8BN", "GTA 6 SALES RECORD", PURPLE),
        ("1 LIGHT-DAY", "VOYAGER 1 FROM EARTH", NAVY),
        ("$120BN", "CLIMATE FINANCE PLEDGED", GREEN),
    ]
    bw, gap = 242, 8
    for i, (num, lab, col) in enumerate(stats):
        x = 16 + i * (bw + gap)
        cv.fill(x, y, bw, h, CREAM)
        cv.rect(x, y, bw, h, INK, 1)
        cv.fill(x, y, bw, 4, col)
        draw_text_centered(cv, x + bw // 2, y + 13, num, 3, INK)
        draw_text_centered(cv, x + bw // 2, y + 42, lab, 1, GREY)

def panel_frame(cv, x, y, w, h, strip, kicker):
    cv.fill(x, y, w, h, CREAM)
    cv.rect(x, y, w, h, INK, 2)
    cv.fill(x, y, w, 30, strip)
    draw_text(cv, x + 10, y + 8, kicker, 2, WHITE)


def panel_voyager(cv, x, y, w, h):
    panel_frame(cv, x, y, w, h, NAVY, "SPACE  •  NASA")
    cv.fill(x + 8, y + 38, w - 16, 96, (8, 16, 40))
    stars(cv, x + 8, y + 38, w - 16, 96, 12345, 40)
    # small Earth in the bottom-left corner of the scene
    cv.disc(x + 52, y + 108, 26, (40, 110, 190))
    cv.ellipse(x + 44, y + 102, 8, 5, GREEN)
    cv.ellipse(x + 60, y + 114, 7, 4, GREEN)
    # dashed trajectory, aligned with the probe body
    for i in range(0, 150, 14):
        cv.fill(x + 120 + i, y + 74, 8, 3, GOLD)
    # probe: body + dish + antenna
    cv.fill(x + 236, y + 66, 34, 18, LIGHTGREY)
    cv.poly([(x + 270, y + 64), (x + 292, y + 54), (x + 292, y + 94), (x + 270, y + 86)], GOLD)
    cv.line(x + 222, y + 75, x + 236, y + 75, LIGHTGREY, 2)
    cv.disc(x + 236, y + 75, 3, RED)
    draw_text(cv, x + 18, y + 146, "VOYAGER 1 CROSSES", 2, INK)
    draw_text(cv, x + 18, y + 166, "ONE LIGHT-DAY", 2, INK)
    draw_wrapped(cv, x + 18, y + 190, "NASA confirms the probe is now a full light-day from Earth.", 1, INK, 46)


def panel_gta(cv, x, y, w, h):
    panel_frame(cv, x, y, w, h, PURPLE, "CULTURE  •  GAMES")
    # sunset bands
    cv.fill(x + 8, y + 38, w - 16, 34, ORANGE)
    cv.fill(x + 8, y + 72, w - 16, 32, MAGENTA)
    cv.fill(x + 8, y + 104, w - 16, 30, (46, 12, 70))
    cv.disc(x + 250, y + 66, 16, GOLD)
    # skyline silhouette
    base = y + 134
    for bx, bh in ((8, 34), (40, 58), (78, 44), (116, 70), (160, 52), (200, 64), (244, 40), (280, 56)):
        cv.fill(x + bx, base - bh, 30, bh, BLACK)
    # neon VI
    draw_text(cv, x + 96, y + 46, "VI", 6, MAGENTA)
    draw_text(cv, x + 96, y + 46, "VI", 6, WHITE)
    # two palm silhouettes
    for px in (x + 30, x + 292):
        cv.line(px, base, px + 4, base - 34, BLACK, 3)
        for dx, dy in ((-16, -12), (-6, -18), (8, -18), (18, -10)):
            cv.line(px + 4, base - 34, px + 4 + dx, base - 34 + dy, BLACK, 2)
    draw_text(cv, x + 18, y + 146, "GTA 6 SALES PASS", 2, INK)
    draw_text(cv, x + 18, y + 166, "$1.8 BILLION", 2, INK)
    draw_wrapped(cv, x + 18, y + 190, "Already past The Odyssey's global box-office run.", 1, INK, 46)


def panel_cyclone(cv, x, y, w, h):
    panel_frame(cv, x, y, w, h, TEAL, "WEATHER  •  INDIA")
    cv.fill(x + 8, y + 38, w - 16, 96, (16, 60, 80))
    # spiral
    cx, cy = x + 150, y + 86
    for k in range(0, 540, 6):
        r = 4 + k * 0.09
        a = math.radians(k)
        px = cx + int(r * math.cos(a))
        py = cy + int(r * math.sin(a) * 0.8)
        cv.disc(px, py, 3, WHITE if k % 36 < 18 else SKY)
    cv.disc(cx, cy, 8, TEAL)
    # rain streaks
    for rx in range(x + 20, x + w - 20, 26):
        cv.line(rx, y + 44, rx - 8, y + 64, SKY, 1)
    # coastline
    cv.poly([(x + 8, y + 134), (x + 120, y + 118), (x + 220, y + 134), (x + 312, y + 122),
             (x + 312, y + 134), (x + 8, y + 134)], SAND)
    draw_text(cv, x + 18, y + 146, "CYCLONE AKVAN:", 2, INK)
    draw_text(cv, x + 18, y + 166, "300,000 EVACUATED", 2, INK)
    draw_wrapped(cv, x + 18, y + 190, "Odisha braces as the storm nears India's east coast.", 1, INK, 46)


def panel_kyiv(cv, x, y, w, h):
    panel_frame(cv, x, y, w, h, DARKRED, "WAR  •  UKRAINE")
    cv.fill(x + 8, y + 38, w - 16, 96, (60, 24, 16))
    # dusk bands
    cv.fill(x + 8, y + 38, w - 16, 30, (120, 50, 24))
    cv.fill(x + 8, y + 68, w - 16, 28, (90, 36, 20))
    # skyline
    base = y + 134
    for bx, bh in ((8, 40), (48, 62), (92, 48), (140, 70), (190, 54), (240, 66), (284, 44)):
        cv.fill(x + bx, base - bh, 34, bh, BLACK)
    # smoke puffs above two buildings
    cv.disc(x + 62, y + 62, 10, (150, 150, 148))
    cv.disc(x + 158, y + 56, 12, (150, 150, 148))
    # four missile trails
    for tx0, ty0 in ((40, 44), (110, 40), (180, 46), (250, 42)):
        cv.line(x + tx0, y + ty0, x + tx0 - 26, y + ty0 + 40, GOLD, 2)
        cv.disc(x + tx0, y + ty0, 4, GOLD)
        cv.disc(x + tx0, y + ty0, 2, WHITE)
    draw_text(cv, x + 18, y + 146, "KYIV HIT BY FOUR", 2, INK)
    draw_text(cv, x + 18, y + 166, "BALLISTIC MISSILES", 2, INK)
    draw_wrapped(cv, x + 18, y + 190, "Europe says it is ready for talks with Russia on ending the war.", 1, INK, 46)


def panel_gulf(cv, x, y, w, h):
    panel_frame(cv, x, y, w, h, ORANGE, "ENERGY  •  THE GULF")
    cv.fill(x + 8, y + 38, w - 16, 96, (24, 20, 34))
    stars(cv, x + 8, y + 38, w - 16, 60, 777, 18)
    cv.disc(x + 268, y + 62, 12, LIGHTGREY)
    # tower silhouette with flame
    cv.fill(x + 40, y + 64, 26, 70, BLACK)
    cv.poly([(x + 46, y + 64), (x + 60, y + 48), (x + 66, y + 64)], BLACK)
    cv.disc(x + 60, y + 42, 6, ORANGE)
    cv.disc(x + 60, y + 42, 3, GOLD)
    # tanker on waves, with its own fire
    cv.fill(x + 130, y + 104, 150, 18, (90, 30, 30))
    cv.fill(x + 150, y + 88, 40, 16, (140, 50, 50))
    cv.fill(x + 200, y + 92, 50, 12, (140, 50, 50))
    cv.disc(x + 170, y + 82, 6, ORANGE)
    cv.disc(x + 170, y + 82, 3, GOLD)
    cv.fill(x + 8, y + 126, w - 16, 8, (40, 70, 110))
    draw_text(cv, x + 18, y + 146, "HOUTHI STRIKES HIT", 2, INK)
    draw_text(cv, x + 18, y + 166, "RIYADH AND A TANKER", 2, INK)
    draw_wrapped(cv, x + 18, y + 190, "A Saudi landmark is damaged; a tanker burns after hitting a mine off Hormuz.", 1, INK, 46)


def panel_cop(cv, x, y, w, h):
    panel_frame(cv, x, y, w, h, GREEN, "CLIMATE  •  ANTALYA")
    cv.fill(x + 8, y + 38, w - 16, 96, DARKGREEN)
    # sun rays from the top right
    for rx in range(0, 5):
        cv.line(x + w - 16, y + 38 + rx * 20, x + w - 110, y + 60 + rx * 20, (120, 200, 120), 2)
    # globe
    cv.disc(x + 70, y + 86, 40, (40, 110, 190))
    cv.ellipse(x + 58, y + 76, 14, 9, GREEN)
    cv.ellipse(x + 82, y + 96, 12, 8, GREEN)
    cv.ellipse(x + 66, y + 100, 8, 6, GREEN)
    # leaf
    cv.poly([(x + 190, y + 60), (x + 230, y + 70), (x + 240, y + 104), (x + 200, y + 118), (x + 186, y + 92)], GREEN)
    cv.line(x + 190, y + 60, x + 240, y + 104, DARKGREEN, 2)
    # small Turkish flag, top right
    fx, fy = x + w - 56, y + 44
    cv.fill(fx, fy, 34, 22, RED)
    cv.disc(fx + 13, fy + 11, 7, WHITE)
    cv.disc(fx + 15, fy + 11, 6, RED)
    cv.disc(fx + 24, fy + 11, 2, WHITE)
    draw_text(cv, x + 18, y + 146, "COP31 CLOSES IN", 2, INK)
    draw_text(cv, x + 18, y + 166, "ANTALYA", 2, INK)
    draw_wrapped(cv, x + 18, y + 190, "Draft urges a fossil-fuel exit and $120bn in climate finance.", 1, INK, 46)


def ticker(cv):
    y = 896
    cv.fill(0, y, W, 52, DARKRED)
    draw_text(cv, 16, y + 14, "ALSO TODAY", 2, GOLD)
    msg = ("HAYABUSA2 LANDING OFF  •  GENOA AIRPORT SHUT BY DRONES  •  S. KOREA EXPORTS TOP "
           "$1 TRILLION  •  MIGRANT BOAT SINKS OFF SENEGAL")
    draw_text(cv, 16, y + 32, msg, 1, WHITE)


def footer(cv):
    draw_text_centered(cv, W // 2, 962, "FRIDAY 20 NOVEMBER 2026  •  DRAWN ENTIRELY BY CODE  •  make.fun", 2, GREY)
    cv.fill(0, 1016, W, 8, GOLD)


def build():
    cv = Canvas(W, H, PAPER)
    masthead(cv)
    lead(cv)
    numbers_strip(cv)
    gx, gy = 16, 444
    cw, chh, gap = 325, 216, 8
    panels = [panel_voyager, panel_gta, panel_cyclone, panel_kyiv, panel_gulf, panel_cop]
    for i, fn in enumerate(panels):
        px = gx + (i % 3) * (cw + gap)
        py = gy + (i // 3) * (chh + gap)
        fn(cv, px, py, cw, chh)
    ticker(cv)
    footer(cv)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(build(), path)
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
