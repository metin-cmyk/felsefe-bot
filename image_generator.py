import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

LOGO_PATH = Path("felsefeco_logo.png")
FONT_BOLD_PATH = Path("BarlowCondensed-SemiBold.ttf")
FONT_REG_PATH  = Path("BarlowCondensed-Regular.ttf")

POST_SIZE  = (1080, 1350)
STORY_SIZE = (1080, 1920)

COLOR_PALETTES = [
    {"bg": [(15, 10, 40), (40, 15, 80)],   "text": (255, 255, 255), "accent": (180, 130, 255)},
    {"bg": [(10, 30, 50), (20, 60, 100)],  "text": (255, 255, 255), "accent": (100, 200, 255)},
    {"bg": [(40, 15, 15), (90, 30, 30)],   "text": (255, 255, 255), "accent": (255, 150, 100)},
    {"bg": [(10, 40, 25), (20, 80, 50)],   "text": (255, 255, 255), "accent": (100, 255, 150)},
    {"bg": [(40, 30, 10), (90, 70, 20)],   "text": (255, 255, 255), "accent": (255, 220, 100)},
    {"bg": [(30, 10, 40), (70, 20, 90)],   "text": (255, 255, 255), "accent": (220, 100, 255)},
    {"bg": [(10, 35, 45), (20, 75, 95)],   "text": (255, 255, 255), "accent": (80, 220, 220)},
]

WATERMARK_SYMBOLS = [
    "⚡", "∞", "☯", "Ω", "φ", "∴", "✦", "◈",
]

def _font(size, bold=True):
    path = FONT_BOLD_PATH if bold else FONT_REG_PATH
    if path.exists():
        return ImageFont.truetype(str(path), size)
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def _make_gradient_bg(size, palette):
    w, h = size
    c1 = np.array(palette["bg"][0], dtype=float)
    c2 = np.array(palette["bg"][1], dtype=float)
    img = Image.new("RGB", size)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / h
        color = (c1 * (1-t) + c2 * t).astype(np.uint8)
        arr[y, :] = color
    return Image.fromarray(arr)

def _add_watermark(img, palette):
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    f_wm = _font(180, bold=True)

    symbols = ["Σ", "Φ", "Ψ", "Λ", "Θ", "Ξ", "∞", "◈"]
    for i in range(6):
        sym = random.choice(symbols)
        x = random.randint(50, w-200)
        y = random.randint(50, h-200)
        draw.text((x, y), sym, font=f_wm, fill=(255, 255, 255, 18))

    # Dekoratif yatay çizgi
    accent = palette["accent"]
    draw.rectangle([60, h//2 - 1, w-60, h//2 + 1], fill=accent + (80,))
    return img

def _add_quote_text(img, quote_data, palette, size):
    w, h = size
    draw = ImageDraw.Draw(img)

    quote   = quote_data.get("quote", "")
    author  = quote_data.get("author", "")
    akim    = quote_data.get("akim", "")
    accent  = palette["accent"]
    text_c  = palette["text"]

    # Tırnak işareti - sol üst
    f_tirnak = _font(120, bold=True)
    draw.text((55, 60), "\u201c", font=f_tirnak, fill=accent + (0,) if len(accent)==3 else accent)

    # Ana söz
    f_quote = _font(72, bold=True)
    max_w   = 42 if w == 1080 else 42
    wrapped = textwrap.fill(quote, width=max_w)
    lines   = wrapped.split("\n")

    total_h = len(lines) * 88
    y_start = (h - total_h) // 2 - 60

    for line in lines:
        # Gölge
        draw.text((62, y_start+3), line, font=f_quote, fill=(0,0,0))
        draw.text((60, y_start),   line, font=f_quote, fill=text_c)
        y_start += 88

    # Ayraç çizgi
    line_y = y_start + 30
    draw.rectangle([60, line_y, 200, line_y+3], fill=accent)

    # Yazar
    f_author = _font(48, bold=True)
    draw.text((62, line_y+20), "— %s" % author, font=f_author, fill=accent)

    # Akım
    f_akim = _font(36, bold=False)
    draw.text((62, line_y+80), akim, font=f_akim, fill=text_c[:3] + (0,) if False else text_c)

    # Logo
    _add_logo(img, w, h)

    return img

def _add_logo(img, w, h):
    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo_size = 130
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            # Sağ alt köşe
            x = w - logo_size - 40
            y = h - logo_size - 40
            img.paste(logo, (x, y), logo)
        except:
            _add_text_logo(img, w, h)
    else:
        _add_text_logo(img, w, h)

def _add_text_logo(img, w, h):
    draw = ImageDraw.Draw(img)
    f_logo = _font(38, bold=True)
    draw.text((w-200, h-65), "felsefe.co", font=f_logo, fill=(255,255,255))

def create_post_image(quote_data):
    palette = random.choice(COLOR_PALETTES)
    img = _make_gradient_bg(POST_SIZE, palette)
    img = _add_watermark(img, palette)
    img = _add_quote_text(img, quote_data, palette, POST_SIZE)

    safe = re.sub(r"[^a-z0-9]", "_", quote_data["author"].lower())[:20]
    path = OUTPUT_DIR / "post_%s_%d.jpg" % (safe, int(time.time()))
    img.save(path, "JPEG", quality=95)
    return path

def create_story_image(quote_data):
    palette = random.choice(COLOR_PALETTES)
    img = _make_gradient_bg(STORY_SIZE, palette)
    img = _add_watermark(img, palette)
    img = _add_quote_text(img, quote_data, palette, STORY_SIZE)

    safe = re.sub(r"[^a-z0-9]", "_", quote_data["author"].lower())[:20]
    path = OUTPUT_DIR / "story_%s_%d.jpg" % (safe, int(time.time()))
    img.save(path, "JPEG", quality=95)
    return path
