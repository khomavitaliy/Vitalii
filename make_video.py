"""Генерирует 10-секундное видео «Закат в горах» полностью процедурно.

Все кадры и звук создаются кодом (numpy + ffmpeg), без сторонних
изображений, музыки или шрифтов — поэтому видео свободно от авторских прав.

Запуск: python3 make_video.py  ->  sunset_10s.mp4
"""
import subprocess
import wave

import numpy as np

W, H, FPS, DUR = 1280, 720, 30, 10
N = FPS * DUR
SR = 44100
rng = np.random.default_rng(42)

y = np.linspace(0, 1, H)[:, None]
x = np.linspace(0, 1, W)[None, :]


def lerp(a, b, t):
    return a + (b - a) * t


def ridge(seed, base, amp, freqs):
    r = np.random.default_rng(seed)
    h = np.full(W, base)
    xs = np.arange(W) / W  # целые частоты -> бесшовный повтор
    for f in freqs:
        h += amp / f * np.sin(2 * np.pi * f * xs + r.uniform(0, 2 * np.pi))
    return h


ridges = [  # (высота хребта, цвет днём, цвет ночью)
    (ridge(1, 0.55, 0.10, [1, 2, 5, 12]), (120, 90, 140), (30, 25, 55)),
    (ridge(2, 0.66, 0.09, [1, 3, 7, 15]), (80, 55, 100), (18, 15, 38)),
    (ridge(3, 0.78, 0.07, [1, 3, 6, 19]), (40, 25, 55), (8, 6, 20)),
]

star_x = rng.integers(0, W, 400)
star_y = rng.integers(0, int(H * 0.6), 400)
star_b = rng.uniform(0.3, 1.0, 400)
star_ph = rng.uniform(0, 2 * np.pi, 400)


def frame(i):
    t = i / (N - 1)  # 0..1 по ходу видео
    # Небо: от тёплого заката к ночи
    top = lerp(np.array([255, 140, 90]), np.array([10, 12, 40]), t)
    bot = lerp(np.array([255, 210, 120]), np.array([60, 30, 80]), t)
    img = lerp(top, bot, y[..., None] ** 1.3) * np.ones((1, W, 1))

    # Солнце опускается за горы
    sx, sy = 0.5, lerp(0.45, 0.85, t)
    d = np.sqrt(((x - sx) * W / H) ** 2 + (y - sy) ** 2)
    glow = np.exp(-d * 6)[..., None] * (1 - t) * np.array([255, 160, 80]) * 0.6
    disc = (d < 0.07)[..., None] * np.array([255, 235, 180])
    img = np.where(d[..., None] < 0.07, disc, img + glow)

    # Звёзды проступают и мерцают
    vis = np.clip((t - 0.35) / 0.4, 0, 1)
    if vis > 0:
        tw = 0.6 + 0.4 * np.sin(star_ph + i * 0.3)
        img[star_y, star_x] = np.maximum(
            img[star_y, star_x], (255 * vis * star_b * tw)[:, None])

    # Горы с параллаксом
    rows = np.arange(H)[:, None]
    for k, (h, cday, cnight) in enumerate(ridges):
        shift = int(i * (k + 1) * 0.6)
        hh = np.roll(h, -shift)
        mask = rows >= (hh * H)[None, :]
        col = lerp(np.array(cday), np.array(cnight), t)
        img[mask] = col

    # Виньетка
    v = 1 - 0.35 * (((x - 0.5) ** 2 + (y - 0.5) ** 2) * 2)
    img = img * v[..., None]
    # Плавное появление и затухание
    fade = min(1, i / 15, (N - 1 - i) / 15)
    return np.clip(img * fade, 0, 255).astype(np.uint8)


def make_audio(path):
    tt = np.arange(SR * DUR) / SR
    notes = [220.0, 261.63, 329.63, 392.0]  # Am7 — спокойный пэд
    sig = sum(np.sin(2 * np.pi * f * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt))
              for f in notes)
    sig += 0.3 * np.sin(2 * np.pi * 110 * tt)
    env = np.minimum(1, np.minimum(tt / 2, (DUR - tt) / 2))
    sig = sig / np.max(np.abs(sig)) * env * 0.5
    data = (sig * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main():
    make_audio("audio.wav")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", "audio.wav",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-shortest", "sunset_10s.mp4"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(frame(i).tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    main()
