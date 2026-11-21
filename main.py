#!/usr/bin/env python3
"""News poster for Saturday 21 November 2026.

Draws a 1024x1024 newspaper-style front page summing up the day's world
news, using only the Python standard library, and writes it to
/output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png when set).

The poster is drawn from scratch: a hand-written 5x7 bitmap font, simple
geometric icons, and a minimal PNG encoder (zlib + CRC32). No network,
no files besides this one, deterministic output.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font -----
# 5x7 bitmap font: each glyph is 7 rows of 5 bits, '#' = ink.
FONT = {
    'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    'B': ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    'C': ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    'D': ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    'E': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    'F': ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    'G': ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    'H': ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    'I': ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    'J': ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    'K': ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    'M': ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    'P': ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    'Q': ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    'V': ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    'W': ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    'X': ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    'Y': ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    'Z': ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    '0': ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    '1': ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    '2': ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    '3': ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    '4': ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    '6': ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    '8': ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    '9': ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ' ': ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    '.': ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ',': ["00000", "00000", "00000", "00000", "01100", "00100", "01000"],
    ':': ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    '-': ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    '%': ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    '/': ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    '(': ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ')': ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    '&': ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    '+': ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    '!': ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    '?': ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
    '$': ["00100", "01111", "10100", "01110", "00101", "11110", "00100"],
    '*': ["00000", "00100", "01110", "01110", "01110", "00100", "00000"],
}

# -------------------------------------------------------------- canvas -----
PAPER = (247, 243, 234)
NAVY = (20, 33, 61)
RED = (178, 34, 34)
INK = (24, 24, 24)
GREY = (90, 90, 90)
WHITE = (255, 255, 255)


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def hline(self, x, y, w, color, t=1):
        self.rect(x, y, w, t, color)

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def line(self, x0, y0, x1, y1, color, t=2):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.rect(x0 - t // 2, y0 - t // 2, t, t, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def text(self, x, y, s, scale, color, spacing=1):
        """Draw uppercase text; returns the width in pixels."""
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[' '])
            for row in range(7):
                for col in range(5):
                    if glyph[row][col] == '1':
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += (5 + spacing) * scale
        return cx - x - spacing * scale

    def text_width(self, s, scale, spacing=1):
        return len(s) * (5 + spacing) * scale - spacing * scale


def wrap(text, max_chars):
    """Greedy word wrap, returns a list of lines."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ png -----
def encode_png(canvas):
    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png

# -------------------------------------------------------------- layout -----
# Six stories reported on Saturday 21 November 2026:
#  - Russian strikes continue in Ukraine; Kryvyi Rih hit, two killed and
#    dozens wounded; Poland says two missiles and a drone came down on
#    its territory, PM Tusk calls it a deliberate provocation.
#  - COP31 climate talks in Antalya run past their deadline, deadlocked
#    over fossil fuels; Pacific nations warn over fossil fuels.
#  - Saudi-led coalition intercepts Houthi missiles aimed at Riyadh;
#    airstrikes in Yemen kill at least 41, including 11 children.
#  - US stocks: Nasdaq erases all its 2026 gains, S&P 500 slips into
#    correction in the AI sell-off; Nikkei down 5.1%.
#  - A magnitude 6.7 earthquake shakes the Peruvian Andes; one person
#    injured, buildings and roads damaged.
#  - FBI criminal database reportedly hacked as US outages continue;
#    Gen Z protests spread across 25 European countries.
# Footer: Trump defends ties to Putin and Xi after summit; Bayer pays
# $7.25bn to settle Roundup complaints; Bitcoin falls toward $62k.
STORIES = [
    ("UKRAINE / POLAND", "STRIKES GO ON, POLAND HIT AGAIN",
     "Kryvyi Rih hit: 2 killed, dozens hurt. Tusk: deliberate provocation.",
     (178, 34, 34), "missile"),
    ("ANTALYA", "COP31 TALKS RUN PAST DEADLINE",
     "Nearly 200 nations deadlocked over fossil fuels. Summit extended.",
     (20, 110, 70), "sun"),
    ("RIYADH / YEMEN", "HOUTHI MISSILES AIMED AT RIYADH",
     "Coalition intercepts them. Yemen airstrikes kill at least 41.",
     (20, 33, 61), "scales"),
    ("MARKETS", "NASDAQ ERASES ITS 2026 GAINS",
     "S&P 500 slips into correction in the AI sell-off. Nikkei down 5.1%.",
     (150, 90, 10), "bars"),
    ("PERU", "QUAKE M6.7 SHAKES THE ANDES",
     "Tremor strikes central Peru. One injured, buildings damaged.",
     (120, 70, 20), "quake"),
    ("UNITED STATES", "FBI DATABASE HACKED, OUTAGES GO ON",
     "Cyberattacks continue. Gen Z protests spread across 25 countries.",
     (30, 90, 140), "stars"),
]

