"""«RONALDO SAW YAMAL'S RATING 💀» — вертикальный TikTok-ролик 9:16.

Пародия, сгенерированная ИИ: карточки, графика, музыка и звуковые эффекты
создаются кодом (numpy + Pillow + ffmpeg), голоса — офлайн-моделью Kokoro TTS
(оригинальные синтетические голоса, НЕ клоны голосов футболистов).

Запуск:
    python3 make_tiktok.py <папка_с_kokoro> <папка_вывода>
В папке kokoro должны лежать kokoro-v1.0.onnx и voices-v1.0.bin
(github.com/thewh1teagle/kokoro-onnx, релиз model-files-v1.0).
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H, FPS = 1080, 1920, 30
SR = 44100
FONT_DIR = "/usr/share/fonts/opentype/inter/"
rng = np.random.default_rng(7)


def font(size, weight="ExtraBold"):
    return ImageFont.truetype(f"{FONT_DIR}InterDisplay-{weight}.otf", size)


# ---------------------------------------------------------------- реплики
VOICE_R = "am_fenrir"  # Роналду: взрослый, напористый
VOICE_Y = "am_puck"    # Ямаль: моложе, лёгкий, дерзкий
LINES = [  # (id, персонаж, текст для TTS, субтитр, скорость, желаемый старт)
    ("L1", "RONALDO", "Ninety-nine?!", "NINETY-NINE?!", 1.0, 0.45),
    ("L2", "RONALDO", "And I'm only ninety-one?!", "And I'm only NINETY-ONE?!", 1.05, 1.75),
    ("L3", "YAMAL", "The future is here, bro.", "The future is here, bro.", 1.0, 4.45),
    ("L4", "RONALDO", "Watch this.", "Watch this.", 0.9, 6.8),
    ("L5", "YAMAL", "Wait... what?!", "Wait... WHAT?!", 1.0, 13.5),
    ("L6", "RONALDO", "See-yooooo!", "SIUUU!", 0.8, 15.5),
]


def make_voices(kokoro_dir, out_dir):
    import soundfile as sf
    from kokoro_onnx import Kokoro

    k = Kokoro(os.path.join(kokoro_dir, "kokoro-v1.0.onnx"),
               os.path.join(kokoro_dir, "voices-v1.0.bin"))
    clips = {}
    os.makedirs(out_dir, exist_ok=True)
    for lid, who, text, _, speed, _ in LINES:
        s, sr = k.create(text, voice=VOICE_R if who == "RONALDO" else VOICE_Y,
                         speed=speed, lang="en-us")
        s = np.asarray(s, dtype=np.float64)
        # обрезаем тишину по краям
        nz = np.where(np.abs(s) > 0.01)[0]
        s = s[max(nz[0] - 240, 0): nz[-1] + 1200]
        # 24 кГц -> 44.1 кГц
        n = int(len(s) * SR / sr)
        s = np.interp(np.linspace(0, len(s) - 1, n), np.arange(len(s)), s)
        s = s / np.max(np.abs(s)) * 0.9
        clips[lid] = s
        sf.write(os.path.join(out_dir, f"{lid}_{who.lower()}.wav"), s, SR)
    return clips


# ---------------------------------------------------------------- аудио
def t_arr(d):
    return np.arange(int(d * SR)) / SR


def fft_filter(x, lo=0, hi=SR / 2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def noise(d):
    return rng.uniform(-1, 1, int(d * SR))


def sweep_filter(x, lo0, lo1, hi0, hi1, chunks=40):
    """Полосовой фильтр с плавно меняющейся полосой (по кускам)."""
    out = np.zeros_like(x)
    n = len(x)
    edges = np.linspace(0, n, chunks + 1).astype(int)
    for i in range(chunks):
        a, b = edges[i], edges[i + 1]
        k = i / max(chunks - 1, 1)
        pad = 2048
        seg = x[max(a - pad, 0): min(b + pad, n)]
        f = fft_filter(seg, lo0 + (lo1 - lo0) * k, hi0 + (hi1 - hi0) * k)
        off = a - max(a - pad, 0)
        out[a:b] = f[off: off + (b - a)]
    return out


def env_ad(n, a, d_curve):
    e = np.ones(n)
    na = max(int(a * SR), 1)
    e[:na] = np.linspace(0, 1, na)
    return e * d_curve


def sfx_ding():
    t = t_arr(0.6)
    s = np.zeros_like(t)
    for f0, dt in ((1318.5, 0.0), (1760.0, 0.09)):
        tt = np.clip(t - dt, 0, None)
        s += np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 9) * (t >= dt)
    return s * 0.5


def sfx_slam():
    t = t_arr(0.9)
    f = 90 * np.exp(-t * 6) + 38
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
    s += fft_filter(noise(0.9), 0, 3000) * np.exp(-t * 25) * 0.6
    return s


def saw(freq, t):
    ph = np.cumsum(np.broadcast_to(freq, t.shape)) / SR
    return 2 * (ph % 1) - 1


def sfx_sad_trombone():
    notes = [(233.1, 0.32), (220.0, 0.32), (207.7, 0.32), (196.0, 0.55)]
    out = []
    for i, (f0, d) in enumerate(notes):
        t = t_arr(d)
        f = f0 * (1 + (0.025 * np.sin(2 * np.pi * 6 * t) * (t > 0.15) if i == 3 else 0))
        s = saw(f, t) * 0.6 + np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, t.shape)) / SR) * 0.4
        e = np.minimum(1, t / 0.03) * np.minimum(1, (d - t) / 0.06)
        out.append(fft_filter(s, 0, 1800) * e)
    return np.concatenate(out) * 0.55


def sfx_riser(d):
    t = t_arr(d)
    k = t / d
    n = sweep_filter(noise(d), 300, 3000, 1200, 12000)
    tone = np.sin(2 * np.pi * np.cumsum(150 + 900 * k ** 2) / SR)
    return (n * 0.6 + tone * 0.35) * k ** 2.2


def sfx_heartbeat(n_beats, gap=0.62):
    out = np.zeros(int((n_beats * gap + 0.5) * SR))
    t = t_arr(0.25)
    thump = np.sin(2 * np.pi * (55 + 30 * np.exp(-t * 30)) * t) * np.exp(-t * 18)
    for i in range(n_beats):
        for off, g in ((0.0, 1.0), (0.19, 0.7)):
            a = int((i * gap + off) * SR)
            out[a:a + len(thump)] += thump * g
    return out


def sfx_kick():
    t = t_arr(0.4)
    f = 160 * np.exp(-t * 35) + 55
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)
    s += fft_filter(noise(0.4), 1500, 9000) * np.exp(-t * 90) * 1.2
    return s


def sfx_whoosh(d=0.7):
    t = t_arr(d)
    n = sweep_filter(noise(d), 400, 2500, 1500, 8000)
    return n * np.sin(np.pi * t / d) ** 2 * 1.3


def sfx_boom():
    t = t_arr(2.2)
    s = np.sin(2 * np.pi * np.cumsum(45 + 40 * np.exp(-t * 8)) / SR) * np.exp(-t * 2.2)
    s += fft_filter(noise(2.2), 20, 900) * np.exp(-t * 5) * 0.8
    return s


def sfx_crash(d=2.0):
    t = t_arr(d)
    return fft_filter(noise(d), 4000, 16000) * np.exp(-t * 2.5) * 0.7


def sfx_crowd(d=3.0):
    t = t_arr(d)
    n = fft_filter(noise(d), 300, 2500)
    n += fft_filter(noise(d), 120, 600) * 0.6
    return n * np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 1.2) * 0.8


def sfx_victory():
    out = np.zeros(int(2.4 * SR))
    stabs = [(0.0, 0.18, [261.6, 329.6, 392.0]), (0.2, 0.18, [293.7, 370.0, 440.0]),
             (0.4, 1.8, [392.0, 493.9, 587.3, 784.0])]
    for st, d, chord in stabs:
        t = t_arr(d)
        s = sum(saw(f * (1 + 0.003 * j), t) for j, f in enumerate(chord))
        e = np.minimum(1, t / 0.02) * np.exp(-t * (0.8 if d > 1 else 4))
        s = fft_filter(s, 0, 4500) * e / len(chord)
        a = int(st * SR)
        out[a:a + len(s)] += s
    return out * 0.9


def sfx_scratch():
    t = t_arr(0.45)
    f = 300 + 900 * np.abs(np.sin(2 * np.pi * 3.2 * t))
    s = saw(f, t) * 0.4 + fft_filter(noise(0.45), 800, 5000) * 0.5
    return fft_filter(s, 0, 5000) * np.minimum(1, (0.45 - t) / 0.1)


def sfx_bass_drop():
    t = t_arr(1.6)
    s = np.tanh(2.5 * np.sin(2 * np.pi * np.cumsum(60 * np.exp(-t * 1.5) + 32) / SR)) * np.exp(-t * 1.8)
    return s


def music_bed(dur, bpm=124):
    """Оригинальный трэп/хаус-бит: кик, клэп, хэты, бас, аккорды."""
    beat = 60 / bpm
    out = np.zeros(int(dur * SR))

    def add(sig, at, g=1.0):
        a = int(at * SR)
        if a >= len(out):
            return
        b = min(len(out), a + len(sig))
        out[a:b] += sig[:b - a] * g

    t = t_arr(0.3)
    kick = np.sin(2 * np.pi * np.cumsum(50 + 110 * np.exp(-t * 40)) / SR) * np.exp(-t * 10)
    clap = fft_filter(noise(0.2), 900, 6000) * np.exp(-t_arr(0.2) * 25)
    hat = fft_filter(noise(0.06), 7000, 16000) * np.exp(-t_arr(0.06) * 60)
    prog = [110.0, 87.3, 130.8, 98.0]  # A F C G (басы)
    n_beats = int(dur / beat) + 1
    for i in range(n_beats):
        tb = i * beat
        add(kick, tb, 0.9)
        if i % 2 == 1:
            add(clap, tb, 0.45)
        add(hat, tb + beat / 2, 0.25)
        add(hat, tb, 0.12)
        root = prog[(i // 4) % 4]
        tt = t_arr(beat * 0.9)
        bass = np.tanh(1.8 * np.sin(2 * np.pi * root / 2 * tt)) * np.exp(-tt * 3)
        add(bass, tb + beat * 0.5, 0.35)
        if i % 4 == 0:
            ct = t_arr(beat * 3.8)
            ch = sum(saw(root * m, ct) for m in (2, 2.52, 3, 4))
            ch = fft_filter(ch, 0, 2200) * np.minimum(1, ct / 0.05) * np.exp(-ct * 0.6) / 4
            add(ch, tb, 0.18)
    return out


# ---------------------------------------------------------------- графика
def lerp(a, b, k):
    return a + (b - a) * k


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out_cubic(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x, s=1.9):
    x = clamp01(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def vgrad(w, h, c0, c1):
    k = np.linspace(0, 1, h)[:, None, None]
    a = np.array(c0, float)[None, None, :]
    b = np.array(c1, float)[None, None, :]
    return np.broadcast_to(a + (b - a) * k, (h, w, 3)).astype(np.uint8)


CW, CH = 600, 860
SHIELD = [(46, 0), (554, 0), (600, 46), (600, 690), (300, 860), (0, 690), (0, 46)]


def shield_mask(inset=0):
    m = Image.new("L", (CW, CH), 0)
    cx, cy = CW / 2, CH / 2
    pts = [(cx + (x - cx) * (1 - inset / 300), cy + (y - cy) * (1 - inset / 430)) for x, y in SHIELD]
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def draw_silhouette(d, x, y, s, col, hair):
    d.ellipse([x - 70 * s, y + 230 * s, x + 70 * s, y + 360 * s], fill=col)  # шея/тень
    d.rounded_rectangle([x - 150 * s, y + 250 * s, x + 150 * s, y + 420 * s], 70 * s, fill=col)
    d.ellipse([x - 82 * s, y + 40 * s, x + 82 * s, y + 250 * s], fill=col)
    if hair == "quiff":
        d.ellipse([x - 84 * s, y + 18 * s, x + 70 * s, y + 110 * s], fill=col)
        d.polygon([(x - 30 * s, y + 30 * s), (x + 50 * s, y - 6 * s), (x + 80 * s, y + 60 * s)], fill=col)
    else:
        for dx, dy in ((-60, 60), (-30, 32), (5, 22), (40, 32), (66, 62), (-75, 100), (78, 100)):
            d.ellipse([x + (dx - 30) * s, y + (dy - 30) * s, x + (dx + 30) * s, y + (dy + 30) * s], fill=col)


def make_card(name, rating, pos, nation, stats, style):
    if style == "gold":
        top, bot, txt, sil = (250, 222, 140), (190, 140, 50), (60, 40, 10), (160, 115, 40)
        edge = (255, 240, 190)
    elif style == "neon":
        top, bot, txt, sil = (20, 40, 110), (5, 10, 40), (235, 250, 255), (40, 80, 170)
        edge = (60, 240, 255)
    else:  # icon / GOAT
        top, bot, txt, sil = (60, 20, 80), (12, 5, 18), (255, 225, 140), (110, 60, 140)
        edge = (255, 205, 90)
    body = Image.fromarray(vgrad(CW, CH, top, bot)).convert("RGBA")
    d = ImageDraw.Draw(body)
    # диагональные блики
    for i in range(6):
        x0 = -200 + i * 170
        d.polygon([(x0, 0), (x0 + 60, 0), (x0 + 360, CH), (x0 + 300, CH)],
                  fill=tuple(min(255, c + 18) for c in top) + (255,))
    draw_silhouette(d, 390, 70, 1.0, sil, "quiff" if name == "RONALDO" else "curly")
    d.text((48, 40), str(rating), font=font(170, "Black"), fill=txt)
    d.text((58, 220), pos, font=font(56, "Bold"), fill=txt)
    fx, fy = 62, 300
    if nation == "POR":
        d.rectangle([fx, fy, fx + 44, fy + 66], fill=(0, 102, 0))
        d.rectangle([fx + 44, fy, fx + 110, fy + 66], fill=(210, 16, 52))
        d.ellipse([fx + 30, fy + 20, fx + 58, fy + 48], fill=(255, 215, 0))
    else:
        d.rectangle([fx, fy, fx + 110, fy + 66], fill=(170, 21, 27))
        d.rectangle([fx, fy + 16, fx + 110, fy + 50], fill=(241, 191, 0))
    d.line([(60, 490), (540, 490)], fill=txt, width=3)
    nf = font(78, "Black")
    tw = d.textlength(name, font=nf)
    d.text(((CW - tw) / 2, 496), name, font=nf, fill=txt)
    d.line([(110, 592), (490, 592)], fill=txt, width=2)
    sf_ = font(40, "Bold")
    for i, (k, v) in enumerate(stats):
        col, row = i // 3, i % 3
        x = 120 + col * 200
        y = 602 + row * 50
        vf = font(42, "Black")
        d.text((x + 76 - d.textlength(str(v), font=vf), y), f"{v}", font=vf, fill=txt)
        d.text((x + 88, y), k, font=sf_, fill=txt)
    card = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    card.paste(Image.new("RGBA", (CW, CH), edge + (255,)), (0, 0), shield_mask())
    card.paste(body, (0, 0), shield_mask(14))
    return card


def glow(img, color, radius=40, strength=1.6):
    pad = radius * 2
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    big_a = Image.new("L", out.size, 0)
    big_a.paste(img.split()[3], (pad, pad))
    big_a = big_a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * strength)))
    gl = Image.new("RGBA", out.size, color + (255,))
    gl.putalpha(big_a)
    out = Image.alpha_composite(out, gl)
    out.alpha_composite(img, (pad, pad))
    return out


def locker_bg():
    img = Image.fromarray(vgrad(W, H, (24, 32, 52), (8, 10, 20))).convert("RGBA")
    d = ImageDraw.Draw(img)
    for i in range(6):
        x = 20 + i * 180
        d.rounded_rectangle([x, 160, x + 160, 1240], 10, fill=(34, 46, 74), outline=(60, 78, 112), width=4)
        for v in range(5):
            d.rectangle([x + 40, 230 + v * 22, x + 120, 236 + v * 22], fill=(20, 28, 46))
        d.rectangle([x + 128, 650, x + 138, 760], fill=(150, 160, 180))
        d.rounded_rectangle([x + 30, 330, x + 130, 380], 6, fill=(22, 30, 50))
        d.text((x + 58, 333), str([7, 10, 4, 19, 11, 9][i]), font=font(38, "Bold"), fill=(170, 180, 205))
    d.rectangle([0, 1240, W, 1300], fill=(70, 48, 30))
    d.rectangle([0, 1300, W, H], fill=(16, 18, 26))
    for x in range(-400, W + 400, 120):  # плитка пола
        d.line([(540 + (x - 540) * 0.35, 1300), (x, H)], fill=(26, 30, 42), width=3)
    # лампы
    lights = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lights)
    for x in (270, 810):
        ld.ellipse([x - 300, -200, x + 300, 400], fill=(255, 240, 210, 70))
    img = Image.alpha_composite(img, lights.filter(ImageFilter.GaussianBlur(80)))
    return vignette(img, 0.75)


def pitch_bg():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    hz = 260
    # трибуны
    d.rectangle([0, 0, W, hz], fill=(12, 14, 24))
    for i in range(1400):
        x, y = rng.integers(0, W), rng.integers(0, hz - 10)
        c = int(rng.integers(40, 110))
        d.ellipse([x, y, x + 5, y + 5], fill=(c, c, c + 20))
    # газон с полосами в перспективе
    for i in range(14):
        y0 = hz + (H - hz) * (i / 14) ** 1.6
        y1 = hz + (H - hz) * ((i + 1) / 14) ** 1.6
        g = (34, 120, 52) if i % 2 else (40, 138, 60)
        d.rectangle([0, y0, W, y1], fill=g)
    # ворота
    gx0, gx1, gy0, gy1 = 230, 850, 280, 560
    for k in range(0, 21):
        x = gx0 + (gx1 - gx0) * k / 20
        d.line([(x, gy0), (x, gy1)], fill=(225, 225, 225, 255), width=2)
    for k in range(0, 11):
        y = gy0 + (gy1 - gy0) * k / 10
        d.line([(gx0, y), (gx1, y)], fill=(225, 225, 225, 255), width=2)
    d.rectangle([gx0 - 14, gy0 - 14, gx1 + 14, gy0], fill=(250, 250, 250))
    d.rectangle([gx0 - 14, gy0, gx0, gy1], fill=(250, 250, 250))
    d.rectangle([gx1, gy0, gx1 + 14, gy1], fill=(250, 250, 250))
    # разметка
    d.line([(60, gy1 + 10), (W - 60, gy1 + 10)], fill=(230, 240, 230), width=6)
    d.polygon([(130, gy1 + 10), (950, gy1 + 10), (1060, 1000), (20, 1000)], outline=(230, 240, 230))
    d.line([(20, 1000), (1060, 1000)], fill=(230, 240, 230), width=6)
    d.ellipse([515, 1470, 565, 1500], fill=(230, 240, 230))
    lights = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lights).ellipse([140, -300, 940, 500], fill=(255, 255, 230, 90))
    img = Image.alpha_composite(img, lights.filter(ImageFilter.GaussianBlur(90)))
    return vignette(img, 0.85)


def vignette(img, strength):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    k = np.clip(1 - strength * np.clip(r - 0.45, 0, None) * 1.6, 0, 1)
    a = np.asarray(img.convert("RGB"), float) * k[..., None]
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


def make_ball(size=170):
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, s - 1, s - 1], fill=(250, 250, 250))
    c = s / 2

    def pent(cx, cy, r, rot):
        return [(cx + r * math.cos(rot + i * 2 * math.pi / 5), cy + r * math.sin(rot + i * 2 * math.pi / 5)) for i in range(5)]

    d.polygon(pent(c, c, s * 0.16, -math.pi / 2), fill=(20, 20, 20))
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        px, py = c + math.cos(a) * s * 0.42, c + math.sin(a) * s * 0.42
        d.polygon(pent(px, py, s * 0.13, a + math.pi), fill=(20, 20, 20))
        d.line([(c + math.cos(a) * s * 0.16, c + math.sin(a) * s * 0.16), (px, py)], fill=(60, 60, 60), width=10)
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).ellipse([0, 0, s - 1, s - 1], fill=255)
    shade = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shade).ellipse([s * 0.25, s * 0.25, s * 1.4, s * 1.4], fill=(0, 0, 0, 90))
    img = Image.alpha_composite(img, shade.filter(ImageFilter.GaussianBlur(s * 0.12)))
    img.putalpha(m)
    return img.resize((size, size), Image.LANCZOS)


def text_img(text, size, fill=(255, 255, 255), stroke=8, stroke_fill=(0, 0, 0), weight="Black"):
    f = font(size, weight)
    bb = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=f, stroke_width=stroke)
    img = Image.new("RGBA", (bb[2] - bb[0] + 20, bb[3] - bb[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10 - bb[0], 10 - bb[1]), text, font=f, fill=fill,
                             stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def caption_img(who, text):
    col = (225, 30, 50) if who == "RONALDO" else (30, 120, 235)
    tag = text_img(who, 40, stroke=0, weight="Black")
    body = text_img(text, 74 if len(text) < 20 else 64, stroke=9)
    w = max(body.width, tag.width + 60) + 40
    img = Image.new("RGBA", (w, body.height + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tx = (w - tag.width - 40) // 2
    d.rounded_rectangle([tx, 0, tx + tag.width + 40, 62], 18, fill=col + (255,))
    img.alpha_composite(tag, (tx + 20, 2))
    img.alpha_composite(body, ((w - body.width) // 2, 66))
    return img


def ai_badge():
    t = text_img("AI PARODY · NOT REAL", 34, stroke=0, weight="Bold")
    img = Image.new("RGBA", (t.width + 40, t.height + 16), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, img.width - 1, img.height - 1], 22, fill=(0, 0, 0, 150),
                                          outline=(255, 255, 255, 120), width=2)
    img.alpha_composite(t, (20, 8))
    return img


def rays(color, n=14):
    s = 2400
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    for i in range(n):
        a0 = i * 2 * math.pi / n
        a1 = a0 + math.pi / n * 0.6
        d.polygon([(c, c), (c + math.cos(a0) * s, c + math.sin(a0) * s), (c + math.cos(a1) * s, c + math.sin(a1) * s)],
                  fill=color + (70,))
    return img.filter(ImageFilter.GaussianBlur(6))


def place(frame, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    im = img
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05:
        im = im.rotate(rot, resample=Image.BILINEAR, expand=True)
    if alpha < 1:
        a = im.split()[3].point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    l, t_ = max(-x, 0), max(-y, 0)
    r, b = min(im.width, frame.width - x), min(im.height, frame.height - y)
    if r <= l or b <= t_:
        return
    frame.alpha_composite(im.crop((l, t_, r, b)), (x + l, y + t_))


def desaturate(img, k):
    g = ImageOps.grayscale(img.convert("RGB")).convert("RGB")
    out = Image.blend(img.convert("RGB"), g, k).convert("RGBA")
    out.putalpha(img.split()[3])
    return out


def crack(img):
    out = img.copy()
    d = ImageDraw.Draw(out)
    r = np.random.default_rng(3)
    for _ in range(5):
        x, y = CW * 0.5 + r.uniform(-60, 60), CH * 0.35 + r.uniform(-60, 60)
        for _ in range(7):
            nx, ny = x + r.uniform(-90, 90), y + r.uniform(20, 110)
            d.line([(x, y), (nx, ny)], fill=(15, 15, 15, 255), width=6)
            x, y = nx, ny
    return out


# ---------------------------------------------------------------- сборка
def main(kokoro_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    vdir = os.path.join(out_dir, "voices")
    clips = make_voices(kokoro_dir, vdir)
    T = {lid: (start, start + len(clips[lid]) / SR) for lid, *_, start in LINES}
    for lid, (a, b) in T.items():
        print(f"{lid}: {a:.2f}-{b:.2f}")

    tKick = T["L4"][1] + 2.2          # пауза-напряжение после «Watch this»
    tGoal = tKick + 0.55
    tReveal = tKick + 1.45
    tSplit2 = T["L5"][0] - 0.5
    tSiu = T["L6"][0] - 0.25
    tEnd = T["L6"][1] + 2.8
    assert tReveal + 1.2 < tSplit2, (tReveal, tSplit2)
    DUR = tEnd
    print(f"duration {DUR:.2f}s, kick {tKick:.2f}, reveal {tReveal:.2f}")

    # ---------- аудио
    N = int(DUR * SR)
    music = np.zeros(N)
    bed = music_bed(DUR)
    m_env = np.ones(N)
    tt = np.arange(N) / SR
    m_env[(tt > T["L4"][0] - 0.2) & (tt < tReveal)] = 0.0   # музыка уходит перед ударом
    m_env[tt < 0.35] = 0
    m_env = np.convolve(m_env, np.ones(2000) / 2000, mode="same")
    music += bed * m_env * 0.32
    voice = np.zeros(N)
    for lid, (a, b) in T.items():
        s = clips[lid] * (1.15 if lid == "L6" else 1.0)
        i = int(a * SR)
        voice[i:i + len(s)] += s[:N - i]
    duck = np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(6000) / 6000, mode="same")
    music *= 1 - 0.65 * np.clip(duck * 3, 0, 1)
    fx = np.zeros(N)

    def add(sig, at, g):
        i = int(at * SR)
        if i < N:
            fx[i:i + len(sig)] += sig[:N - i] * g

    add(sfx_ding(), 0.0, 0.5)
    add(sfx_slam(), 0.15, 0.7)
    add(sfx_whoosh(0.45), T["L2"][0] - 0.55, 0.35)
    add(sfx_slam(), T["L2"][0] - 0.15, 0.4)
    add(sfx_sad_trombone(), T["L2"][1] + 0.05, 0.4)
    add(sfx_whoosh(0.5), T["L3"][0] - 0.45, 0.3)
    add(sfx_boom(), T["L4"][0] - 0.3, 0.35)
    add(sfx_heartbeat(4), T["L4"][1] + 0.1, 0.55)
    add(sfx_riser(tKick - T["L4"][1]), T["L4"][1], 0.45)
    add(sfx_kick(), tKick, 0.9)
    add(sfx_whoosh(0.6), tKick + 0.02, 0.6)
    add(sfx_crowd(3.2), tGoal, 0.35)
    add(sfx_boom(), tGoal, 0.55)
    add(sfx_slam(), tReveal, 0.8)
    add(sfx_victory(), tReveal, 0.42)
    add(sfx_crash(), tReveal, 0.35)
    add(sfx_scratch(), T["L5"][0] - 0.5, 0.35)
    add(sfx_bass_drop(), T["L6"][0], 0.55)
    add(sfx_crash(2.5), T["L6"][0], 0.3)
    add(sfx_crowd(2.5), T["L6"][0] + 0.2, 0.3)
    fx = fx * 0.9

    mix = voice * 1.0 + music + fx
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix = mix / np.max(np.abs(mix)) * 0.95
    stems = {"mix": mix, "music": music, "sfx": fx, "dialogue": voice}
    for name, sig in stems.items():
        sig = sig / max(1e-9, np.max(np.abs(sig))) * 0.95 if name != "mix" else sig
        st = np.repeat(sig[:, None], 2, axis=1)
        path = os.path.join(out_dir, "audio_" + name + ".wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((st * 32767).astype("<i2").tobytes())

    # ---------- субтитры (SRT)
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    with open(os.path.join(out_dir, "subtitles.srt"), "w") as f:
        for i, (lid, who, _, sub, *_r) in enumerate(LINES, 1):
            a, b = T[lid]
            f.write(f"{i}\n{ts(a - 0.05)} --> {ts(b + 0.35)}\n{who.title()}: {sub}\n\n")
        f.write(f"{len(LINES) + 1}\n{ts(0.0)} --> {ts(DUR)}\nAI PARODY · NOT REAL\n\n")

    # ---------- ассеты
    yamal = make_card("YAMAL", 99, "RW", "ESP",
                      [("PAC", 97), ("SHO", 95), ("PAS", 98), ("DRI", 99), ("DEF", 45), ("PHY", 80)], "neon")
    ron91 = make_card("RONALDO", 91, "ST", "POR",
                      [("PAC", 84), ("SHO", 93), ("PAS", 80), ("DRI", 86), ("DEF", 34), ("PHY", 78)], "gold")
    ron100 = make_card("RONALDO", 100, "GOAT", "POR",
                       [("PAC", 99), ("SHO", 100), ("PAS", 99), ("DRI", 99), ("DEF", 99), ("PHY", 99)], "icon")
    yamal_glow = glow(yamal, (60, 240, 255), 38)
    ron100_glow = glow(ron100, (255, 200, 80), 50, 2.0)
    yamal_broken = desaturate(crack(yamal), 0.75)
    locker, pitch = locker_bg(), pitch_bg()
    ball = make_ball()
    badge = ai_badge()
    title1 = text_img("RONALDO SAW", 80)
    title2 = text_img("YAMAL'S RATING", 80, fill=(255, 220, 70))
    end1 = text_img("WHO'S THE REAL GOAT?", 72, fill=(255, 220, 70))
    end2 = text_img("COMMENT BELOW", 56)
    goal_txt = text_img("GOOOAL!", 140, fill=(255, 255, 255), stroke=12)
    siu = text_img("SIUUU!", 220, fill=(255, 225, 90), stroke=16)
    new_rating = text_img("NEW RATING UNLOCKED", 64, fill=(255, 225, 90))
    rays_gold = rays((255, 200, 90))
    caps = {lid: caption_img(who, sub) for lid, who, _, sub, *_r in LINES}
    conf = [(rng.uniform(0, W), rng.uniform(-900, -50), rng.uniform(250, 520), rng.uniform(0, 360),
             rng.uniform(-300, 300), tuple(int(c) for c in rng.choice(
                 [(255, 215, 0), (255, 255, 255), (225, 30, 50), (40, 170, 90), (255, 140, 0)])))
            for _ in range(160)]

    def shake(t0, t, amp=26, decay=7):
        if t < t0:
            return 0, 0
        e = amp * math.exp(-(t - t0) * decay)
        return e * math.sin(t * 91), e * math.cos(t * 77)

    def frame_at(t):
        sx = sy = 0.0
        for t0, amp in ((0.15 + 0.3, 30), (T["L2"][0] - 0.15, 18), (tKick, 22), (tGoal, 34),
                        (tReveal + 0.25, 40), (T["L6"][0], 36)):
            dx, dy = shake(t0, t, amp)
            sx, sy = sx + dx, sy + dy

        if t < tKick - 0.0 and t < T["L4"][0] - 0.25:
            fr = locker.copy()
        elif t < tReveal:
            fr = pitch.copy()
        else:
            fr = locker.copy()

        # ----- сцена 1–2: карточки
        if t < T["L4"][0] - 0.25:
            k_in = ease_out_back((t - 0.15) / 0.35)
            ys = lerp(2.4, 1.0, k_in) if t >= 0.15 else 0
            sp = ease_in_out((t - (T["L2"][0] - 0.55)) / 0.45)   # сплит
            fo = ease_in_out((t - (T["L3"][0] - 0.45)) / 0.45)   # фокус на Ямале
            yx = lerp(lerp(540, 292, sp), 540, fo)
            yy = lerp(lerp(860, 880, sp), 820, fo)
            ysc = lerp(lerp(ys, 0.78, sp), 0.98 + 0.02 * math.sin(t * 6), fo) if t >= 0.15 else 0
            rx = lerp(lerp(1500, 790, sp), -500, fo)
            wob = 0
            if T["L2"][1] < t < T["L2"][1] + 1.6:
                wob = 6 * math.sin((t - T["L2"][1]) * 18) * math.exp(-(t - T["L2"][1]) * 2)
            if sp > 0 and fo < 1:
                place(fr, ron91, rx + sx, 880 + sy, 0.78, wob)
                if t > T["L2"][1] and fo < 0.5:
                    place(fr, text_img("91?!", 110, fill=(255, 60, 60)), rx + sx, 470 + sy,
                          ease_out_back((t - T["L2"][1]) / 0.3))
            if t >= 0.15:
                im = yamal_glow if fo > 0 else yamal
                place(fr, im, yx + sx, yy + sy, ysc * CW / im.width)
                if 0.5 < t and sp < 0.5:
                    place(fr, text_img("99?!", 130, fill=(60, 240, 255)), 850 + sx, 480 + sy,
                          ease_out_back((t - T["L1"][0]) / 0.3) * (1 - sp * 2), rot=10)
        # ----- сцена 3: напряжение
        elif t < tReveal:
            cam = 1 + 0.12 * ease_in_out((t - T["L4"][0]) / max(0.1, tKick - T["L4"][0]))
            kb = clamp01((t - tKick) / 0.55)
            if t < tKick:
                place(fr, ron91, 200 + sx, 880 + sy, 0.42 * cam, 8)
                place(fr, ball, 540 + sx, 1480 + sy, cam * (1 + 0.04 * math.sin(t * 10)))
                # красная пульсирующая виньетка
                pulse = 0.5 + 0.5 * math.sin((t - T["L4"][1]) * 2 * math.pi / 0.62)
                if t > T["L4"][1]:
                    ov = Image.new("RGBA", (W, H), (150, 0, 0, int(55 * pulse)))
                    fr = Image.alpha_composite(fr, ov)
            else:
                e = ease_out_cubic(kb)
                bx, by = lerp(540, 790, e), lerp(1480, 380, e) - 260 * math.sin(math.pi * e) * 0.5
                for j in range(1, 7):  # шлейф
                    e2 = ease_out_cubic(max(0, kb - j * 0.04))
                    tx, ty = lerp(540, 790, e2), lerp(1480, 380, e2) - 260 * math.sin(math.pi * e2) * 0.5
                    place(fr, ball, tx + sx, ty + sy, lerp(1, 0.38, e2), alpha=0.35 - j * 0.05)
                place(fr, ball, bx + sx, by + sy, lerp(1, 0.38, e), rot=-t * 900)
                if t >= tGoal:
                    g = clamp01((t - tGoal) / 0.25)
                    place(fr, goal_txt, 540 + sx, 860 + sy, ease_out_back(g))
                    fl = max(0.0, 1 - (t - tGoal) / 0.25)
                    if fl > 0:
                        fr = Image.alpha_composite(fr, Image.new("RGBA", (W, H), (255, 255, 255, int(200 * fl))))
        # ----- сцена 5–7: карточка 100
        else:
            tr = t - tReveal
            rot_rays = rays_gold.rotate(tr * 25, resample=Image.BILINEAR)
            place(fr, rot_rays, 540, 840, 1.0, alpha=clamp01(tr / 0.3))
            s_in = lerp(2.6, 1.0, ease_out_back(tr / 0.4))
            sp2 = ease_in_out((t - tSplit2) / 0.4)
            back = ease_in_out((t - tSiu) / 0.3)
            pulse = 1 + 0.04 * math.sin(t * 9) if t > T["L6"][0] else 1
            cx = lerp(lerp(540, 770, sp2), 540, back)
            cy = lerp(lerp(840, 860, sp2), 800, back)
            cs = lerp(lerp(s_in, 0.72, sp2), 1.0, back) * pulse
            if sp2 > 0 and back < 1:
                ya = 1 - back
                place(fr, yamal_broken, lerp(-400, 285, sp2) + sx * 1.6, 930 + sy * 1.6, 0.6, 4 * math.sin(t * 40) * (t > T["L5"][0]), alpha=ya)
            place(fr, ron100_glow, cx + sx, cy + sy, cs * CW / ron100_glow.width)
            if tr < 1.6 and sp2 == 0:
                place(fr, new_rating, 540 + sx, 250 + sy, ease_out_back((tr - 0.3) / 0.3))
            fl = max(0.0, 1 - tr / 0.35)
            if fl > 0:
                fr = Image.alpha_composite(fr, Image.new("RGBA", (W, H), (255, 255, 255, int(255 * fl))))
            # конфетти
            cd = ImageDraw.Draw(fr)
            for (x0, y0, vy, a0, va, col) in conf:
                y = y0 + vy * tr
                if -20 < y < H:
                    x = x0 + 30 * math.sin(tr * 3 + a0)
                    a = math.radians(a0 + va * tr)
                    dx, dy = 12 * math.cos(a), 7 * math.sin(a)
                    cd.polygon([(x - dx, y - dy), (x + dy, y - dx), (x + dx, y + dy), (x - dy, y + dx)], fill=col)
            if t >= T["L6"][0]:
                ks = ease_out_back((t - T["L6"][0]) / 0.3, 2.5)
                place(fr, siu, 540 + sx, 1420 + sy, ks * (1 + 0.03 * math.sin(t * 12)), rot=-6)
            if t >= T["L6"][1] + 0.4:
                ke = ease_out_back((t - T["L6"][1] - 0.4) / 0.35)
                place(fr, end1, 540, 230, ke)
                place(fr, end2, 540, 320, ke)

        # ----- общий слой: заголовок, субтитры, бейдж
        if t < T["L4"][0] - 0.25:
            k = ease_out_back((t - 0.05) / 0.3)
            if T["L3"][0] - 0.45 > t:
                place(fr, title1, 540, 250, k)
                place(fr, title2, 540, 345, k)
        for lid, who, *_r in LINES:
            a, b = T[lid]
            if lid == "L6":
                continue
            if a - 0.05 <= t <= b + 0.35:
                k = ease_out_back((t - a + 0.05) / 0.18)
                cy = 1430 if not (lid in ("L4",)) else 1700
                place(fr, caps[lid], 540, cy, k)
        place(fr, badge, 40 + badge.width / 2, 120 + badge.height / 2)
        return fr.convert("RGB")

    # ---------- рендер
    if os.environ.get("PREVIEW"):  # PREVIEW="0.5,3,9" — только кадры-превью
        for x in os.environ["PREVIEW"].split(","):
            frame_at(float(x)).resize((540, 960)).save(os.path.join(out_dir, f"preview_{float(x):05.2f}.png"))
        return
    video = os.path.join(out_dir, "ronaldo_yamal_rating_9x16.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", os.path.join(out_dir, "audio_mix.wav"),
           "-af", "loudnorm=I=-14:TP=-1.0:LRA=11",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart",
           video]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(DUR * FPS)
    for i in range(nf):
        t = i / FPS
        fr = frame_at(t)
        p.stdin.write(fr.tobytes())
        if i == int((tReveal + 0.9) * FPS):
            fr.save(os.path.join(out_dir, "cover.jpg"), quality=92)
        if i % 60 == 0:
            print(f"frame {i}/{nf}", flush=True)
    p.stdin.close()
    p.wait()
    with open(os.path.join(out_dir, "timeline.txt"), "w") as f:
        for lid, (a, b) in T.items():
            f.write(f"{lid} {a:.2f} {b:.2f}\n")
        f.write(f"kick {tKick:.2f}\ngoal {tGoal:.2f}\nreveal {tReveal:.2f}\nend {DUR:.2f}\n")
    print("done", video)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
