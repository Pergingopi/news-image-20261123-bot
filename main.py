#!/usr/bin/env python3
"""The World Today - one image summing up the world news of Monday 23 November 2026.

Pure Python 3.13 standard library: the poster is drawn pixel by pixel into an
RGB buffer and encoded as a PNG by hand (zlib + struct). No network, no fonts
on disk - the lettering comes from a small built-in 5x7 bitmap font. The run is
fully deterministic: the same code always writes the same bytes.

Stories (all verified against news reports of 23 November 2026):
  1. COP31 climate talks collapse in Antalya - EU rejects the deal as too weak,
     UN chief Guterres "deeply disappointed".
  2. The Gulf war spreads - Iran hits a civilian facility in Bahrain, Houthis
     strike Riyadh for a third straight day.
  3. Democrats win 258 US House seats - the biggest majority since 1992.
  4. A Russian drone hits a building in the Kyiv region - 14 people missing.
  5. UN talks on lethal AI weapons end with no binding rules; work runs to 2028.
  6. South Korea's education minister quits over an AI exam-cheating scandal.

Usage: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import struct
import zlib
from math import cos, sin, sqrt

W = H = 1024

# ---------------------------------------------------------------- font (5x7)
# Each glyph is 7 rows; each row is a 5-bit mask, bit 4 is the leftmost pixel.
FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 6, 8, 16, 31),
    "3": (30, 1, 1, 14, 1, 1, 30),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 12, 4, 8),
    "'": (4, 4, 8, 0, 0, 0, 0),
    "!": (4, 4, 4, 4, 4, 0, 4),
    "?": (14, 17, 1, 6, 4, 0, 4),
    "-": (0, 0, 0, 14, 0, 0, 0),
    "/": (1, 2, 2, 4, 8, 8, 16),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "&": (12, 18, 20, 8, 21, 18, 13),
    "%": (25, 26, 2, 4, 8, 11, 19),
    "+": (0, 4, 4, 14, 4, 4, 0),
    "=": (0, 0, 14, 0, 14, 0, 0),
    '"': (10, 10, 0, 0, 0, 0, 0),
    "*": (0, 21, 14, 31, 14, 21, 0),
    ";": (0, 12, 0, 12, 12, 4, 8),
    "_": (0, 0, 0, 0, 0, 0, 31),
    ":": (0, 12, 0, 12, 0, 12, 12),
}

# ---------------------------------------------------------------- palette
NAVY = (15, 42, 67)
DARK = (11, 27, 46)
GOLD = (242, 183, 5)
WHITE = (255, 255, 255)
CREAM = (232, 237, 243)
GREEN = (20, 83, 45)
GREEN_SUB = (209, 250, 229)
SLATE = (31, 42, 68)
BLUE = (20, 55, 90)
STEEL = (46, 52, 64)
PURPLE = (45, 42, 74)
VIOLET = (76, 29, 149)
ORANGE = (245, 158, 11)
RED = (228, 87, 46)
SKY = (56, 189, 248)
OCEAN = (46, 111, 183)
LAND = (63, 163, 77)


class Canvas:
    def __init__(self):
        self.px = bytearray(W * H * 3)
        self.rect(0, 0, W, H, DARK)

    def _set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(W, x1)
        y1 = min(H, y1)
        for y in range(y0, y1):
            base = (y * W + x0) * 3
            for x in range(x0, x1):
                i = base + (x - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int(sqrt(r * r - dy * dy))
            self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, c)

    def ring(self, cx, cy, r, w, c):
        for dy in range(-r, r + 1):
            dx = int(sqrt(r * r - dy * dy))
            dx2 = int(sqrt(max(0, (r - w) * (r - w) - dy * dy)) if abs(dy) < r - w else 0)
            if abs(dy) < r - w:
                self.rect(cx - dx, cy + dy, cx - dx2, cy + dy + 1, c)
                self.rect(cx + dx2, cy + dy, cx + dx + 1, cy + dy + 1, c)
            else:
                self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, c)

    def line(self, x0, y0, x1, y1, c, w=1):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        half = w // 2
        for s in range(steps + 1):
            x = x0 + dx * s // steps
            y = y0 + dy * s // steps
            self.rect(x - half, y - half, x + half + 1, y + half + 1, c)

    def poly(self, pts, c):
        # Even-odd scanline fill.
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.rect(xs[j], y, xs[j + 1] + 1, y + 1, c)

    def text_w(self, s, scale):
        return len(s) * 6 * scale - scale

    def text(self, x, y, s, scale, c):
        s = s.upper()
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.rect(cx + col * scale, y + row * scale,
                                  cx + (col + 1) * scale, y + (row + 1) * scale, c)
            cx += 6 * scale
        return cx

    def centre_text(self, y, s, scale, c, x0=0, x1=W):
        w = self.text_w(s, scale)
        self.text(x0 + (x1 - x0 - w) // 2, y, s, scale, c)


# ---------------------------------------------------------------- icons
def icon_tanker(cv, ix, iy):
    # Oil tanker on waves, flame above the funnel.
    cv.line(ix + 2, iy + 40, ix + 10, iy + 36, SKY, 2)
    cv.line(ix + 10, iy + 36, ix + 18, iy + 40, SKY, 2)
    cv.line(ix + 18, iy + 40, ix + 26, iy + 36, SKY, 2)
    cv.line(ix + 26, iy + 36, ix + 34, iy + 40, SKY, 2)
    cv.line(ix + 34, iy + 40, ix + 42, iy + 36, SKY, 2)
    cv.poly([(ix + 2, iy + 22), (ix + 42, iy + 22), (ix + 38, iy + 34), (ix + 6, iy + 34)],
            (203, 213, 225))
    cv.rect(ix + 30, iy + 12, ix + 38, iy + 22, (148, 163, 184))
    cv.rect(ix + 10, iy + 14, ix + 16, iy + 22, RED)
    cv.poly([(ix + 13, iy + 2), (ix + 16, iy + 8), (ix + 19, iy + 4),
             (ix + 17, iy + 12), (ix + 11, iy + 12), (ix + 9, iy + 6)], ORANGE)


def icon_dome(cv, ix, iy):
    # US Capitol dome.
    cv.circle(ix + 22, iy + 22, 12, (229, 231, 235))
    cv.rect(ix + 10, iy + 22, ix + 34, iy + 34, (229, 231, 235))
    cv.rect(ix + 6, iy + 32, ix + 38, iy + 40, (229, 231, 235))
    cv.rect(ix + 4, iy + 40, ix + 40, iy + 43, GOLD)
    cv.line(ix + 22, iy + 4, ix + 22, iy + 10, GOLD, 2)
    cv.rect(ix + 22, iy + 4, ix + 29, iy + 8, RED)
    cv.rect(ix + 10, iy + 22, ix + 34, iy + 23, NAVY)
    for cx in (12, 19, 26, 33):
        cv.rect(ix + cx, iy + 24, ix + cx + 2, iy + 32, NAVY)


def icon_building(cv, ix, iy):
    # Block hit by a drone, smoke rising.
    cv.circle(ix + 16, iy + 10, 5, (209, 213, 219))
    cv.circle(ix + 22, iy + 6, 4, (209, 213, 219))
    cv.rect(ix + 8, iy + 16, ix + 26, iy + 42, (156, 163, 175))
    for wy in (20, 27, 34):
        for wx in (11, 18):
            cv.rect(ix + wx, iy + wy, ix + wx + 4, iy + wy + 4, (31, 41, 55))
    cv.rect(ix + 31, iy + 8, ix + 39, iy + 12, ORANGE)
    cv.line(ix + 29, iy + 6, ix + 41, iy + 6, ORANGE, 1)
    cv.line(ix + 29, iy + 14, ix + 41, iy + 14, ORANGE, 1)


def icon_robot(cv, ix, iy):
    # Robot head: the AI-weapons story.
    cv.line(ix + 22, iy + 12, ix + 22, iy + 5, SKY, 2)
    cv.circle(ix + 22, iy + 4, 2, GOLD)
    cv.rect(ix + 8, iy + 18, ix + 10, iy + 28, SKY)
    cv.rect(ix + 34, iy + 18, ix + 36, iy + 28, SKY)
    cv.rect(ix + 10, iy + 12, ix + 34, iy + 34, SKY)
    cv.circle(ix + 18, iy + 21, 3, NAVY)
    cv.circle(ix + 26, iy + 21, 3, NAVY)
    cv.line(ix + 16, iy + 28, ix + 28, iy + 28, NAVY, 2)


def icon_cap(cv, ix, iy):
    # Graduation cap: the exam-cheating story.
    cv.poly([(ix + 22, iy + 8), (ix + 42, iy + 18), (ix + 22, iy + 28), (ix + 2, iy + 18)],
            GOLD)
    cv.rect(ix + 14, iy + 26, ix + 30, iy + 36, (31, 41, 55))
    cv.line(ix + 42, iy + 18, ix + 42, iy + 32, GOLD, 2)
    cv.circle(ix + 42, iy + 34, 2, GOLD)


def icon_globe(cv, cx, cy, r):
    # Cracked Earth with a hot sun.
    cv.circle(cx, cy, r, OCEAN)
    cv.circle(cx - 35, cy - 25, 20, LAND)
    cv.circle(cx + 25, cy + 25, 16, LAND)
    cv.circle(cx + 15, cy - 50, 12, LAND)
    cv.circle(cx - 45, cy + 30, 12, LAND)
    cv.line(cx - 50, cy - 60, cx - 25, cy - 30, DARK, 3)
    cv.line(cx - 25, cy - 30, cx - 40, cy, DARK, 3)
    cv.line(cx - 40, cy, cx - 10, cy + 30, DARK, 3)
    cv.line(cx - 10, cy + 30, cx - 25, cy + 60, DARK, 3)
    cv.ring(cx, cy, r, 3, GOLD)
    sx, sy, sr = cx + 68, cy - 76, 24
    for k in range(8):
        ang = k * 3.14159265 / 4
        x0 = int(sx + (sr + 2) * cos(ang))
        y0 = int(sy + (sr + 2) * sin(ang))
        x1 = int(sx + (sr + 12) * cos(ang))
        y1 = int(sy + (sr + 12) * sin(ang))
        cv.line(x0, y0, x1, y1, ORANGE, 3)
    cv.circle(sx, sy, sr, ORANGE)


# ---------------------------------------------------------------- poster
def draw_cell(cv, x0, y0, x1, y1, bg, kicker, title, subs, accent, icon):
    cv.rect(x0, y0, x1, y1, bg)
    icon(cv, x0 + 18, y0 + 8)
    cv.text(x0 + 74, y0 + 20, kicker, 2, accent)
    y = y0 + 62
    for line in title:
        cv.text(x0 + 18, y, line, 5, WHITE)
        y += 41
    y = y0 + 150
    for line in subs:
        cv.text(x0 + 18, y, line, 3, CREAM)
        y += 25


def build():
    cv = Canvas()

    # Header.
    cv.rect(0, 0, W, 148, NAVY)
    cv.centre_text(26, "THE WORLD TODAY", 7, WHITE)
    cv.centre_text(92, "MONDAY 23 NOVEMBER 2026", 4, GOLD)
    cv.rect(0, 148, W, 152, GOLD)

    # Lead story: COP31 collapses.
    cv.rect(16, 160, 1008, 420, GREEN)
    cv.text(40, 182, "CLIMATE - ANTALYA, TURKEY", 3, GOLD)
    cv.text(40, 216, "COP31 COLLAPSES", 8, WHITE)
    cv.text(40, 296, "Climate talks end in failure", 4, GREEN_SUB)
    cv.text(40, 330, "EU rejects the weak text", 4, GREEN_SUB)
    cv.text(40, 372, "'DEEPLY DISAPPOINTED'", 5, GOLD)
    icon_globe(cv, 880, 290, 82)

    # Four stories in a 2x2 grid.
    # Gulf kicker in ORANGE, not RED: RED on SLATE measured 3.9:1, the dimmest
    # kicker on the poster (the others are 5.0-6.7:1) and nearly unreadable at
    # thumbnail size; ORANGE on SLATE is 6.6:1.
    draw_cell(cv, 16, 432, 504, 644, SLATE, "MIDDLE EAST - THE GULF",
              ["GULF WAR", "SPREADS"],
              ["Iran hits Bahrain,", "Houthis strike Riyadh"],
              ORANGE, icon_tanker)
    draw_cell(cv, 520, 432, 1008, 644, BLUE, "UNITED STATES - WASHINGTON",
              ["DEMOCRATS WIN", "258 SEATS"],
              ["Biggest majority", "since 1992"],
              GOLD, icon_dome)
    draw_cell(cv, 16, 656, 504, 868, STEEL, "UKRAINE - KYIV REGION",
              ["DRONE HITS", "KYIV REGION"],
              ["14 missing after", "Russian drone strike"],
              ORANGE, icon_building)
    draw_cell(cv, 520, 656, 1008, 868, PURPLE, "UNITED NATIONS - AI WEAPONS",
              ["UN AI-WEAPONS", "TALKS END"],
              ["No binding rules;", "talks run to 2028"],
              SKY, icon_robot)

    # Bottom strip: South Korea.
    cv.rect(16, 884, 1008, 1008, VIOLET)
    icon_cap(cv, 40, 904)
    cv.text(170, 902, "SOUTH KOREA - SEOUL", 2, GOLD)
    cv.text(170, 926, "SEOUL MINISTER QUITS", 5, WHITE)
    cv.text(170, 972, "AI exam-cheating scandal", 4, CREAM)
    # A crossed-out "AI" box on the right.
    cv.rect(830, 908, 960, 984, VIOLET)
    cv.line(830, 908, 960, 908, RED, 3)
    cv.line(830, 984, 960, 984, RED, 3)
    cv.line(830, 908, 830, 984, RED, 3)
    cv.line(960, 908, 960, 984, RED, 3)
    cv.text(862, 928, "AI", 6, WHITE)
    cv.line(838, 916, 952, 976, RED, 4)

    return png_bytes(cv.px)


def png_bytes(px):
    raw = b"".join(b"\x00" + bytes(px[y * W * 3:(y + 1) * W * 3]) for y in range(H))

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        return out + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = build()
    tmp = os.path.join(out_dir, ".entry.png.tmp")
    final = os.path.join(out_dir, "entry.png")
    with open(tmp, "wb") as f:
        f.write(data)
    os.chmod(tmp, 0o644)
    os.replace(tmp, final)
    os.chmod(final, 0o644)


if __name__ == "__main__":
    main()
