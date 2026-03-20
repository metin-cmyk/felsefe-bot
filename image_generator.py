import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path(“images”)
OUTPUT_DIR.mkdir(exist_ok=True)

LOGO_PATH      = Path(“felsefeco_logo.png”)
FONT_BOLD_PATH = Path(“BarlowCondensed-SemiBold.ttf”)
FONT_REG_PATH  = Path(“BarlowCondensed-Regular.ttf”)

POST_SIZE  = (1080, 1350)
STORY_SIZE = (1080, 1920)

# Pastel / orta ton paletler — (arka plan rengi, koyu mu açık mı)

PALETTES = [
{“bg”: (232, 220, 255), “dark”: True,  “accent”: (100, 60, 180)},   # Lavender
{“bg”: (255, 228, 220), “dark”: True,  “accent”: (180, 80, 50)},    # Somon
{“bg”: (220, 240, 255), “dark”: True,  “accent”: (50, 100, 180)},   # Buz mavisi
{“bg”: (220, 255, 235), “dark”: True,  “accent”: (30, 130, 80)},    # Mint
{“bg”: (255, 245, 210), “dark”: True,  “accent”: (160, 110, 20)},   # Krem
{“bg”: (255, 220, 240), “dark”: True,  “accent”: (160, 40, 100)},   # Pembe
{“bg”: (60,  40, 100),  “dark”: False, “accent”: (180, 150, 255)},  # Koyu mor
{“bg”: (30,  60,  90),  “dark”: False, “accent”: (100, 180, 255)},  # Gece mavisi
{“bg”: (50,  30,  30),  “dark”: False, “accent”: (255, 160, 100)},  # Koyu kahve
{“bg”: (20,  60,  40),  “dark”: False, “accent”: (100, 220, 150)},  # Koyu yesil
]

def _font(size, bold=True):
path = FONT_BOLD_PATH if bold else FONT_REG_PATH
if path.exists():
return ImageFont.truetype(str(path), size)
for p in [”/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf”,
“/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf”]:
if Path(p).exists():
return ImageFont.truetype(p, size)
return ImageFont.load_default()

def _text_color(palette):
return (30, 30, 30) if palette[“dark”] else (240, 240, 240)

def _make_bg(size, palette):
return Image.new(“RGB”, size, palette[“bg”])

def _add_subtle_texture(img, palette):
“”“Cok hafif nokta doku — monotonlugu kirlar.”””
arr = np.array(img).astype(float)
noise = np.random.uniform(-8, 8, arr.shape)
arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
return Image.fromarray(arr)

def _draw_content(img, quote_data, palette, size):
w, h = size
draw = ImageDraw.Draw(img)

```
quote   = quote_data.get("quote", "")
author  = quote_data.get("author", "")
akim    = quote_data.get("akim", "")
tc      = _text_color(palette)
accent  = palette["accent"]

# Fontlar
f_tirnak = _font(160, bold=True)
f_quote  = _font(80, bold=True)
f_author = _font(52, bold=True)
f_akim   = _font(40, bold=False)

# --- Acik tırnak (sol ust) ---
draw.text((60, 30), '"', font=f_tirnak, fill=accent)

# --- Ana soz - ortali ---
max_chars = 22
wrapped = textwrap.fill(quote, width=max_chars)
lines   = wrapped.split("\n")
line_h  = 96
total_h = len(lines) * line_h

# Dikey merkez - biraz yukari
y = (h - total_h) // 2 - 80

for line in lines:
    bbox = draw.textbbox((0, 0), line, font=f_quote)
    lw = bbox[2] - bbox[0]
    x  = (w - lw) // 2
    draw.text((x, y), line, font=f_quote, fill=tc)
    y += line_h

# --- Kapanıs tırnak (sag alt of quote) ---
draw.text((w - 100, y - 20), '"', font=f_tirnak, fill=accent)

# --- Ayrac ---
line_y = y + 30
draw.rectangle([(w//2 - 60, line_y), (w//2 + 60, line_y + 4)], fill=accent)

# --- Yazar ---
author_text = "— %s" % author
bbox = draw.textbbox((0, 0), author_text, font=f_author)
aw = bbox[2] - bbox[0]
draw.text(((w - aw) // 2, line_y + 20), author_text, font=f_author, fill=accent)

# --- Akim ---
bbox = draw.textbbox((0, 0), akim, font=f_akim)
akw = bbox[2] - bbox[0]
draw.text(((w - akw) // 2, line_y + 85), akim, font=f_akim, fill=tc)

# --- Logo ---
_add_logo(img, draw, w, h, tc)

return img
```

def _add_logo(img, draw, w, h, tc):
logo_size = 160
margin    = 40
y_logo    = h - logo_size - margin

```
if LOGO_PATH.exists():
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        x = (w - logo_size) // 2
        img.paste(logo, (x, y_logo), logo)
        return
    except:
        pass

# Fallback: metin logo
f_logo = _font(44, bold=True)
text   = "felsefe.co"
bbox   = draw.textbbox((0, 0), text, font=f_logo)
lw     = bbox[2] - bbox[0]
draw.text(((w - lw) // 2, h - 65), text, font=f_logo, fill=tc)
```

def _make_image(size, quote_data):
palette = random.choice(PALETTES)
img = _make_bg(size, palette)
img = _add_subtle_texture(img, palette)
img = _draw_content(img, quote_data, palette, size)
return img

def create_post_image(quote_data):
img  = *make_image(POST_SIZE, quote_data)
safe = re.sub(r”[^a-z0-9]”, “*”, quote_data[“author”].lower())[:20]
path = OUTPUT_DIR / (“post_%s_%d.jpg” % (safe, int(time.time())))
img.save(path, “JPEG”, quality=95)
return path

def create_story_image(quote_data):
img  = *make_image(STORY_SIZE, quote_data)
safe = re.sub(r”[^a-z0-9]”, “*”, quote_data[“author”].lower())[:20]
path = OUTPUT_DIR / (“story_%s_%d.jpg” % (safe, int(time.time())))
img.save(path, “JPEG”, quality=95)
return path