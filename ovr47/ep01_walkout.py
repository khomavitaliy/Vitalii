"""OVR 47 — Episode 1: «THE WALKOUT».

Вертикальный ролик 1080x1920, ~56 с, полностью процедурный: персонажи,
фоны, субтитры, музыка и звуки создаются кодом (numpy + Pillow + ffmpeg).
Никаких чужих кадров, логотипов, музыки или голосов — нет проблем с правами.

Запуск:  python3 ovr47/ep01_walkout.py            -> ovr47/out/ep01_walkout.mp4
         python3 ovr47/ep01_walkout.py --frames 0 4.8 31.7   -> PNG-превью кадров
"""
import math
import os
import subprocess
import sys
import wave
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
DUR = 56.0
N = int(DUR * FPS)
SR = 44100
K = 2  # суперсэмплинг спрайтов персонажей (сглаживание)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
FONT_DIR = "/usr/share/fonts/opentype/inter/"
SUB_Y = 1400  # центр субтитров: выше нижнего UI TikTok

# ----------------------------------------------------------------- утилиты


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in(x):
    return x ** 3


def smooth(x):
    return x * x * (3 - 2 * x)


def ease_back(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, x):
    return a + (b - a) * x


def lerp_c(c1, c2, x):
    return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))


@lru_cache(maxsize=None)
def font(size, weight="Black"):
    fam = "InterDisplay" if size >= 60 else "Inter"
    return ImageFont.truetype(f"{FONT_DIR}{fam}-{weight}.otf", int(size))


# ----------------------------------------------------------------- персонажи

TIERS = {
    "bronze": dict(top=(214, 146, 92), bot=(112, 64, 32), edge=(250, 205, 160),
                   text=(58, 30, 10)),
    "gold": dict(top=(255, 232, 140), bot=(190, 142, 36), edge=(255, 250, 215),
                 text=(72, 50, 4)),
    "manager": dict(top=(64, 120, 108), bot=(18, 44, 44), edge=(150, 230, 210),
                    text=(225, 255, 245)),
    "pack": dict(top=(70, 30, 110), bot=(20, 8, 40), edge=(255, 214, 70),
                 text=(255, 214, 70)),
}
CHARS = {
    "dex": dict(name="DEX", rating="47", pos="ST", tier="bronze", club="FC LEFTOVER"),
    "kai": dict(name="KAI", rating="91", pos="ST", tier="gold", club="FC LEFTOVER"),
    "gaffer": dict(name="GAFFER", rating="MGR", pos="", tier="manager", club="FC LEFTOVER"),
}
SPEAKER_COL = {"dex": (236, 156, 96), "kai": (255, 216, 80), "gaffer": (96, 224, 194)}

CARD_W, CARD_H = 400, 560
SHIELD = [(48, 0), (352, 0), (400, 40), (400, 470), (200, 560), (0, 470), (0, 40)]
CANV_W, CANV_H = 560, 900
CARD_OX, CARD_OY = 80, 30
FOOT_Y = 880
INK = (16, 14, 20)


def gradient(w, h, top, bot, sheen=0.05):
    yy = np.linspace(0, 1, h)[:, None]
    xx = np.linspace(0, 1, w)[None, :]
    g = np.array(top) + (np.array(bot) - np.array(top)) * yy[..., None]
    g = g * np.ones((1, w, 1))
    g *= 1 + sheen * np.sin((xx * 3 + yy * 2) * math.pi * 6)[..., None]
    return np.clip(g, 0, 255).astype(np.uint8)


@lru_cache(maxsize=None)
def card_mask():
    m = Image.new("L", (CARD_W * K, CARD_H * K), 0)
    ImageDraw.Draw(m).polygon([(x * K, y * K) for x, y in SHIELD], fill=255)
    return m


@lru_cache(maxsize=None)
def card_base(cid):
    """Карточка без лица: градиент, рамка, рейтинг, позиция, имя."""
    if cid == "pack":
        tier, c = TIERS["pack"], None
    else:
        c = CHARS[cid]
        tier = TIERS[c["tier"]]
    w, h = CARD_W * K, CARD_H * K
    img = Image.fromarray(gradient(w, h, tier["top"], tier["bot"])).convert("RGBA")
    img.putalpha(card_mask())
    d = ImageDraw.Draw(img)
    poly = [(x * K, y * K) for x, y in SHIELD]
    d.line(poly + [poly[0]], fill=tier["edge"], width=14 * K, joint="curve")
    inner = [(200 * K + (x * K - 200 * K) * 0.9, 285 * K + (y * K - 280 * K) * 0.9)
             for x, y in SHIELD]
    d.line(inner + [inner[0]], fill=tier["edge"] + (110,), width=2 * K)
    tc = tier["text"]
    if c is None:  # рубашка пака
        d.text((200 * K, 270 * K), "?", font=font(300 * K), fill=tc, anchor="mm")
        return img
    rsize = 96 if len(c["rating"]) <= 2 else 54
    d.text((96 * K, 82 * K), c["rating"], font=font(rsize * K), fill=tc, anchor="mm")
    if c["pos"]:
        d.text((96 * K, 152 * K), c["pos"], font=font(40 * K, "Bold"), fill=tc, anchor="mm")
    d.line([(80 * K, 398 * K), (320 * K, 398 * K)], fill=tc, width=3 * K)
    d.text((200 * K, 440 * K), c["name"], font=font(58 * K), fill=tc, anchor="mm")
    d.text((200 * K, 492 * K), c["club"], font=font(24 * K, "Bold"), fill=tc, anchor="mm")
    return img


