import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

LOGO_PATH      = Path("felsefeco_logo.png")
FONT_BOLD_PATH = Path("BarlowCondensed-SemiBold.ttf")
FONT_REG_PATH  = Path("BarlowCondensed-Regular.ttf")

POST_SIZE  = (1080, 1350)
STORY_SIZE = (1080, 1920)

COLOR_PALETTES = [
    {"bg": [(15, 10, 40), (40, 15, 80)],  "text": (255,255,255), "accent": (180,130,255)},
    {"bg": [(10, 30, 50), (20, 60,100)],  "text": (255,255,255), "accent": (100,200,255)},
    {"bg": [(40, 15, 15), (90, 30, 30)],  "text": (255,255,255), "accent": (255,150,100)},
    {"bg": [(10, 40, 25), (20, 80, 50)],  "text": (255,255,255), "accent": (100,255,150)},
    {"bg": [(40, 30, 10), (90, 70, 20)],  "text": (255,255,255), "accent": (255,220,100)},
    {"bg": [(30, 10, 40), (70, 20, 90)],  "text": (255,255,255), "accent": (220,100,255)},
    {"bg": [(10, 35, 45), (20, 75, 95)],  "text": (255,255,255), "accent": (80, 220,220)},
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
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / h
        arr[y, :] = (c1 * (1-t) + c2 * t).astype(np.uint8)
    return Image.fromarray(arr)

def _add_watermark(img, palette):
    draw = ImageDraw.Draw(img, "RGBA")
    f_wm = _font(180, bold=True)
    symbols = ["Sigma", "Phi", "Psi", "Lambda", "Theta", "Xi"]
    greek   = [chr(0x03A3), chr(0x03A6), chr(0x03A8), chr(0x039B), chr(0x0398), chr(0x039E)]
    for i in range(6):
        sym = greek[i % len(greek)]
        x = random.randint(50, img.width-200)
        y = random.randint(50, img.height-200)
        draw.text((x, y), sym, font=f_wm, fill=(255, 255, 255, 18))
    return img

def _add_texts(img, quote_data, palette, size):
    w, h = size
    draw   = ImageDraw.Draw(img)
    quote  = quote_data.get("quote", "")
    author = quote_data.get("author", "")
    akim   = quote_data.get("akim", "")
    accent = palette["accent"]
    text_c = palette["text"]

    # Tırnak
    f_tirnak = _font(120, bold=True)
    draw.text((55, 60), "\u201c", font=f_tirnak, fill=accent)

    # Ana söz
    f_quote = _font(72, bold=True)
    wrapped = textwrap.fill(quote, width=42)
    lines   = wrapped.split("\n")
    total_h = len(lines) * 88
    y = (h - total_h) // 2 - 60

    for line in lines:
        draw.text((62, y+3), line, font=f_quote, fill=(0, 0, 0))
        draw.text((60, y),   line, font=f_quote, fill=text_c)
        y += 88

    # Ayraç
    draw.rectangle([60, y+30, 200, y+33], fill=accent)

    # Yazar
    f_author = _font(48, bold=True)
    draw.text((62, y+48), "— %s" % author, font=f_author, fill=accent)

    # Akım
    f_akim = _font(36, bold=False)
    draw.text((62, y+108), akim, font=f_akim, fill=text_c)

    # Logo
    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = logo.resize((130, 130), Image.LANCZOS)
            img.paste(logo, (w-170, h-170), logo)
        except:
            pass
    else:
        f_logo = _font(38, bold=True)
        draw.text((w-220, h-65), "felsefe.co", font=f_logo, fill=(255,255,255))

    return img

def _make_image(size, quote_data):
    palette = random.choice(COLOR_PALETTES)
    img = _make_gradient_bg(size, palette)
    img = _add_watermark(img, palette)
    img = _add_texts(img, quote_data, palette, size)
    return img

def create_post_image(quote_data):
    img  = _make_image(POST_SIZE, quote_data)
    safe = re.sub(r"[^a-z0-9]", "_", quote_data.get("author","x").lower())[:20]
    filename = "post_%s_%d.jpg" % (safe, int(time.time()))
    path = OUTPUT_DIR / filename
    img.save(str(path), "JPEG", quality=95)
    return path

def create_story_image(quote_data):
    img  = _make_image(STORY_SIZE, quote_data)
    safe = re.sub(r"[^a-z0-9]", "_", quote_data.get("author","x").lower())[:20]
    filename = "story_%s_%d.jpg" % (safe, int(time.time()))
    path = OUTPUT_DIR / filename
    img.save(str(path), "JPEG", quality=95)
    return path
