#!/usr/bin/env python3
"""news-image-20261119 -- front page of Thursday 19 November 2026.

Stdlib-only (zlib + struct). No network, no fonts, no randomness, no time.
Draws a 1024x1024 newspaper front page with a procedural 5x7 bitmap font
and a hand-written PNG encoder. Deterministic: identical bytes every run.
"""
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font 5x7
# Each glyph: 7 rows of 5 bits ("1" = ink). All text is upper-cased first.
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
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
}
# Normalise fancy punctuation to the glyphs we have.
NORMALISE = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
             "\u2014": "-", "\u2013": "-", "\u00b7": ".", "\u2022": ".",
             "\u00a3": "L", "\u00e9": "E"}


def norm_char(ch):
    ch = ch.upper()
    return NORMALISE.get(ch, ch)


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def wrap_text(s, scale, max_w):
    """Greedy word wrap; returns list of lines (each fits max_w)."""
    words = s.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = c

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                self.px[base + (xx - x0) * 3: base + (xx - x0) * 3 + 3] = c

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c, t=1):
        self.fill_rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.fill_rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.fill_rect(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d2 <= r * r:
                        self.set(xx, yy, c)
                else:
                    if abs(d2 - r * r) <= r:
                        self.set(xx, yy, c)

    def poly(self, pts, c):
        """Filled polygon via scanline fill."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.set(x, y, c)

    def draw_char(self, x, y, ch, scale, c):
        g = FONT.get(norm_char(ch))
        if g is None:
            return
        for r, row in enumerate(g):
            for col, bit in enumerate(row):
                if bit == "1":
                    self.fill_rect(x + col * scale, y + r * scale,
                                   scale, scale, c)

    def text(self, x, y, s, scale, c, align="left"):
        s = "".join(norm_char(ch) for ch in s)
        if align == "center":
            x -= text_width(s, scale) // 2
        elif align == "right":
            x -= text_width(s, scale)
        cx = x
        for ch in s:
            self.draw_char(cx, y, ch, scale, c)
            cx += 6 * scale
        return x

    def text_lines(self, x, y, lines, scale, c, leading=None, align="left"):
        lh = leading if leading is not None else 7 * scale + 3
        for ln in lines:
            self.text(x, y, ln, scale, c, align=align)
            y += lh
        return y


# ---------------------------------------------------------------- PNG encoder
def png_bytes(cv):
    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- palette
PAPER = bytes((247, 243, 232))
INK = bytes((17, 17, 17))
RED = bytes((176, 30, 36))
BLUE = bytes((27, 58, 92))
GREY = bytes((90, 88, 80))
LIGHT = bytes((232, 227, 214))
OCEAN = bytes((205, 224, 238))
LAND = bytes((62, 107, 79))
GOLD = bytes((196, 148, 44))
WHITE = bytes((255, 255, 255))


# ---------------------------------------------------------------- illustrations
# All drawings are simple flat geometric shapes, drawn procedurally.

def draw_flag(cv, x, y, w, h, kind):
    """Small flag on a pole at (x, y); flag box w x h."""
    cv.vline(x, y, h + 26, INK, 2)
    cv.fill_rect(x - 2, y + h + 24, 6, 4, GOLD)
    if kind == "US":
        cv.fill_rect(x + 2, y, w, h, WHITE)
        for i in range(7):
            if i % 2 == 0:
                cv.fill_rect(x + 2, y + i * h // 7, w, h // 7 + 1, RED)
        cv.fill_rect(x + 2, y, w * 2 // 5, h * 4 // 7, BLUE)
        for r in range(4):
            for c in range(5):
                cv.set(x + 5 + c * 7, y + 4 + r * 7, WHITE)
    elif kind == "CN":
        cv.fill_rect(x + 2, y, w, h, RED)
        cv.circle(x + 12, y + 10, 5, GOLD)
        cv.circle(x + 26, y + 6, 2, GOLD)
        cv.circle(x + 30, y + 12, 2, GOLD)
        cv.circle(x + 26, y + 18, 2, GOLD)
    elif kind == "RU":
        cv.fill_rect(x + 2, y, w, h // 3, WHITE)
        cv.fill_rect(x + 2, y + h // 3, w, h // 3, BLUE)
        cv.fill_rect(x + 2, y + 2 * h // 3, w, h // 3 + 1, RED)


def draw_summit(cv, x, y, w, h):
    """Three flags over a summit table."""
    cv.fill_rect(x, y + h - 26, w, 4, INK)
    fw = (w - 40) // 3
    fh = 34
    draw_flag(cv, x + 10, y + 8, fw, fh, "US")
    draw_flag(cv, x + 20 + fw, y + 8, fw, fh, "CN")
    draw_flag(cv, x + 30 + 2 * fw, y + 8, fw, fh, "RU")
    # table + three seats
    cv.fill_rect(x + 8, y + h - 22, w - 16, 14, BLUE)
    cv.fill_rect(x + 8, y + h - 8, w - 16, 3, GOLD)
    for sx in (x + 30, x + w // 2 - 8, x + w - 46):
        cv.fill_rect(sx, y + h - 40, 16, 14, RED)


def draw_court(cv, x, y, w, h):
    """Courthouse pediment + columns + gavel."""
    # pediment
    cv.poly([(x + 6, y + 34), (x + w // 2, y + 4), (x + w - 6, y + 34)], BLUE)
    cv.fill_rect(x + 4, y + 34, w - 8, 5, INK)
    # columns
    for cx in range(x + 16, x + w - 16, 34):
        cv.fill_rect(cx, y + 40, 10, h - 52, WHITE)
        cv.rect(cx, y + 40, 10, h - 52, INK, 1)
    cv.fill_rect(x + 4, y + h - 12, w - 8, 5, INK)
    # gavel on the right
    gx, gy = x + w - 52, y + 46
    cv.fill_rect(gx, gy, 26, 10, GOLD)
    cv.rect(gx, gy, 26, 10, INK, 1)
    cv.line(gx + 13, gy + 10, gx + 26, gy + 30, INK, 3)
    cv.fill_rect(gx - 8, gy + 30, 40, 4, INK)


def draw_skyline(cv, x, y, w, h):
    """Vice City skyline at sunset + big VI (GTA VI)."""
    # sunset sky
    cv.fill_rect(x, y, w, h, bytes((250, 196, 120)))
    cv.circle(x + w - 34, y + 22, 14, GOLD)
    # buildings
    heights = [28, 40, 34, 48, 30, 44, 24, 38]
    bw = w // 8
    for i, bh in enumerate(heights):
        bx = x + i * bw + 2
        cv.fill_rect(bx, y + h - 8 - bh, bw - 4, bh, INK)
        for wy in range(y + h - 8 - bh + 6, y + h - 12, 10):
            for wx in range(bx + 3, bx + bw - 6, 7):
                cv.set(wx, wy, GOLD)
    cv.fill_rect(x, y + h - 8, w, 8, BLUE)
    # palm tree silhouette
    px, py = x + 14, y + h - 8
    cv.line(px, py, px + 2, py - 26, INK, 3)
    for dx, dy in [(-12, -6), (12, -6), (-10, 2), (10, 2), (0, -10)]:
        cv.line(px + 2, py - 26, px + 2 + dx, py - 26 + dy, INK, 2)
    # big VI in the sky
    cv.text(x + w // 2, y + 2, "VI", 3, RED, align="center")


def draw_small_icon(cv, x, y, kind):
    """~44x30 icon for stories 4-11."""
    if kind == "voyager":
        cv.line(x + 2, y + 24, x + 30, y + 6, INK, 2)
        cv.circle(x + 34, y + 5, 4, GOLD)
        cv.poly([(x + 30, y + 12), (x + 42, y + 8), (x + 38, y + 20)], BLUE)
        cv.set(x + 10, y + 10, INK)
        cv.set(x + 16, y + 20, INK)
    elif kind == "ipo":
        cv.line(x + 4, y + 26, x + 40, y + 26, INK, 2)
        cv.line(x + 6, y + 22, x + 18, y + 14, RED, 3)
        cv.line(x + 18, y + 14, x + 28, y + 18, RED, 3)
        cv.line(x + 28, y + 18, x + 38, y + 4, RED, 3)
        cv.poly([(x + 38, y + 4), (x + 30, y + 4), (x + 38, y + 12)], RED)
        cv.text(x + 2, y + 2, "$", 2, BLUE)
    elif kind == "fed":
        cv.fill_rect(x + 4, y + 6, 36, 4, INK)
        for cx in range(x + 8, x + 38, 10):
            cv.fill_rect(cx, y + 10, 4, 16, INK)
        cv.fill_rect(x + 4, y + 26, 36, 3, INK)
        cv.text(x + 30, y + 2, "%", 1, RED)
    elif kind == "tank":
        cv.fill_rect(x + 4, y + 18, 30, 8, INK)
        cv.fill_rect(x + 12, y + 10, 14, 8, INK)
        cv.line(x + 26, y + 13, x + 42, y + 9, INK, 3)
        for cx in range(x + 8, x + 32, 8):
            cv.circle(cx, y + 28, 3, INK)
    elif kind == "bridge":
        cv.line(x + 2, y + 22, x + 22, y + 8, INK, 2)
        cv.line(x + 22, y + 8, x + 42, y + 22, INK, 2)
        cv.fill_rect(x + 2, y + 22, 40, 3, INK)
        cv.hline(x + 2, y + 28, 40, BLUE, 2)
    elif kind == "cyclone":
        cv.circle(x + 22, y + 16, 13, BLUE, fill=False)
        cv.circle(x + 22, y + 16, 8, BLUE, fill=False)
        cv.circle(x + 22, y + 16, 3, RED)
        cv.line(x + 22, y + 3, x + 30, y + 3, BLUE, 2)
        cv.line(x + 35, y + 16, x + 42, y + 16, BLUE, 2)
        cv.line(x + 22, y + 29, x + 14, y + 29, BLUE, 2)
    elif kind == "dome":
        cv.circle(x + 22, y + 12, 11, BLUE)
        cv.fill_rect(x + 11, y + 12, 22, 3, BLUE)
        cv.fill_rect(x + 8, y + 15, 28, 12, WHITE)
        cv.rect(x + 8, y + 15, 28, 12, INK, 1)
        cv.vline(x + 22, y + 0, 4, INK, 2)
    elif kind == "flame":
        cv.poly([(x + 22, y + 2), (x + 32, y + 16), (x + 28, y + 26),
                 (x + 16, y + 26), (x + 12, y + 16)], RED)
        cv.poly([(x + 22, y + 12), (x + 27, y + 20), (x + 17, y + 20)], GOLD)


# ---------------------------------------------------------------- content
TOP = [
    ("SUMMIT IN SHENZHEN", "TRUMP, XI AND PUTIN MEET IN SHENZHEN",
     "First-ever trilateral: 90 minutes at APEC, a 'peace declaration' - "
     "no Ukraine deal.", "summit"),
    ("THE HAGUE", "WORLD COURT: MYANMAR COMMITTED GENOCIDE",
     "The ICJ rules 9-6 that Myanmar committed genocide against the "
     "Rohingya in 2017. Final and binding.", "court"),
    ("GAMING", "GTA VI IS OUT",
     "Rockstar's epic lands on PS5 and Xbox, 13 years after GTA V - the "
     "most pre-ordered game ever.", "skyline"),
]

MID = [
    (4, "VOYAGER 1, ONE LIGHT-DAY AWAY",
     "NASA: probe is 16 billion miles out.", "voyager"),
    (5, "ANTHROPIC'S RECORD $81.3B IPO",
     "IPO raises $81.3B; shares up 17%.", "ipo"),
    (6, "FED: MORE HIKES LIKELY",
     "Officials see more rises ahead.", "fed"),
    (7, "ISRAEL'S RARE GAZA GROUND PUSH",
     "IDF tanks push near Nuseirat camp.", "tank"),
    (8, "CRIMEAN BRIDGE HIT AGAIN",
     "Third strike in a week; rail halted.", "bridge"),
    (9, "CYCLONE AKVAN BEARS DOWN",
     "90-100 km/h winds; 105,000 evacuated.", "cyclone"),
    (10, "JEFFRIES NOMINATED FOR SPEAKER",
     "Democrats pick Jeffries 251-11.", "dome"),
    (11, "IRAN WAR: 'SEE WHAT HAPPENS'",
     "Trump weighs Iran strikes.", "flame"),
]

LIST = [
    (12, "Senate rejects Iran war-powers 51-48"),
    (13, "N. Korea expands Yongbyon site"),
    (14, "S. Korea court clears ex-PM Han"),
    (15, "Japan PM Takaichi speaks with Putin"),
    (16, "Denmark backs Greenland defence"),
    (17, "COP31 final phase; fossil-fuel row"),
    (18, "Bangladesh unrest: 4 dead"),
    (19, "Tanker Gas Husky sunk off Bulgaria"),
    (20, "Migrant boat capsizes off Senegal"),
    (21, "APEC adopts 'Shenzhen Outlook'"),
    (22, "UK, Norway fund two Ukraine warships"),
    (23, "Abu Dhabi talks stall; grid hit"),
    (24, "Drone strikes kill 3 in Saratov"),
    (25, "France, Germany, UK weigh talks"),
    (26, "Gaza peace plan scores 4 of 26"),
    (27, "Trump asks court to block TPS"),
    (28, "Arizona probes OpenAI 'rogue AI'"),
    (29, "Musk turns from MAGA over $446m"),
    (30, "Nvidia revenue hits record $115.8B"),
    (31, "Dow -561; S&P falls 5th straight"),
    (32, "Rio Tinto pays $250m over Panguna"),
    (33, "589m children in conflict zones"),
    (34, "Florida man guilty in Haiti plot"),
    (35, "Judge: ICE in contempt in Colorado"),
    (36, "FBI chief Patel skips hearing"),
    (37, "Judge blocks Trump 'triumphal arch'"),
    (38, "England beat Australia by 97 runs"),
    (39, "Chelsea beat PSG 1-0; City, Real in"),
    (40, "Jazz end Lakers' 9-game win run"),
]

NUMBERS = [
    ("$81.3B", "RECORD IPO"),
    ("9-6", "ICJ VOTE"),
    ("16B MILES", "VOYAGER 1"),
    ("251-11", "JEFFRIES"),
    ("589M", "CHILDREN IN CONFLICT"),
    ("212 GB", "GTA VI DOWNLOAD"),
]

SOURCES = ("AP REUTERS AFP BBC NYT CNBC NPR CBS FED IMD NASA ICJ IAEA "
           "APEC SAVE THE CHILDREN")


# ---------------------------------------------------------------- layout
MX = 24            # side margin
CW = W - 2 * MX    # 976 content width


def draw():
    cv = Canvas(W, H, PAPER)
    y = 10

    # ---- masthead
    cv.text(W // 2, y, "THE DAILY WORLD", 6, INK, align="center")
    y += 46
    cv.fill_rect(MX, y, CW, 3, RED)
    y += 8
    cv.text(W // 2, y, "THURSDAY 19 NOVEMBER 2026", 2, INK, align="center")
    y += 17
    cv.text(W // 2, y, "40 STORIES FROM A DAY THAT CHANGED THE WORLD",
            2, RED, align="center")
    y += 18
    cv.fill_rect(MX, y, CW, 3, INK)
    y += 10

    # ---- top 3 stories
    colw = (CW - 2 * 20) // 3
    top_y = y
    top_bottom = top_y
    for i, (kicker, head, summ, kind) in enumerate(TOP):
        x = MX + i * (colw + 20)
        cv.text(x, top_y, kicker, 2, RED)
        iy = top_y + 16
        cv.rect(x, iy, colw, 76, INK, 1)
        cv.fill_rect(x + 1, iy + 1, colw - 2, 74, LIGHT)
        if kind == "summit":
            draw_summit(cv, x + 4, iy + 2, colw - 8, 72)
        elif kind == "court":
            draw_court(cv, x + 4, iy + 2, colw - 8, 72)
        else:
            draw_skyline(cv, x + 4, iy + 2, colw - 8, 72)
        hy = iy + 82
        lines = wrap_text(head, 3, colw)
        cv.text_lines(x, hy, lines[:3], 3, INK, leading=24)
        sy = hy + len(lines[:3]) * 24 + 4
        slines = wrap_text(summ, 2, colw)
        cv.text_lines(x, sy, slines[:4], 2, INK, leading=16)
        top_bottom = max(top_bottom, sy + len(slines[:4]) * 16)
    for i in range(2):
        x = MX + i * (colw + 20)
        cv.vline(x + colw + 10, top_y, top_bottom - top_y, GREY, 1)
    y = top_bottom + 8
    cv.fill_rect(MX, y, CW, 2, INK)
    y += 8

    # ---- stories 4-11 (2 rows x 4 cols)
    midw = (CW - 3 * 16) // 4
    for row in range(2):
        ry = y + row * 96
        for col in range(4):
            n, head, summ, kind = MID[row * 4 + col]
            x = MX + col * (midw + 16)
            draw_small_icon(cv, x, ry, kind)
            cv.text(x + 50, ry + 2, str(n) + ".", 2, RED)
            hlines = wrap_text(head, 2, midw)
            cv.text_lines(x, ry + 30, hlines[:2], 2, INK, leading=16)
            slines = wrap_text(summ, 2, midw)
            cv.text_lines(x, ry + 64, slines[:2], 2, GREY, leading=15)
    y += 192
    cv.fill_rect(MX, y, CW, 2, INK)
    y += 6

    # ---- world map
    cv.text(MX, y, "WHERE IT HAPPENED", 2, RED)
    y += 18
    map_y, map_h = y, 76
    cv.fill_rect(MX, map_y, CW, map_h, OCEAN)
    cv.rect(MX, map_y, CW, map_h, INK, 1)

    def mp(u, v):
        return (MX + int(u * CW / 100.0), map_y + int(v * map_h / 46.0))

    def continent(pts):
        cv.poly([mp(u, v) for u, v in pts], LAND)

    continent([(4, 6), (12, 3), (22, 4), (28, 7), (30, 12), (26, 16),
               (22, 20), (18, 24), (14, 22), (8, 18), (4, 12)])
    continent([(24, 26), (30, 25), (33, 30), (31, 38), (27, 44), (24, 36),
               (22, 30)])
    continent([(32, 2), (38, 2), (37, 6), (32, 6)])
    continent([(44, 6), (50, 4), (54, 7), (52, 12), (47, 13), (44, 10)])
    continent([(44, 18), (52, 16), (57, 20), (56, 28), (52, 36), (48, 38),
               (45, 30), (43, 24)])
    continent([(56, 5), (72, 3), (88, 5), (95, 9), (93, 15), (86, 18),
               (80, 16), (74, 20), (68, 22), (62, 18), (57, 12)])
    continent([(80, 24), (84, 23), (82, 27)])
    continent([(80, 32), (90, 31), (94, 35), (88, 40), (81, 37)])
    for u, v in [(24, 12), (47, 8), (56, 16), (56, 9), (76, 18),
                 (88, 15), (60, 18), (42, 22)]:
        dx, dy = mp(u, v)
        cv.circle(dx, dy, 4, RED)
        cv.circle(dx, dy, 2, WHITE)
    y = map_y + map_h + 4
    cv.text(W // 2, y,
            "SHENZHEN - THE HAGUE - GAZA - CRIMEA - ODISHA - WASHINGTON - "
            "RIYADH - SENEGAL", 1, GREY, align="center")
    y += 12
    cv.fill_rect(MX, y, CW, 2, INK)
    y += 6

    # ---- numbered list 12-40, two columns
    list_y = y
    col2x = MX + CW // 2 + 8
    half = CW // 2 - 8
    for idx, (n, item) in enumerate(LIST):
        col = 0 if idx < 15 else 1
        row = idx if idx < 15 else idx - 15
        x = MX if col == 0 else col2x
        line = str(n) + ". " + item
        cv.text(x, list_y + row * 16, line, 2, INK)
    y = list_y + 15 * 16 + 6
    cv.fill_rect(MX, y, CW, 2, INK)
    y += 6

    # ---- day in numbers
    cv.text(MX, y, "THE DAY IN NUMBERS", 2, RED)
    y += 18
    box_y = y
    cellw = CW // 6
    cv.rect(MX, box_y, CW, 36, INK, 2)
    for i, (val, lab) in enumerate(NUMBERS):
        x = MX + i * cellw
        if i:
            cv.vline(x, box_y, 36, GREY, 1)
        cv.text(x + cellw // 2, box_y + 3, val, 3, INK, align="center")
        cv.text(x + cellw // 2, box_y + 25, lab, 1, GREY, align="center")
    y = box_y + 36 + 5

    # ---- footer
    cv.fill_rect(MX, y, CW, 2, INK)
    y += 6
    cv.text(W // 2, y, "DATE CHECK: THURSDAY 19 NOVEMBER 2026", 2, RED,
            align="center")
    y += 15
    cv.text(W // 2, y, SOURCES, 1, GREY, align="center")
    y += 9
    return cv, y


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv, end_y = draw()
    data = png_bytes(cv)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes), layout ends at y=%d" % (path, len(data), end_y))


if __name__ == "__main__":
    main()