def draw_face(card, cid, e, t):
    """Лицо прямо на карточке. e — словарь выражения."""
    d = ImageDraw.Draw(card)
    k = K
    fx, ey, my = 250, 222, 318
    lx, ly = e.get("look", (0, 0))
    brow = e.get("brow", 0.0)
    eyes = e.get("eyes", "normal")
    blink = e.get("blink", False)
    ink = INK

    def P(x, y):
        return (x * k, y * k)

    for side in (-1, 1):
        ex = fx + side * 50
        if eyes == "tiny":
            d.ellipse([*P(ex - 9 + lx * 4, ey - 9 + ly * 4), *P(ex + 9 + lx * 4, ey + 9 + ly * 4)], fill=ink)
        elif blink or eyes == "half" and False:
            d.line([P(ex - 30, ey + 4), P(ex + 30, ey + 4)], fill=ink, width=7 * k)
        elif eyes == "wink" and side == 1:
            d.arc([*P(ex - 30, ey - 14), *P(ex + 30, ey + 22)], 200, 340, fill=ink, width=7 * k)
        else:
            rx, ry = (40, 46) if eyes == "big" else (33, 38)
            d.ellipse([*P(ex - rx, ey - ry), *P(ex + rx, ey + ry)], fill=(255, 255, 255),
                      outline=ink, width=5 * k)
            pr = 13 if eyes == "big" else 15
            px, py = ex + lx * (rx - pr - 6), ey + ly * (ry - pr - 6)
            d.ellipse([*P(px - pr, py - pr), *P(px + pr, py + pr)], fill=ink)
            if eyes == "sparkle":
                d.ellipse([*P(px - 4, py - 9), *P(px + 5, py)], fill=(255, 255, 255))
                d.ellipse([*P(px + 3, py + 3), *P(px + 8, py + 8)], fill=(255, 255, 255))
            if eyes == "half":  # «крутое» полузакрытое веко
                d.chord([*P(ex - rx - 2, ey - ry - 2), *P(ex + rx + 2, ey + ry + 2)], 180, 360,
                        fill=TIERS[CHARS[cid]["tier"]]["top"] if cid in CHARS else ink)
                d.line([P(ex - rx, ey), P(ex + rx, ey)], fill=ink, width=6 * k)
        # брови: inner — ближе к центру лица
        inner_dy, outer_dy = -14 * brow, 14 * brow
        bw = 12 if cid == "gaffer" else 7
        ix, ox = ex - side * 26, ex + side * 30
        if not (cid == "kai" and e.get("glasses", True)):
            d.line([P(ix, ey - 58 + inner_dy), P(ox, ey - 58 + outer_dy)], fill=ink, width=bw * k)

    # очки Кая
    if cid == "kai" and e.get("glasses", True):
        gx, gy = e.get("glasses_off", (0, 0))
        ga = e.get("glasses_rot", 0)
        g = Image.new("RGBA", (260 * k, 90 * k), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        gd.rounded_rectangle([0, 10 * k, 112 * k, 80 * k], 22 * k, fill=ink)
        gd.rounded_rectangle([148 * k, 10 * k, 260 * k, 80 * k], 22 * k, fill=ink)
        gd.rectangle([108 * k, 26 * k, 152 * k, 36 * k], fill=ink)
        gd.line([(22 * k, 28 * k), (48 * k, 22 * k)], fill=(255, 255, 255), width=6 * k)
        gd.line([(170 * k, 28 * k), (196 * k, 22 * k)], fill=(255, 255, 255), width=6 * k)
        if ga:
            g = g.rotate(ga, resample=Image.BICUBIC, expand=True)
        card.alpha_composite(g, (int((fx - 130 + gx) * k), int((ey - 45 + gy) * k)))

    # усы тренера
    if cid == "gaffer":
        d.chord([*P(fx - 62, my - 40), *P(fx + 2, my + 4)], 180, 360, fill=(70, 46, 34))
        d.chord([*P(fx - 2, my - 40), *P(fx + 62, my + 4)], 180, 360, fill=(70, 46, 34))

    mouth = e.get("mouth", "flat")
    if e.get("talk_open"):
        mouth = "talk"
    mx = fx
    dark = (60, 18, 24)
    if mouth == "smile":
        d.arc([*P(mx - 50, my - 34), *P(mx + 50, my + 26)], 20, 160, fill=ink, width=8 * k)
    elif mouth == "grin":
        d.chord([*P(mx - 58, my - 34), *P(mx + 58, my + 42)], 0, 180, fill=dark, outline=ink, width=5 * k)
        d.rectangle([*P(mx - 40, my + 3), *P(mx + 40, my + 14)], fill=(255, 255, 255))
    elif mouth == "frown":
        d.arc([*P(mx - 44, my - 4), *P(mx + 44, my + 48)], 205, 335, fill=ink, width=8 * k)
    elif mouth == "o":
        d.ellipse([*P(mx - 18, my - 12), *P(mx + 18, my + 30)], fill=dark, outline=ink, width=4 * k)
    elif mouth == "talk":
        d.ellipse([*P(mx - 34, my - 10), *P(mx + 34, my + 34)], fill=dark, outline=ink, width=5 * k)
        d.chord([*P(mx - 20, my + 12), *P(mx + 20, my + 34)], 180, 360, fill=(220, 90, 100))
    elif mouth == "smirk":
        d.line([P(mx - 40, my + 6), P(mx + 14, my + 6)], fill=ink, width=8 * k)
        d.arc([*P(mx + 4, my - 22), *P(mx + 44, my + 10)], 20, 120, fill=ink, width=8 * k)
    elif mouth == "wobble":
        pts = [P(mx - 44 + i * 11, my + 8 + (6 if i % 2 else -6)) for i in range(9)]
        d.line(pts, fill=ink, width=7 * k, joint="curve")
    else:  # flat
        d.line([P(mx - 34, my + 8), P(mx + 34, my + 8)], fill=ink, width=8 * k)

    if e.get("sweat"):
        sy = 150 + (t * 120) % 90
        d.ellipse([*P(352, sy), *P(372, sy + 26)], fill=(140, 200, 255), outline=ink, width=3 * k)
        d.polygon([P(354, sy + 10), P(362, sy - 12), P(370, sy + 10)], fill=(140, 200, 255))


def shimmer(card, t):
    """Блик, бегущий по золотой карточке."""
    w, h = card.size
    band = Image.new("L", (w, h), 0)
    x0 = ((t * 0.9) % 1.6 - 0.3) * w
    ImageDraw.Draw(band).polygon([(x0, 0), (x0 + 90 * K, 0), (x0 - 160 * K, h), (x0 - 250 * K, h)],
                                 fill=120)
    a = np.minimum(np.asarray(band), np.asarray(card.getchannel("A")))
    white = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    white.putalpha(Image.fromarray(a))
    card.alpha_composite(white)


def char_sprite(cid, p, t):
    """Персонаж-карточка с резиновыми руками и ногами (холст 2x)."""
    img = Image.new("RGBA", (CANV_W * K, CANV_H * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(x, y):
        return (x * K, y * K)

    lw = 15 * K
    walk = p.get("walk")
    for side, hx in ((-1, 232), (1, 328)):
        sw = 0
        lift = 0
        if walk is not None:
            ph = walk + (0 if side < 0 else math.pi)
            sw = 34 * math.sin(ph)
            lift = 22 * max(0, math.cos(ph))
        hip = (hx, 540)
        foot = (hx + sw + side * 14, 846 - lift)
        knee = ((hip[0] + foot[0]) / 2 + side * 10, (hip[1] + foot[1]) / 2)
        d.line([P(*hip), P(*knee), P(*foot)], fill=INK, width=lw, joint="curve")
        d.ellipse([*P(foot[0] - 44 + side * 14, foot[1] - 8), *P(foot[0] + 44 + side * 14, foot[1] + 34)],
                  fill=INK)
        d.ellipse([*P(foot[0] - 30 + side * 14, foot[1] - 2), *P(foot[0] + 6 + side * 14, foot[1] + 12)],
                  fill=(70, 70, 90))

    arms = p.get("arms", (12, 12))
    for side, ang, sh in ((-1, arms[0], (90, 330)), (1, arms[1], (470, 330))):
        a = math.radians(ang)
        L = 170
        hand = (sh[0] + side * L * math.sin(a), sh[1] + L * math.cos(a))
        mid = ((sh[0] + hand[0]) / 2, (sh[1] + hand[1]) / 2)
        nx, ny = -(hand[1] - sh[1]) / L, (hand[0] - sh[0]) / L
        elbow = (mid[0] + nx * 18 * side, mid[1] + ny * 18 * side)
        d.line([P(*sh), P(*elbow), P(*hand)], fill=INK, width=lw, joint="curve")
        r = 25
        d.ellipse([*P(hand[0] - r, hand[1] - r), *P(hand[0] + r, hand[1] + r)],
                  fill=(255, 255, 255), outline=INK, width=6 * K)
        if p.get("point") == side:
            fx2 = hand[0] + side * 46 * math.sin(a)
            fy2 = hand[1] + 46 * math.cos(a)
            d.line([P(*hand), P(fx2, fy2)], fill=INK, width=12 * K)

    card = card_base(cid).copy()
    draw_face(card, cid, p, t)
    if CHARS[cid]["tier"] == "gold":
        shimmer(card, t)
    img.alpha_composite(card, (CARD_OX * K, CARD_OY * K))
    return img


def blink_at(t, off):
    return ((t + off) % 3.3) < 0.11


def place(frame, cid, p, t):
    """Рисует персонажа: p = x, y (ступни), s, rot, sx, sy + выражение."""
    p = dict(p)
    if "blink" not in p:
        p["blink"] = blink_at(t, {"dex": 0, "kai": 1.1, "gaffer": 2.2}[cid])
    sp = speaking(cid, t)
    if sp is not None and p.get("talk", True):
        p["talk_open"] = int((t - sp) * 11) % 2 == 0
    spr = char_sprite(cid, p, t)
    s = p.get("s", 1.0)
    sx, sy = p.get("sx", 1.0), p.get("sy", 1.0)
    w, h = max(2, int(CANV_W * s * sx)), max(2, int(CANV_H * s * sy))
    spr = spr.resize((w, h), Image.LANCZOS)
    cx = p["x"]
    cy = p["y"] - (FOOT_Y - CANV_H / 2) * s * sy
    if p.get("rot"):
        spr = spr.rotate(p["rot"], resample=Image.BICUBIC, expand=True)
    if p.get("alpha", 1) < 1:
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * p["alpha"])))
    frame.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


# ----------------------------------------------------------------- субтитры

SUBS = [  # (начало, конец, кто, реплика)
    (5.70, 7.60, "dex", "Wait. Fireworks... for ME?"),
    (7.70, 9.30, "dex", "I'm literally him."),
    (10.30, 12.10, "kai", "A bronze? In MY club?"),
    (12.20, 13.20, "dex", "OUR club."),
    (13.40, 15.30, "kai", "Bro, you're SBC fodder."),
    (16.40, 19.00, "gaffer", "Oi! Nobody's fodder in MY dressing room."),
    (19.70, 21.30, "gaffer", "...except him."),
    (23.80, 26.00, "dex", "No no no no. I've got a FAMILY!"),
    (26.10, 27.90, "kai", "Click it. CLICK IT."),
    (32.30, 34.30, "kai", "...NINETY-NINE PACE?!"),
    (34.50, 37.00, "gaffer", "Lad's a bronze with a jet engine."),
    (40.10, 42.60, "dex", "Still 47. Still him."),
    (44.60, 46.90, "dex", "...why does it say my NAME?"),
    (47.10, 48.90, "kai", "Unlucky, speedy."),
]


def speaking(cid, t):
    for a, b, spk, _ in SUBS:
        if spk == cid and a <= t < b - 0.15:
            return a
    return None


