# RONALDO SAW YAMAL'S RATING 💀

AI-пародия для футбольного TikTok. Формат 9:16, 1080×1920, 30 fps, длительность 19,1 с.
Вымышленная ситуация. Голоса синтетические и оригинальные, это не клоны и не записи футболистов.

## Что в папке

| Файл | Что это |
|---|---|
| `ronaldo_yamal_rating_9x16.mp4` | Готовый ролик: графика, озвучка, музыка, SFX, вшитые субтитры, плашка «AI PARODY · NOT REAL» |
| `cover.jpg` | Обложка (кадр с карточкой 100) |
| `subtitles.srt` | Субтитры с таймкодами |
| `voices/L1…L6_*.wav` | Каждая реплика отдельным файлом (44,1 кГц) |
| `audio_dialogue.wav`, `audio_music.wav`, `audio_sfx.wav` | Стемы для пересведения |
| `audio_mix.wav` | Итоговый микс |
| `make_tiktok.py` | Генератор: пересобирает весь ролик одной командой |

## Сценарий с таймкодами

| Время | Сцена | Картинка | Звук | Реплика |
|---|---|---|---|---|
| 0.00–0.45 | **Хук** | Карточка YAMAL 99 влетает в кадр с тряской, сверху заголовок «RONALDO SAW YAMAL'S RATING» | Уведомление телефона, удар | |
| 0.45–1.25 | Шок | Стикер «99?!» | | **Ronaldo:** «NINETY-NINE?!» |
| 1.30–3.00 | Сравнение | Рядом выезжает карточка RONALDO 91, она качается | Свист, удар, затем грустный тромбон | **Ronaldo:** «And I'm only NINETY-ONE?!» |
| 4.00–5.70 | Провокация | Карточка Ямаля в центре, неоновое свечение | Свист | **Yamal:** «The future is here, bro.» |
| 6.50–9.80 | Напряжение | Поле, ворота, мяч на точке, красная пульсация | Музыка пропадает, сердцебиение, нарастающий райзер | **Ronaldo:** «Watch this.» |
| 9.81–10.36 | Удар | Мяч со шлейфом летит в девятку | Удар по мячу, свист мяча | |
| 10.36–11.26 | Гол | «GOOOAL!», вспышка | Бум, рёв трибун | |
| 11.26–13.30 | **Поворот** | Белая вспышка, карточка RONALDO 100 «GOAT», лучи, конфетти, «NEW RATING UNLOCKED» | Удар, победные фанфары, тарелка | |
| 13.00–14.30 | Реакция | Карточка Ямаля трескается и сереет, трясётся | Скрэтч пластинки | **Yamal:** «Wait… WHAT?!» |
| 15.50–16.30 | Финал | Огромное «SIUUU!», карточка 100 пульсирует | Бас-дроп, тарелка, трибуны | **Ronaldo:** «SIUUU!» |
| 16.70–19.10 | Концовка | «WHO'S THE REAL GOAT? COMMENT BELOW» | Музыка | |

## Голоса

- Роналду: Kokoro `am_fenrir`, взрослый и напористый.
- Ямаль: Kokoro `am_puck`, моложе и легче.

Ограничение: Kokoro передаёт эмоции слабо, реплики звучат ровнее, чем у живого актёра. Для более сильной игры можно переозвучить те же реплики в ElevenLabs (Voice Design, оригинальный голос, не клон) и заменить файлы из `voices/` в CapCut по тем же таймкодам.

## Промпты для AI-видео (если нужны живые сцены вместо графики)

Большинство генераторов (Sora, Veo, Kling, Runway) блокируют или ограничивают внешность реальных знаменитостей. Поэтому промпты описывают типаж, а не лицо. Плашку «AI parody» оставляйте в кадре при любом варианте.

**Сцена 1, раздевалка, телефон (0–3 с)**
> Vertical 9:16 cinematic close-up, modern football locker room, warm overhead lights. A muscular Portuguese footballer in his late 30s, slicked-back dark hair, white training top with number 7, stares at his smartphone in disbelief, eyes widening, mouth opening to shout. Shallow depth of field, realistic skin, 35mm lens, handheld micro-shake, photoreal.

**Сцена 2, вставка экрана телефона (0–3 с)**
> Vertical 9:16 macro shot of a smartphone screen showing a glowing blue football rating card with a big "99", the card animates in with a flash. Realistic screen reflections, dark background.

**Сцена 3, молодой игрок дразнит (4–6 с)**
> Vertical 9:16 medium close-up, same locker room. A slim 18-year-old Spanish winger with short curly dark hair, red-and-blue training top, leans into frame with a cheeky confident grin and raises his eyebrows at the camera. Soft key light, realistic, cinematic, natural motion.

**Сцена 4, удар (6.5–10.5 с)**
> Vertical 9:16, floodlit stadium at night, low angle behind the ball on the penalty spot. The same 30s footballer in white kit takes a deep breath, power stance, then strikes the ball, slow motion at contact, ball flies into the top corner, net ripples. Dramatic rim light, realistic physics.

**Сцена 5, новая карточка (11–13 с)**
> Vertical 9:16 motion graphic: a dark purple and gold premium football card with "100" and "GOAT" slams onto the screen, god rays, gold confetti, glossy reflections.

**Сцена 6, реакция молодого игрока (13–14.5 с)**
> Vertical 9:16 close-up, the 18-year-old winger's confident smile drops into comedic shock, jaw open, frozen, quick push-in zoom.

**Сцена 7, финал (15.5–19 с)**
> Vertical 9:16, the 30s footballer turns to camera, jumps and lands with arms spread wide in a celebration pose, confident smirk, stadium lights behind, confetti, cinematic slow motion.

Синхронизация губ: Kling Lip Sync, Hedra или Runway Act-One по файлам из `voices/`.

## Сборка в CapCut (если меняете сцены)

1. Новый проект 9:16, 1080×1920, 30 fps.
2. Положите клипы сцен по таймкодам из таблицы выше.
3. Аудио: дорожка `audio_dialogue.wav` (0 dB), `audio_sfx.wav` (−3 dB), `audio_music.wav` (−12 dB, ключ на диалог).
4. Субтитры: импортируйте `subtitles.srt`, жирный белый шрифт с чёрной обводкой, держите их выше нижних 300 px (там интерфейс TikTok).
5. Оставьте плашку «AI PARODY · NOT REAL» и включите в TikTok отметку «AI-generated content».
6. Экспорт: 1080p, 30 fps, высокий битрейт.

## Подпись для публикации

> RONALDO SAW YAMAL'S RATING 💀 #ronaldo #yamal #siuuu #football #eafc #fyp #aiparody
> AI parody, not real. Fictional ratings.

## Пересборка

```bash
pip install kokoro-onnx soundfile numpy pillow   # + ffmpeg в системе
# kokoro-v1.0.onnx и voices-v1.0.bin из github.com/thewh1teagle/kokoro-onnx (релиз model-files-v1.0)
python3 make_tiktok.py <папка_kokoro> <папка_вывода>
PREVIEW="0.5,9,12" python3 make_tiktok.py <папка_kokoro> <папка_вывода>   # только превью-кадры
```