FOOTER = "ALSO: TRUMP DEFENDS PUTIN AND XI TIES * BAYER PAYS $7.25BN"


def draw_icon(cv, kind, x, y, size, color):
    """Small geometric pictogram inside a panel's top-right corner."""
    if kind == "missile":  # triangle pointing up-right
        cv.line(x + 4, y + size - 6, x + size - 4, y + 4, color, 4)
        cv.line(x + size - 4, y + 4, x + size - 14, y + 6, color, 4)
        cv.line(x + size - 4, y + 4, x + size - 6, y + 14, color, 4)
    elif kind == "scales":  # balance: post, beam, two pans
        cv.line(x + size // 2, y + 4, x + size // 2, y + size - 6, color, 3)
        cv.line(x + 6, y + 10, x + size - 6, y + 10, color, 3)
        cv.line(x + 6, y + 10, x + 2, y + size - 12, color, 2)
        cv.line(x + size - 6, y + 10, x + size - 2, y + size - 12, color, 2)
        cv.rect(x - 2, y + size - 12, 12, 4, color)
        cv.rect(x + size - 10, y + size - 12, 12, 4, color)
    elif kind == "bars":  # falling chart bars
        heights = [size - 8, size - 18, size - 28]
        for i, hh in enumerate(heights):
            bx = x + 4 + i * (size // 3)
            cv.rect(bx, y + size - 4 - hh, size // 4, hh, color)
        cv.line(x + 2, y + 8, x + size - 2, y + size - 10, color, 3)
    elif kind == "stars":  # ring of dots (EU-style)
        for i in range(8):
            import math
            a = math.pi * 2 * i / 8
            cv.circle(int(x + size / 2 + math.cos(a) * size / 3),
                      int(y + size / 2 + math.sin(a) * size / 3), 3, color)
    elif kind == "quake":  # zigzag crack
        pts = [(x + 2, y + size - 8), (x + size // 3, y + 8),
               (x + size // 2, y + size - 12), (x + 2 * size // 3, y + 6),
               (x + size - 2, y + size - 8)]
        for a, b in zip(pts, pts[1:]):
            cv.line(a[0], a[1], b[0], b[1], color, 3)
    elif kind == "sun":  # sun with rays
        cv.circle(x + size // 2, y + size // 2, size // 4, color)
        for i in range(8):
            import math
            a = math.pi * 2 * i / 8
            x0 = int(x + size / 2 + math.cos(a) * (size / 4 + 3))
            y0 = int(y + size / 2 + math.sin(a) * (size / 4 + 3))
            x1 = int(x + size / 2 + math.cos(a) * (size / 2 - 2))
            y1 = int(y + size / 2 + math.sin(a) * (size / 2 - 2))
            cv.line(x0, y0, x1, y1, color, 3)


def draw_panel(cv, x, y, w, h, story):
    kicker, headline, sub, color, icon = story
    cv.rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, 8, color)  # accent bar
    cv.rect(x, y + h - 2, w, 2, (220, 214, 200))  # bottom rule
    cv.text(x + 18, y + 24, kicker, 2, color)
    draw_icon(cv, icon, x + w - 58, y + 18, 40, color)
    lines = wrap(headline, 17)
    yy = y + 56
    for ln in lines[:3]:
        cv.text(x + 18, yy, ln, 4, INK)
        yy += 34
    # Sub sits just below the headline, not at a fixed height, so panels
    # with two-line headlines do not show a dead gap.
    yy += 20
    sub_lines = wrap(sub, 36)
    for ln in sub_lines[:2]:
        cv.text(x + 18, yy, ln, 2, GREY)
        yy += 20


def draw():
    cv = Canvas(W, H, PAPER)
    # Masthead
    cv.rect(0, 0, W, 150, NAVY)
    cv.text(16, 20, "THE WORLD IN ONE DAY", 3, (200, 205, 220))
    cv.text(16, 56, "SATURDAY 21 NOVEMBER 2026", 6, WHITE)
    cv.rect(0, 142, W, 8, RED)
    # Story grid: 2 columns x 3 rows
    px, py = 16, 166
    pw, ph = 488, 258
    gap = 16
    for i, story in enumerate(STORIES):
        col, row = i % 2, i // 2
        draw_panel(cv, px + col * (pw + gap), py + row * (ph + gap),
                   pw, ph, story)
    # Footer strip
    cv.rect(0, 980, W, 44, NAVY)
    cv.text(16, 993, FOOTER, 2, (220, 224, 235))
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    png = encode_png(draw())
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