@lru_cache(maxsize=256)
def sub_sprite(idx, active):
    a, b, spk, text = SUBS[idx]
    f = font(76)
    words = text.split()
    space = f.getlength(" ")
    lines, cur, curw = [], [], 0
    for wi, wd in enumerate(words):
        ww = f.getlength(wd)
        if cur and curw + space + ww > 900:
            lines.append(cur)
            cur, curw = [], 0
        cur.append((wi, wd, ww))
        curw += ww + (space if len(cur) > 1 else 0)
    lines.append(cur)
    lh = 92
    img = Image.new("RGBA", (1000, 70 + lh * len(lines) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # плашка с именем говорящего
    name = CHARS[spk]["name"]
    tf = font(34)
    tw = tf.getlength(name)
    d.rounded_rectangle([500 - tw / 2 - 22, 4, 500 + tw / 2 + 22, 56], 16,
                        fill=SPEAKER_COL[spk], outline=INK, width=4)
    d.text((500, 31), name, font=tf, fill=INK, anchor="mm")
    for li, line in enumerate(lines):
        total = sum(w for _, _, w in line) + space * (len(line) - 1)
        x = 500 - total / 2
        y = 70 + li * lh + lh / 2
        for wi, wd, ww in line:
            col = (255, 226, 60) if wi == active else (255, 255, 255)
            d.text((x, y), wd, font=f, fill=col, anchor="lm", stroke_width=9, stroke_fill=INK)
            x += ww + space
    return img


def draw_subs(frame, t):
    for idx, (a, b, spk, text) in enumerate(SUBS):
        if a <= t < b:
            words = text.split()
            lens = np.cumsum([len(w) + 1 for w in words])
            prog = clamp((t - a) / max(0.3, (b - a) - 0.25)) * lens[-1]
            active = int(min(len(words) - 1, np.searchsorted(lens, prog)))
            spr = sub_sprite(idx, active)
            pop = 0.86 + 0.14 * ease_back(seg(t, a, a + 0.14))
            if pop != 1:
                spr = spr.resize((int(spr.width * pop), int(spr.height * pop)), Image.BILINEAR)
            frame.paste(spr, (int(540 - spr.width / 2), int(SUB_Y - 70 * pop - 46)), spr)


# ----------------------------------------------------------------- текст и UI


@lru_cache(maxsize=512)
def text_sprite(text, size, fill, stroke, stroke_fill, weight="Black"):
    f = font(size, weight)
    bb = f.getbbox(text, stroke_width=stroke)
    img = Image.new("RGBA", (bb[2] - bb[0] + 24, bb[3] - bb[1] + 24), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((12 - bb[0], 12 - bb[1]), text, font=f, fill=fill,
                             stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def put_text(frame, text, cx, cy, size, fill=(255, 255, 255), stroke=8, stroke_fill=INK,
             scale=1.0, rot=0.0, alpha=1.0, weight="Black"):
    if alpha <= 0 or scale <= 0.01:
        return
    spr = text_sprite(text, size, fill, stroke, stroke_fill, weight)
    if scale != 1:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    frame.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


def chip(frame, text, cx, cy, fill=(20, 20, 28), fg=(255, 255, 255), size=34, alpha=1.0):
    if alpha <= 0:
        return
    f = font(size)
    tw = f.getlength(text)
    layer = Image.new("RGBA", (int(tw + 60), size + 34), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([2, 2, layer.width - 3, layer.height - 3], 18, fill=fill + (230,),
                        outline=(255, 255, 255, 90), width=2)
    d.text((layer.width / 2, layer.height / 2), text, font=f, fill=fg, anchor="mm")
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    frame.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


def brand_tag(frame):
    """Постоянная микро-метка бренда в левом верхнем углу каждого кадра."""
    chip(frame, "OVR 47  ·  EP.1", 190, 190, fill=(120, 70, 34), fg=(255, 226, 190), size=30, alpha=0.92)


@lru_cache(maxsize=8)
def cursor_sprite(size):
    pts = [(0, 0), (0, 0.74), (0.18, 0.58), (0.31, 0.88), (0.43, 0.83), (0.30, 0.54), (0.52, 0.54)]
    pad = 30
    img = Image.new("RGBA", (int(size * 0.6) + pad * 2, int(size * 0.95) + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    sh = [(pad + x * size + 18, pad + y * size + 22) for x, y in pts]
    d.polygon(sh, fill=(0, 0, 0, 110))
    pp = [(pad + x * size, pad + y * size) for x, y in pts]
    d.polygon(pp, fill=(255, 255, 255))
    d.line(pp + [pp[0]], fill=INK, width=12, joint="curve")
    return img, pad


def draw_cursor(frame, x, y, size=300, press=0.0):
    spr, pad = cursor_sprite(size)
    if press:
        s = 1 - 0.15 * press
        spr = spr.resize((int(spr.width * s), int(spr.height * s)), Image.BILINEAR)
        pad = pad * s
    frame.paste(spr, (int(x - pad), int(y - pad)), spr)


def panel(d, box, fill=(18, 18, 26), outline=(255, 255, 255), width=5, r=26):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


# ----------------------------------------------------------------- фоны

HY, HX = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)


def bg_rays(rot, c_ray, c_glow, base=(8, 6, 16), strength=1.0, cy=880, nrays=12):
    dx = (HX - W / 4) / (W / 2)
    dy = (HY - cy / 2) / (W / 2)
    ang = np.arctan2(dy, dx)
    rad = np.sqrt(dx * dx + dy * dy)
    rays = (0.5 + 0.5 * np.cos(ang * nrays + rot)) ** 6 * np.clip(1.4 - rad, 0, 1)
    glow = np.exp(-rad * 2.6)
    img = (np.array(base)[None, None, :]
           + np.array(c_ray)[None, None, :] * (rays * 0.55 * strength)[..., None]
           + np.array(c_glow)[None, None, :] * (glow * 0.8 * strength)[..., None])
    img *= (1 - 0.45 * np.clip(rad - 0.6, 0, 1))[..., None]
    small = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return small.resize((W, H), Image.BILINEAR)


@lru_cache(maxsize=1)
def bg_room():
    """Раздевалка «FC LEFTOVER»: стена-инвентарь с пустыми слотами карточек."""
    img = Image.fromarray(gradient(W, H, (26, 30, 56), (14, 16, 30), sheen=0.0))
    d = ImageDraw.Draw(img, "RGBA")
    # слоты карточек на стене
    for row in range(5):
        for col in range(6):
            x = 40 + col * 175 + (row % 2) * 40
            y = 250 + row * 205
            pts = [(x + px * 0.36, y + py * 0.32) for px, py in SHIELD]
            d.polygon(pts, fill=(255, 255, 255, 8), outline=(120, 140, 210, 40))
    # пол
    d.rectangle([0, 1180, W, H], fill=(20, 18, 26))
    for i in range(-8, 9):
        d.line([(540 + i * 40, 1180), (540 + i * 260, H)], fill=(255, 255, 255, 14), width=3)
    d.line([(0, 1180), (W, 1180)], fill=(255, 255, 255, 40), width=4)
    # скамейка
    d.rounded_rectangle([60, 1080, 1020, 1112], 10, fill=(70, 50, 40, 255))
    # прожектор
    arr = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    spot = np.exp(-(((xx - 540) / 520) ** 2 + ((yy - 760) / 700) ** 2) * 1.6)
    arr = arr * (0.55 + 0.75 * spot[..., None])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


@lru_cache(maxsize=1)
def vignette_mask():
    yy, xx = np.mgrid[0:H, 0:W]
    v = np.clip(((xx - 540) / 540) ** 2 + ((yy - 960) / 960) ** 2 - 0.35, 0, 1)
    return v


def darken(frame, a):
    if a <= 0:
        return frame
    return Image.blend(frame, Image.new("RGB", frame.size, (0, 0, 0)), a)


def red_alarm(frame, a):
    if a <= 0:
        return frame
    m = Image.fromarray((vignette_mask() * 255 * a).astype(np.uint8))
    frame.paste(Image.new("RGB", frame.size, (230, 20, 30)), (0, 0), m)
    return frame


def fireworks(frame, t, t0, ox, oy, seed, cols):
    dt = t - t0
    if dt < 0 or dt > 1.4:
        return
    r = np.random.default_rng(seed)
    n = 46
    ang = r.uniform(0, 2 * math.pi, n)
    sp = r.uniform(380, 820, n)
    d = ImageDraw.Draw(frame)
    fade = 1 - dt / 1.4
    for i in range(n):
        x = ox + math.cos(ang[i]) * sp[i] * dt
        y = oy + math.sin(ang[i]) * sp[i] * dt + 420 * dt * dt
        c = cols[i % len(cols)]
        rr = 9 * fade + 2
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=lerp_c((20, 10, 30), c, fade))


def lightning(frame, seed, a):
    if a <= 0:
        return
    r = np.random.default_rng(seed)
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for bolt in range(2):
        x = r.uniform(150, 930)
        pts = [(x, 0)]
        y = 0
        while y < 900:
            y += r.uniform(60, 120)
            x += r.uniform(-90, 90)
            pts.append((x, y))
        d.line(pts, fill=(170, 140, 255, int(110 * a)), width=34, joint="curve")
        d.line(pts, fill=(255, 255, 255, int(255 * a)), width=9, joint="curve")
    frame.paste(layer, (0, 0), layer)


def speed_lines(frame, x, y, direction, a=1.0):
    d = ImageDraw.Draw(frame)
    r = np.random.default_rng(int(x) % 97)
    for i in range(9):
        yy = y - 620 + i * 70 + r.uniform(-15, 15)
        ln = r.uniform(250, 600)
        x0 = x - direction * 160
        d.line([(x0, yy), (x0 - direction * ln, yy)], fill=(255, 255, 255), width=int(r.uniform(4, 10)))


def dust(frame, t, t0, x, y, s=1.0):
    dt = t - t0
    if not 0 <= dt < 0.5:
        return
    d = ImageDraw.Draw(frame)
    for k in range(6):
        side = -1 if k < 3 else 1
        rr = (30 + 50 * dt * 2) * s * (1 - dt * 1.6)
        px = x + side * (60 + (k % 3) * 70 + 300 * dt) * s
        if rr > 2:
            d.ellipse([px - rr, y - rr * 0.7, px + rr, y + rr * 0.5], fill=(150, 140, 150))


# ----------------------------------------------------------------- сцены


def pack(frame, tl, cx=540, cy=860):
    spin = tl * 4.2
    sx = max(0.08, abs(math.cos(spin)))
    base = card_base("pack")
    w = int(CARD_W * 1.0 * sx)
    h = int(CARD_H * 1.0)
    spr = base.resize((max(2, w), h), Image.BILINEAR)
    bob = 14 * math.sin(tl * 3)
    d = ImageDraw.Draw(frame, "RGBA")
    d.ellipse([cx - 330, cy - 360, cx + 330, cy + 360], fill=(255, 214, 70, 26))
    frame.paste(spr, (int(cx - w / 2), int(cy - h / 2 + bob)), spr)


def scene_pack(t, tl, cam, hook):
    frame = bg_rays(tl * 2.2, (255, 214, 70), (150, 70, 255))
    pack(frame, tl)
    if hook:
        for a, b, seed in ((0.30, 0.48, 1), (1.12, 1.26, 2)):
            if a <= t < b:
                lightning(frame, seed, 1 - seg(t, a, b))
                cam["flash"] = 0.55 * (1 - seg(t, a, b))
        if t >= 0.35:
            s = ease_back(seg(t, 0.35, 0.55)) * (1 + 0.03 * math.sin(t * 40))
            put_text(frame, "WALKOUT?!", 540, 400, 170, fill=(255, 214, 70), stroke=14,
                     stroke_fill=(40, 10, 60), scale=s, rot=-4)
            cam["shake"] = 14 * (1 - seg(t, 0.35, 0.9))
    else:
        cam["shake"] = 4 * seg(t, 54.5, 56)
        a = seg(t, 53.8, 54.0)
        put_text(frame, "another pack?", 540, SUB_Y, 70, alpha=a, stroke=8)
    return frame


def flag(frame, t, cx, cy, s):
    fw, fh = int(520 * s), int(340 * s)
    f = Image.new("RGB", (fw, fh))
    d = ImageDraw.Draw(f)
    cols = [(32, 150, 140), (245, 245, 240), (240, 130, 40)]
    for i, c in enumerate(cols):
        d.rectangle([0, i * fh / 3, fw, (i + 1) * fh / 3], fill=c)
    d.ellipse([fw / 2 - 40 * s, fh / 2 - 40 * s, fw / 2 + 40 * s, fh / 2 + 40 * s], fill=(40, 40, 60))
    step = 12
    for x in range(0, fw, step):
        dy = 16 * s * math.sin(x * 0.018 - t * 9)
        col = f.crop((x, 0, min(fw, x + step), fh))
        shade = 0.85 + 0.15 * math.sin(x * 0.018 - t * 9 + 1.2)
        col = col.point(lambda v: int(v * shade))
        frame.paste(col, (int(cx - fw / 2 + x), int(cy - fh / 2 + dy)))
    ImageDraw.Draw(frame).rectangle([cx - fw / 2 - 24, cy - fh / 2 - 30, cx - fw / 2 - 8, cy + fh / 2 + 260],
                                    fill=(210, 210, 220))


def badge(frame, cx, cy, s):
    d = ImageDraw.Draw(frame)
    r = 230 * s
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(24, 74, 54), outline=(255, 214, 70), width=int(16 * s))
    r2 = r - 40 * s
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=(255, 214, 70), width=int(4 * s))
    d.text((cx, cy - 40 * s), "FC", font=font(max(10, int(160 * s))), fill=(255, 214, 70), anchor="mm")
    d.text((cx, cy + 85 * s), "LEFTOVER", font=font(max(10, int(56 * s))), fill=(255, 255, 255), anchor="mm")


def scene_reveal(t, cam):
    if t < 4.5:
        stage = 0 if t < 2.8 else 1 if t < 3.6 else 2
        t0 = (2.0, 2.8, 3.6)[stage]
        frame = bg_rays(t * 3.0, (255, 214, 70), (255, 140, 40) if stage != 1 else (60, 160, 255))
        fireworks(frame, t, 2.0, 220, 700, 3, [(255, 214, 70), (255, 90, 90), (90, 200, 255)])
        fireworks(frame, t, 2.8, 860, 600, 4, [(255, 255, 255), (255, 214, 70)])
        fireworks(frame, t, 3.6, 300, 520, 5, [(120, 255, 160), (255, 214, 70)])
        pop = 1.35 - 0.35 * ease_out(seg(t, t0, t0 + 0.16))
        cam["flash"] = 0.35 * (1 - seg(t, t0, t0 + 0.12))
        cam["shake"] = 10 * (1 - seg(t, t0, t0 + 0.3))
        label = ("POSITION", "NATION", "CLUB")[stage]
        put_text(frame, label, 540, 470, 64, fill=(255, 255, 255), stroke=7)
        if stage == 0:
            put_text(frame, "ST", 540, 860, 360, fill=(255, 214, 70), stroke=16, scale=pop)
        elif stage == 1:
            flag(frame, t, 560, 840, pop)
        else:
            badge(frame, 540, 860, pop)
        return frame
    # шлепок карточки — бронза 47
    dull = seg(t, 4.62, 5.1)
    frame = bg_rays(lerp(t * 3.0, 4.6 * 3.0 + (t - 4.6) * 0.4, dull),
                    lerp_c((255, 214, 70), (120, 84, 60), dull),
                    lerp_c((255, 140, 40), (60, 40, 30), dull), strength=lerp(1, 0.6, dull))
    k = ease_out(seg(t, 4.5, 4.68))
    s = lerp(2.6, 1.05, k)
    land = seg(t, 4.68, 4.9)
    squash = 1 - 0.18 * math.sin(land * math.pi) if 0 < land < 1 else 1
    place(frame, "dex", dict(x=540, y=1260, s=s, sy=squash, sx=2 - squash, arms=(14, 14),
                             mouth="flat", eyes="normal", brow=0.2), t)
    if 4.68 <= t < 5.0:
        cam["shake"] = 22 * (1 - seg(t, 4.68, 5.0))
        cam["flash"] = 0.45 * (1 - seg(t, 4.68, 4.8))
    dust(frame, t, 4.68, 540, 1260, 1.3)
    # одинокая грустная искорка
    if t > 4.85:
        dt = t - 4.85
        x, y = 820 + 20 * math.sin(dt * 5), 300 + 160 * dt
        ImageDraw.Draw(frame).ellipse([x - 7, y - 7, x + 7, y + 7], fill=(255, 200, 90))
    a = seg(t, 4.95, 5.1)
    put_text(frame, "...a 47.", 540, 250, 130, fill=(190, 190, 196), stroke=10, alpha=a,
             scale=0.9 + 0.1 * ease_back(a))
    return frame


def scene_dex_close(t, cam):
    frame = bg_rays(t * 0.5, (120, 84, 60), (70, 46, 30), strength=0.7)
    if t < 7.7:
        up = seg(t, 6.6, 6.9)
        p = dict(eyes="big", look=(0.5, -0.8), brow=0.7, mouth="o",
                 arms=(lerp(14, 160, up), lerp(14, 160, up)))
        dx = 820 + 40 * math.sin(t * 4)
        y = 260 + 110 * (t - 5.6)
        d = ImageDraw.Draw(frame)
        d.ellipse([dx - 7, y - 7, dx + 7, y + 7], fill=(255, 200, 90, 255))
    else:
        p = dict(eyes="sparkle", look=(0, -0.2), brow=-0.2, mouth="grin", arms=(32, 32))
    p.update(x=540, y=1390, s=1.2)
    if t >= 7.7:
        p["rot"] = 3 * math.sin((t - 7.7) * 6)
    place(frame, "dex", p, t)
    chip(frame, "DEX  ·  47 OVR  ·  ST", 560, 290, fill=(120, 70, 34), fg=(255, 230, 200),
         size=40, alpha=seg(t, 5.8, 6.1))
    cam["z"] = 1.0 + 0.07 * seg(t, 5.6, 9.4)
    cam["cy"] = 900
    return frame


def scene_room(t, cam):
    frame = bg_room().copy()
    gaffer_in = t >= 16.0
    # Декс
    dex_x = lerp(-160, 300, ease_out(seg(t, 9.4, 10.1)))
    if gaffer_in:
        dex_x = lerp(300, 250, seg(t, 16.0, 16.3))
    dex = dict(x=dex_x, y=1180, s=0.8, arms=(14, 14), look=(0.8, 0), mouth="flat", brow=0.0)
    if t < 10.1:
        dex["walk"] = t * 14
    if 10.3 <= t < 12.15:
        dex.update(brow=0.4, look=(0.9, 0))
    elif 12.15 <= t < 13.3:
        dex.update(brow=-0.8, arms=(14, 165), point=1, look=(0.9, 0))
    elif 15.3 <= t < 16.0:
        dex.update(mouth="frown", brow=1.0, look=(0, 0.7))
    elif 16.0 <= t < 19.0:
        dex.update(eyes="sparkle", mouth="grin", look=(0.8, -0.3), arms=(150, 150) if t > 16.6 else (14, 14))
    elif t >= 19.0:
        dex.update(look=(0.8, 0), mouth="flat" if t < 19.8 else "frown", brow=0 if t < 19.8 else 1.0)
    # прыжок от испуга
    if 16.15 <= t < 16.55:
        dex["y"] -= 70 * math.sin(seg(t, 16.15, 16.55) * math.pi)
    # Кай
    kai_x = lerp(1350, 800, ease_out(seg(t, 9.9, 10.3)))
    if gaffer_in:
        kai_x = lerp(800, 840, seg(t, 16.0, 16.3))
    kai = dict(x=kai_x, y=1180, s=0.8, arms=(28, 28), look=(-0.8, 0), mouth="smirk",
               rot=lerp(-12, 0, seg(t, 10.1, 10.4)))
    if 10.3 <= t < 12.15:
        kai.update(arms=(95, 28), point=-1, brow=-0.8)
    elif 13.4 <= t < 15.4:
        kai.update(mouth="smirk")
    elif 19.75 <= t:
        kai.update(mouth="grin", rot=4 * math.sin(t * 28), arms=(40, 40))
    if 16.15 <= t < 16.55:
        kai["y"] -= 70 * math.sin(seg(t, 16.15, 16.55) * math.pi)
    if t >= 9.9:
        place(frame, "kai", kai, t)
    if gaffer_in:
        fall = seg(t, 16.0, 16.25)
        gy = lerp(-500, 1180, fall * fall)
        land = seg(t, 16.25, 16.6)
        sq = 1 - 0.25 * math.sin(land * math.pi) * (1 - land) if 0 < land < 1 else 1
        g = dict(x=540, y=gy, s=0.8, sy=sq, sx=2 - sq, arms=(160, 160), brow=-1.0,
                 mouth="flat", look=(0, 0))
        if 16.4 <= t < 19.0:
            g["arms"] = (150 + 15 * math.sin(t * 14), 150 - 15 * math.sin(t * 14))
        elif 19.0 <= t < 19.7:
            g.update(arms=(20, 20), look=(-0.9, 0), brow=-0.3)
        elif t >= 19.7:
            g.update(arms=(96, 20), point=-1, look=(-0.9, 0), brow=-0.6)
        elif t >= 16.25:
            g["arms"] = (20, 20)
        place(frame, "gaffer", g, t)
        dust(frame, t, 16.25, 540, 1185, 1.0)
        if 16.25 <= t < 16.5:
            cam["shake"] = 18 * (1 - seg(t, 16.25, 16.5))
    place(frame, "dex", dex, t)
    chip(frame, "FC LEFTOVER  ·  DRESSING ROOM", 540, 300, size=36,
         alpha=seg(t, 9.6, 9.9) * (1 - seg(t, 12.2, 12.5)))
    # панч-зум на грустного Декса
    if 15.3 <= t < 16.0:
        cam.update(z=1.5, cx=dex_x, cy=840, shake=8 * (1 - seg(t, 15.3, 15.6)))
    if 19.7 <= t < 21.5:
        cam.update(z=lerp(1.0, 1.12, ease_out(seg(t, 19.7, 19.9))), cx=420, cy=900)
    # переход-слайд
    if t < 9.6:
        off = int((1 - ease_out(seg(t, 9.4, 9.6))) * W)
        out = Image.new("RGB", (W, H), (0, 0, 0))
        out.paste(frame, (off, 0))
        frame = out
    return frame


MENU = ["VIEW STATS", "QUICK SELL  ·  150", "SEND TO SBC"]
MENU_BOX = (500, 360, 1010, 700)
ITEM_Y = [435, 535, 635]
STATS = [("PAC", 99), ("SHO", 31), ("PAS", 28), ("DRI", 40), ("DEF", 12), ("PHY", 19)]


def draw_menu(frame, t, hl):
    pop = ease_back(seg(t, 22.8, 23.0))
    if pop <= 0:
        return
    layer = Image.new("RGBA", (530, 360), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    panel(d, (5, 5, 525, 355), fill=(18, 18, 26), outline=(255, 255, 255))
    for i, txt in enumerate(MENU):
        y = 75 + i * 100
        if i == hl:
            col = (255, 226, 60) if i != 1 else (255, 80, 80)
            d.rounded_rectangle((22, y - 40, 508, y + 40), 16, fill=col)
            d.text((265, y), txt, font=font(44), fill=INK, anchor="mm")
        else:
            d.text((265, y), txt, font=font(44), fill=(220, 220, 230), anchor="mm")
    if pop != 1:
        layer = layer.resize((max(1, int(530 * pop)), max(1, int(360 * pop))), Image.BILINEAR)
    frame.paste(layer, (int(755 - layer.width / 2), int(530 - layer.height / 2)), layer)


def draw_stats(frame, t):
    slide = ease_out(seg(t, 30.45, 30.7)) - ease_in(seg(t, 36.9, 37.2))
    if slide <= 0:
        return
    y0 = lerp(-450, 190, slide)
    layer = Image.new("RGBA", (860, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    hit = t >= 31.6
    panel(d, (4, 4, 856, 396), fill=(16, 16, 24), outline=(80, 240, 120) if hit else (255, 255, 255))
    d.text((430, 40), "DEX  ·  STATS", font=font(36), fill=(236, 156, 96), anchor="mm")
    for i, (lab, val) in enumerate(STATS):
        if t < 30.6 + i * 0.1:
            continue
        y = 100 + i * 52
        if i == 0:
            v = int(99 * ease_in(seg(t, 30.9, 31.6)))
            col = (80, 240, 120) if hit else (255, 255, 255)
            if hit:
                d.rounded_rectangle((20, y - 24, 840, y + 24), 12, fill=(30, 90, 50))
        else:
            v = val
            col = (240, 80, 80)
        d.text((50, y), lab, font=font(36), fill=(230, 230, 236), anchor="lm")
        d.rounded_rectangle((170, y - 11, 690, y + 11), 11, fill=(50, 50, 64))
        if v > 0:
            d.rounded_rectangle((170, y - 11, 170 + 520 * v / 99, y + 11), 11, fill=col)
        d.text((810, y), str(v), font=font(44), fill=col, anchor="rm")
    frame.paste(layer, (110, int(y0)), layer)


def cursor_pos(t):
    """Траектория Курсора в сценах F/G."""
    if t < 22.6:
        k = smooth(seg(t, 21.8, 22.6))
        x, y = lerp(1250, 330, k), lerp(-260, 700, k)
    elif t < 23.3:
        x, y = 330, 700
    elif t < 30.1:
        k = smooth(seg(t, 23.3, 23.7))
        x, y = lerp(330, 600, k), lerp(700, 545, k)
    else:
        k = smooth(seg(t, 30.1, 30.25))
        x, y = 600, lerp(545, 445, k)
    trem = 0
    if 25.8 <= t < 30.1:
        trem = 2 + 6 * seg(t, 25.8, 30.0)
    x += trem * math.sin(t * 53)
    y += trem * math.cos(t * 47)
    return x, y


def scene_cursor(t, cam):
    frame = bg_room().copy()
    stats_phase = t >= 30.3
    dk = 0.55 * seg(t, 21.5, 22.0)
    if stats_phase:
        dk = lerp(0.55, 0.35, seg(t, 31.6, 31.8))
    frame = darken(frame, dk)
    if t < 23.2:
        frame = red_alarm(frame, 0.55 * (0.5 + 0.5 * math.sin(t * 20)) * (1 - seg(t, 22.9, 23.2)))
    if 31.6 <= t < 32.0:
        cam["flash"] = 0.3 * (1 - seg(t, 31.6, 31.9))
        cam["shake"] = 16 * (1 - seg(t, 31.6, 32.0))

    # позиции
    m = seg(t, 21.5, 21.9)
    g2 = seg(t, 30.4, 30.7)
    dex = dict(x=lerp(250, 300, m), y=1180, s=lerp(0.8, 0.85, m), arms=(14, 14), look=(0.5, -0.8),
               eyes="big", brow=0.6, mouth="o", sweat=t > 22.6)
    kai = dict(x=lerp(840, 800, m), y=1180, s=lerp(0.8, 0.55, m), arms=(28, 28), mouth="smirk",
               look=(-0.5, -0.5))
    gaf = dict(x=lerp(540, 975, m), y=1180, s=lerp(0.8, 0.5, m), arms=(20, 20), mouth="flat",
               look=(-0.6, -0.6), brow=0.4)
    if t < 22.6:
        dex.update(eyes="normal", mouth="flat", look=(0.6, -0.6), sweat=False)
    if 23.8 <= t < 26.0:
        dex.update(arms=(160 + 15 * math.sin(t * 16), 160 - 15 * math.sin(t * 16)), brow=1.0)
    elif 26.0 <= t < 30.3:
        dex.update(mouth="wobble", brow=1.0, look=(0.6, -0.6))
    if 26.1 <= t < 27.9:
        kai.update(mouth="grin", arms=(150 + 25 * math.sin(t * 14), 150 + 25 * math.sin(t * 14)))
    if stats_phase:
        # заморозка + реакция
        dex = dict(x=lerp(300, 260, g2), y=1200, s=lerp(0.85, 0.72, g2), arms=(14, 14), eyes="big",
                   mouth="o", look=(0.4, -0.9), brow=0.5)
        kai = dict(x=lerp(800, 590, g2), y=1200, s=lerp(0.55, 0.72, g2), arms=(28, 28), mouth="o",
                   look=(0, -0.9))
        gaf = dict(x=lerp(975, 890, g2), y=1200, s=lerp(0.5, 0.72, g2), arms=(20, 20), mouth="o",
                   look=(-0.3, -0.9), brow=0.6)
        if t >= 31.6:
            dex.update(eyes="sparkle", mouth="grin", arms=(165, 165), brow=-0.2)
        if t >= 32.45:
            drop = seg(t, 32.45, 32.85)
            if drop < 1:
                kai.update(glasses_off=(0, 260 * drop * drop), glasses_rot=-40 * drop)
            else:
                kai.update(glasses=False)
            kai.update(eyes="tiny", mouth="o" if t < 34.3 else "wobble", brow=1.0,
                       arms=(120, 120) if t < 34.3 else (20, 20))
        if 34.5 <= t < 37.0:
            gaf.update(brow=0.8, look=(-0.6, 0), arms=(40, 40))
        if t >= 37.0:
            # Декс носится по экрану
            runs = [(37.0, 37.35, 260, 1320), (37.45, 37.8, 1320, -240), (37.9, 38.25, -240, 1320),
                    (38.35, 38.8, -240, 540)]
            dex_x, direction = 1320, 1
            for a, b, x0, x1 in runs:
                if t >= a:
                    k = seg(t, a, b)
                    dex_x = lerp(x0, x1, k if b != 38.8 else ease_out(k))
                    direction = 1 if x1 > x0 else -1
            dex.update(x=dex_x, walk=t * 40, rot=-14 * direction, eyes="sparkle", mouth="grin",
                       arms=(110, 110), y=1200, s=0.72)
            if t < 38.6:
                speed_lines(frame, dex_x, 1100, direction)
            if t >= 37.55:
                kai["rot"] = (t - 37.55) * 900 if t < 37.95 else 0
            gaf["look"] = (max(-1, min(1, (dex_x - 890) / 300)), 0)
            kai["look"] = (max(-1, min(1, (dex_x - 590) / 300)), 0)
    place(frame, "gaffer", gaf, t)
    place(frame, "kai", kai, t)
    place(frame, "dex", dex, t)

    if not stats_phase:
        # баннер «THE CURSOR»
        if 21.6 <= t < 23.1:
            a = seg(t, 21.6, 21.75) * (1 - seg(t, 22.9, 23.1))
            d = ImageDraw.Draw(frame)
            cx, cy = 540, 280
            d.polygon([(cx - 400, cy + 40), (cx - 340, cy - 60), (cx - 280, cy + 40)], fill=(255, 214, 70))
            d.text((cx - 340, cy + 8), "!", font=font(70), fill=INK, anchor="mm")
            put_text(frame, "THE CURSOR", cx + 90, cy, 110, fill=(255, 80, 80), stroke=10, alpha=a,
                     scale=1 + 0.03 * math.sin(t * 40))
        hl = 0 if t < 23.5 else 1
        if t >= 30.15:
            hl = 0
        if t < 30.45:
            draw_menu(frame, t, hl)
        cx, cy = cursor_pos(t)
        press = 1 - seg(t, 22.65, 22.8) if t >= 22.65 else 0
        if 30.25 <= t < 30.4:
            press = 1
        if t >= 21.8:
            draw_cursor(frame, cx, cy, press=press)
        # шаги-зумы на ударах сердца
        if 28.0 <= t < 30.3:
            steps = sum(1 for b in (28.0, 28.7, 29.4) if t >= b)
            punch = max(0.0, 0.04 * (1 - seg(t, max(b for b in (28.0, 28.7, 29.4) if t >= b),
                                               max(b for b in (28.0, 28.7, 29.4) if t >= b) + 0.15)))
            cam.update(z=1.0 + 0.1 * steps + punch, cx=cx, cy=cy + 80)
    else:
        draw_stats(frame, t)
        if 30.3 <= t < 30.6:
            draw_cursor(frame, 600, 445, press=1 - seg(t, 30.3, 30.5))
        if t < 31.6 and 30.35 <= t:
            cam["shake"] = 6 * (1 - seg(t, 30.35, 30.6))
        if 31.6 <= t < 32.2:
            cam.update(z=lerp(1.12, 1.0, ease_out(seg(t, 31.6, 32.2))), cx=540, cy=420)
    return frame


def stamp(frame, t, t0, cx=540, cy=320):
    k = seg(t, t0, t0 + 0.25)
    if k <= 0:
        return
    s = lerp(2.6, 1.0, ease_out(k))
    d = ImageDraw.Draw(frame)
    r1, r2 = 250 * s, 205 * s
    rot = t * 0.6
    pts = []
    for i in range(32):
        r = r1 if i % 2 == 0 else r2
        a = rot + i * math.pi / 16
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a) * 0.62))
    d.polygon(pts, fill=(110, 62, 26), outline=(250, 205, 160), width=6)
    put_text(frame, "OVR 47", cx, cy, 190, fill=(236, 156, 96), stroke=14,
             stroke_fill=(46, 22, 6), scale=s, rot=-7)


def scene_brand(t, cam):
    frame = bg_rays(t * 0.9, (236, 156, 96), (140, 80, 30), base=(24, 12, 6), strength=0.9, cy=900)
    skid = seg(t, 38.8, 39.15)
    dex = dict(x=lerp(470, 540, ease_out(skid)), y=1330, s=0.9, rot=lerp(12, 0, ease_out(skid)),
               arms=(34, 34), eyes="half", brow=-0.3, mouth="smirk", look=(0, 0))
    if t >= 42.7:
        dex.update(eyes="wink", mouth="smirk")
    dust(frame, t, 38.8, 470, 1330, 1.0)
    place(frame, "dex", dex, t)
    stamp(frame, t, 39.4)
    if 39.65 <= t < 40.0:
        cam["shake"] = 16 * (1 - seg(t, 39.65, 40.0))
        cam["flash"] = 0.35 * (1 - seg(t, 39.65, 39.8))
    put_text(frame, "@ovr47", 540, 500, 54, fill=(255, 230, 200), stroke=6, alpha=seg(t, 40.0, 40.3))
    return frame


def draw_sbc(frame, t):
    k = ease_out(seg(t, 43.6, 43.9))
    if k <= 0:
        return
    y0 = lerp(-520, 150, k)
    layer = Image.new("RGBA", (920, 450), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    panel(d, (4, 4, 916, 446), fill=(20, 18, 28), outline=(240, 200, 80), width=7)
    d.rounded_rectangle((30, 26, 230, 76), 14, fill=(255, 226, 60))
    d.text((130, 51), "NEW SBC", font=font(32), fill=INK, anchor="mm")
    d.text((460, 140), "BRONZE SACRIFICE", font=font(80), fill=(255, 255, 255), anchor="mm")
    req = "REQUIRES:  1x "
    f44 = font(44)
    total = f44.getlength(req + "DEX (47)")
    x = 460 - total / 2
    d.text((x, 222), req, font=f44, fill=(200, 200, 210), anchor="lm")
    d.text((x + f44.getlength(req), 222), "DEX (47)", font=f44, fill=(236, 156, 96), anchor="lm")
    left = max(0, 86399 - int(max(0, t - 43.9)))
    hh, mm, ss = left // 3600, left % 3600 // 60, left % 60
    d.text((460, 300), f"EXPIRES  {hh:02d}:{mm:02d}:{ss:02d}", font=font(50), fill=(255, 90, 90), anchor="mm")
    hover = t >= 50.6
    pulse = 0.5 + 0.5 * math.sin(t * 12) if hover else 0
    col = lerp_c((60, 200, 100), (140, 255, 170), pulse)
    d.rounded_rectangle((260, 345, 660, 425), 20, fill=col, outline=(255, 255, 255) if hover else None,
                        width=5)
    d.text((460, 385), "SUBMIT", font=font(56), fill=INK, anchor="mm")
    frame.paste(layer, (80, int(y0)), layer)


def scene_sbc(t, cam):
    frame = darken(bg_room().copy(), 0.4)
    dex = dict(x=400, y=1250, s=0.75, arms=(14, 14), look=(0.2, -0.9), eyes="normal", mouth="flat")
    if 44.6 <= t < 47.0:
        dex.update(eyes="big", brow=1.0, sweat=True)
    elif 47.0 <= t < 49.0:
        dex.update(look=(0.9, 0), brow=0.5, mouth="frown")
    elif t >= 49.0:
        dex.update(eyes="big", brow=1.0, mouth="wobble", sweat=True, look=(0.4, -0.9))
    kai = dict(x=850, y=1250, s=0.58, arms=(28, 28), mouth="smirk", look=(-0.8, 0),
               glasses_off=(14, 12), glasses_rot=14)
    place(frame, "kai", kai, t)
    place(frame, "dex", dex, t)
    draw_sbc(frame, t)
    if 43.6 <= t < 43.9:
        cam["shake"] = 8 * (1 - seg(t, 43.6, 43.9))
    if t >= 49.0:
        k = smooth(seg(t, 49.0, 50.6))
        x = lerp(1200, 600, k) + (3 + 5 * seg(t, 50.6, 53.4)) * math.sin(t * 53)
        y = lerp(-200, 560, k) + 20 * seg(t, 50.6, 53.4)
        draw_cursor(frame, x, y)
        if t >= 50.6:
            beats = [50.6, 51.3, 51.9, 52.45, 52.95, 53.3]
            n = sum(1 for b in beats if t >= b)
            cam.update(z=1.0 + 0.025 * n, cx=560, cy=650)
    if t >= 51.0:
        a = seg(t, 51.0, 51.2)
        put_text(frame, "SUBMIT or SAVE?", 540, SUB_Y, 92, fill=(255, 255, 255), stroke=10, alpha=a,
                 scale=0.9 + 0.1 * ease_back(a))
        put_text(frame, "you decide  ·  Ep. 2", 540, SUB_Y + 100, 46, fill=(255, 226, 60), stroke=6,
                 alpha=seg(t, 51.4, 51.6))
    return frame


# ----------------------------------------------------------------- камера и кадр


def apply_cam(frame, cam):
    z = cam.get("z", 1.0)
    sh = cam.get("shake", 0.0)
    if z != 1.0 or sh > 0:
        ox = sh * math.sin(cam["t"] * 91) if sh else 0
        oy = sh * math.cos(cam["t"] * 77) if sh else 0
        z = max(z, 1.0 + sh * 2 / W)  # чтобы при тряске не было пустых краёв
        cw, ch = W / z, H / z
        cx = clamp(cam.get("cx", 540) + ox, cw / 2, W - cw / 2)
        cy = clamp(cam.get("cy", 960) + oy, ch / 2, H - ch / 2)
        frame = frame.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    fl = cam.get("flash", 0.0)
    if fl > 0:
        frame = Image.blend(frame, Image.new("RGB", frame.size, (255, 255, 255)), min(1, fl))
    return frame


def render(i):
    t = i / FPS
    cam = {"t": t}
    if t < 2.0:
        frame = scene_pack(t, t, cam, hook=True)
    elif t < 5.6:
        frame = scene_reveal(t, cam)
    elif t < 9.4:
        frame = scene_dex_close(t, cam)
    elif t < 21.5:
        frame = scene_room(t, cam)
    elif t < 38.8:
        frame = scene_cursor(t, cam)
    elif t < 43.5:
        frame = scene_brand(t, cam)
    elif t < 53.5:
        frame = scene_sbc(t, cam)
    else:
        frame = scene_pack(t, t - DUR, cam, hook=False)
    frame = apply_cam(frame, cam)
    draw_subs(frame, t)
    if not (30.45 <= t < 37.2 or t >= 43.6 and t < 53.5):  # не мешаем UI-панелям
        brand_tag(frame)
    return frame


# ----------------------------------------------------------------- звук

rng = np.random.default_rng(7)


def env_exp(n, rate):
    return np.exp(-np.arange(n) / SR * rate)


def osc(f, n, kind="sine", phase=0.0):
    if np.isscalar(f):
        ph = 2 * np.pi * f * np.arange(n) / SR + phase
    else:
        ph = 2 * np.pi * np.cumsum(f) / SR + phase
    if kind == "sine":
        return np.sin(ph)
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    raise ValueError(kind)


def lowpass(x, k=8):
    return np.convolve(x, np.ones(k) / k, mode="same")


def noise(n):
    return rng.uniform(-1, 1, n)


def s_boom(big=1.0):
    n = int(SR * 0.9)
    f = 40 + 110 * np.exp(-np.arange(n) / SR * 12)
    x = osc(f, n) * env_exp(n, 4.5)
    x[: int(SR * 0.02)] += noise(int(SR * 0.02)) * 0.6
    return np.tanh(x * 1.8 * big)


def s_whoosh(dur=0.35):
    n = int(SR * dur)
    w = np.sin(np.linspace(0, np.pi, n)) ** 2
    return lowpass(noise(n), 6) * w * 1.3


def s_riser(dur, f0=180, f1=1400, start=0.1, end=1.0):
    n = int(SR * dur)
    k = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** k
    x = 0.5 * osc(f, n, "saw") + 0.6 * lowpass(noise(n), 4)
    return lowpass(x, 3) * (start + (end - start) * k ** 2) * 0.5


def s_bell(f, dur=0.6, rate=6):
    n = int(SR * dur)
    x = osc(f, n) + 0.5 * osc(f * 2.01, n) + 0.25 * osc(f * 3.98, n)
    return x * env_exp(n, rate) / 1.75


def s_trombone():
    parts = []
    for f, d in ((293.7, 0.32), (277.2, 0.32), (261.6, 0.32), (246.9, 1.1)):
        n = int(SR * d)
        vib = 1 + (0.025 * np.sin(2 * np.pi * 6 * np.arange(n) / SR) if d > 1 else 0)
        x = lowpass(osc(f * vib, n, "saw"), 10)
        e = np.minimum(1, np.arange(n) / (SR * 0.03)) * np.minimum(1, (n - np.arange(n)) / (SR * 0.08))
        parts.append(x * e)
    return np.concatenate(parts) * 0.6


def s_thud():
    n = int(SR * 0.4)
    return np.tanh(osc(55 + 60 * env_exp(n, 20), n) * env_exp(n, 9) * 2) + lowpass(noise(n), 30) * env_exp(n, 25)


def s_fall():
    n = int(SR * 0.25)
    return osc(np.linspace(1400, 300, n), n) * 0.35


def s_click():
    n = int(SR * 0.04)
    return (noise(n) * env_exp(n, 200) + osc(3200, n) * env_exp(n, 120)) * 0.7


def s_tick():
    n = int(SR * 0.03)
    return osc(2400, n, "square") * env_exp(n, 160) * 0.25


def s_heart():
    n = int(SR * 0.5)
    x = np.zeros(n)
    for o, a in ((0, 1.0), (0.17, 0.7)):
        m = int(SR * 0.16)
        i0 = int(o * SR)
        x[i0:i0 + m] += np.tanh(osc(52 + 30 * env_exp(m, 30), m) * env_exp(m, 22) * 3) * a
    return x


def s_scratch():
    n = int(SR * 0.4)
    k = np.linspace(0, 1, n)
    f = 300 + 900 * np.abs(np.sin(k * np.pi * 2.2))
    return (0.6 * osc(f, n, "saw") * lowpass(noise(n), 3) + 0.4 * osc(f, n, "saw")) * np.sin(k * np.pi) * 0.7


def s_alarm(dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = np.where((t * 4).astype(int) % 2 == 0, 880, 660)
    return lowpass(osc(f, n, "square"), 6) * 0.25


def s_drone(dur):
    n = int(SR * dur)
    x = osc(55, n, "saw") + osc(55.6, n, "saw") + 0.5 * osc(82.4, n, "saw")
    x = lowpass(lowpass(x, 40), 40)
    e = np.minimum(1, np.arange(n) / (SR * 0.4)) * np.minimum(1, (n - np.arange(n)) / (SR * 0.2))
    return x * e * 0.35


def s_notif():
    return np.concatenate([s_bell(988, 0.13, 14), s_bell(1319, 0.5, 7)]) * 0.8


def s_jingle():
    """Фирменный звук «OVR 47»: три бронзовых колокола + удар."""
    out = np.zeros(int(SR * 1.4))
    for i, f in enumerate((659.3, 784.0, 1046.5)):
        b = s_bell(f, 1.0 if i == 2 else 0.4, 4 if i == 2 else 9)
        i0 = int(i * 0.12 * SR)
        out[i0:i0 + len(b)] += b * (1.0 if i == 2 else 0.8)
    bm = s_boom(0.8)
    out[: len(bm)] += bm * 0.7
    return out


def s_glasses():
    out = np.zeros(int(SR * 0.4))
    for o in (0.0, 0.12, 0.2):
        c = s_click()
        i0 = int(o * SR)
        out[i0:i0 + len(c)] += c * 0.8
    return out


def s_skid():
    n = int(SR * 0.4)
    k = np.linspace(0, 1, n)
    return lowpass(noise(n), 3) * (1 - k) * 0.6 + osc(np.linspace(900, 500, n), n, "square") * (1 - k) * 0.08


VOICE = {"dex": (300, "square"), "kai": (170, "saw"), "gaffer": (120, "saw")}


def s_voice(spk, a, b, text, out):
    """Мультяшный «бубнёж» в такт открывания рта (без TTS — это фишка стиля)."""
    base, kind = VOICE[spk]
    r = np.random.default_rng(int(a * 100))
    k = 0
    while True:
        t0 = a + k / 5.5
        if t0 >= b - 0.15:
            break
        f = base * r.uniform(0.85, 1.3) * (1.25 if text.isupper() or "!" in text else 1)
        n = int(SR * 0.085)
        x = osc(f * np.linspace(1.05, 0.95, n), n, kind) * 0.6 + osc(f * 2, n) * 0.3
        x = lowpass(x, 5) * np.sin(np.linspace(0, np.pi, n))
        if spk == "gaffer":
            x *= 1 + 0.3 * noise(n)
        add(out, t0, x * 0.33)
        k += 1


def music(total):
    """Фонк-петля 140 BPM: 808, клэп, хэты, ковбелл."""
    out = np.zeros(total)
    step = 60 / 140 / 4
    n808 = int(SR * 0.5)
    kick = np.tanh(osc(48 + 100 * env_exp(n808, 25), n808) * env_exp(n808, 5) * 2.2)
    nc = int(SR * 0.15)
    clap = lowpass(noise(nc), 2) * env_exp(nc, 28) * 0.6
    nh = int(SR * 0.05)
    hat = np.diff(noise(nh + 1)) * env_exp(nh, 90) * 0.25
    bells = {}
    root = 329.6
    pat = {0: 0, 3: 3, 6: 7, 8: 5, 11: 3, 14: 2}
    bar_shift = [0, 0, -2, 3]

    def cowbell(f):
        if f not in bells:
            n = int(SR * 0.22)
            x = osc(f, n, "square") + osc(f * 1.48, n, "square")
            bells[f] = lowpass(x, 4) * env_exp(n, 16) * 0.22
        return bells[f]

    s = 0
    while s * step < DUR:
        t0 = s * step
        kk = s % 16
        bar = (s // 16) % 4
        if kk in (0, 7, 10):
            add(out, t0, kick)
        if kk in (4, 12):
            add(out, t0, clap)
        if kk % 2 == 0:
            add(out, t0, hat)
        if kk in pat:
            add(out, t0, cowbell(round(root * 2 ** ((pat[kk] + bar_shift[bar]) / 12), 2)))
        s += 1
    return out


def add(out, t0, x, g=1.0):
    i0 = int(t0 * SR)
    if i0 >= len(out):
        return
    x = x[: len(out) - i0]
    out[i0:i0 + len(x)] += x * g


def make_audio(path):
    total = int(DUR * SR)
    sfx = np.zeros(total)
    vox = np.zeros(total)
    # A — хук (начало петли: райзер уже на пике)
    add(sfx, 0.0, s_riser(0.4, 900, 1400, 0.8, 1.0))
    add(sfx, 0.3, lowpass(noise(int(SR * 0.25)), 2) * env_exp(int(SR * 0.25), 12) * 0.6)
    add(sfx, 0.35, s_boom())
    add(sfx, 1.12, lowpass(noise(int(SR * 0.2)), 2) * env_exp(int(SR * 0.2), 14) * 0.5)
    add(sfx, 1.3, s_riser(0.7, 200, 1200, 0.1, 0.8))
    # B — прогулка: позиция / флаг / клуб / шлепок
    for tb in (2.0, 2.8, 3.6):
        add(sfx, tb, s_boom(0.9))
        add(sfx, tb - 0.15, s_whoosh(0.2), 0.6)
    add(sfx, 4.4, s_whoosh(0.3))
    add(sfx, 4.68, s_boom(1.3))
    add(sfx, 4.68, s_thud())
    add(sfx, 4.9, s_trombone(), 0.8)
    # C/D/E
    add(sfx, 9.35, s_whoosh(0.3))
    for i, f in enumerate((1568, 2093, 2637)):
        add(sfx, 9.95 + i * 0.06, s_bell(f, 0.5, 8), 0.45)
    add(sfx, 15.3, s_boom(1.0))
    add(sfx, 16.0, s_fall())
    add(sfx, 16.25, s_thud(), 1.2)
    add(sfx, 19.72, s_bell(1760, 0.8, 5), 0.6)
    # F — Курсор
    add(sfx, 21.5, s_alarm(1.6))
    add(sfx, 21.5, s_drone(8.8))
    add(sfx, 21.8, s_whoosh(0.6), 0.8)
    add(sfx, 22.65, s_click())
    add(sfx, 22.8, s_bell(1200, 0.15, 25), 0.5)
    add(sfx, 23.5, s_tick(), 1.5)
    for b in (28.0, 28.7, 29.4):
        add(sfx, b, s_heart(), 1.3)
    add(sfx, 30.15, s_tick(), 1.5)
    add(sfx, 30.28, s_click())
    add(sfx, 30.35, s_scratch())
    # G — статы
    k = 0
    while 30.9 + k * 0.05 < 31.6:
        add(sfx, 30.9 + k * 0.05, s_tick())
        k += 1
    add(sfx, 31.6, s_boom(1.4))
    add(sfx, 32.45, s_glasses())
    for tw in (37.0, 37.45, 37.9, 38.35):
        add(sfx, tw, s_whoosh(0.3), 1.1)
    add(sfx, 38.8, s_skid())
    # H — фирменная сцена
    add(sfx, 39.4, s_jingle(), 1.1)
    # I — SBC
    add(sfx, 43.6, s_notif())
    add(sfx, 43.5, s_drone(10.0))
    sec = 44.9
    while sec < 53.4:
        add(sfx, sec, s_tick(), 0.6)
        sec += 1.0
    for b in (50.6, 51.3, 51.9, 52.45, 52.95, 53.3):
        add(sfx, b, s_heart(), 1.3)
    # J — петля
    add(sfx, 53.5, s_riser(2.5, 180, 900, 0.05, 0.8))

    for a, b, spk, text in SUBS:
        s_voice(spk, a, b, text, vox)

    mus = music(total)
    tt = np.arange(total) / SR
    gate = np.zeros(total)
    for a, b, g in ((0.0, 4.6, 0.85), (9.5, 19.0, 0.5), (20.0, 21.5, 0.5), (31.6, 38.75, 0.75)):
        gate += g * np.clip((tt - a) / 0.02, 0, 1) * np.clip((b - tt) / 0.03, 0, 1)
    mix = 0.75 * sfx + 1.0 * vox + 0.5 * mus * gate
    mix = np.tanh(mix * 1.1)
    mix = mix / np.max(np.abs(mix)) * 0.92
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())


# ----------------------------------------------------------------- сборка


def render_bytes(i):
    return np.asarray(render(i)).tobytes()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--frames":
        for ts in sys.argv[2:]:
            render(int(float(ts) * FPS)).save(os.path.join(OUT_DIR, f"frame_{float(ts):05.2f}.png"))
        return
    wav = os.path.join(OUT_DIR, "ep01_audio.wav")
    mp4 = os.path.join(OUT_DIR, "ep01_walkout.mp4")
    make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-crf", "21",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, buf in enumerate(pool.imap(render_bytes, range(N), chunksize=4)):
            p.stdin.write(buf)
            if k % 150 == 0:
                print(f"frame {k}/{N}", flush=True)
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("done:", mp4)


if __name__ == "__main__":
    main()
