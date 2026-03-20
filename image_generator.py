import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

LOGO_PATH = Path("felsefeco_logo.png")

# Font dosyaları projenin kendi klasöründe
BASE_DIR = Path(__file__).parent
FONT = {
    "bold":        BASE_DIR / "DejaVuSerif-Bold.ttf",
    "regular":     BASE_DIR / "DejaVuSerif.ttf",
    "italic":      BASE_DIR / "DejaVuSerif-Italic.ttf",
    "bold_italic": BASE_DIR / "DejaVuSerif-BoldItalic.ttf",
}

POST_SIZE  = (1080, 1350)
STORY_SIZE = (1080, 1920)

PALETTES = [
    {"bg": "#F4E7C5", "text": "#2C1810", "accent": "#8B6914", "sub": "#6B4F12"},
    {"bg": "#EAD7A1", "text": "#1A1208", "accent": "#7A5C10", "sub": "#5C4510"},
    {"bg": "#DCC48E", "text": "#1A1208", "accent": "#6B4F0E", "sub": "#4A3509"},
    {"bg": "#F1E3B6", "text": "#2C1810", "accent": "#8B6914", "sub": "#6B4F12"},
    {"bg": "#E5E7EB", "text": "#111827", "accent": "#374151", "sub": "#6B7280"},
    {"bg": "#F0F2F5", "text": "#111827", "accent": "#374151", "sub": "#6B7280"},
    {"bg": "#D6D9DD", "text": "#111827", "accent": "#374151", "sub": "#6B7280"},
    {"bg": "#D6A77A", "text": "#1C0F06", "accent": "#5C2E0A", "sub": "#7A3B10"},
    {"bg": "#E0B899", "text": "#1C0F06", "accent": "#5C2E0A", "sub": "#7A3B10"},
    {"bg": "#E8DFF5", "text": "#1A0A2E", "accent": "#4C1D95", "sub": "#6D28D9"},
    {"bg": "#DCEEF2", "text": "#0A1E2E", "accent": "#1E3A5F", "sub": "#2563EB"},
    {"bg": "#F5E4E0", "text": "#2E0A08", "accent": "#9B1C1C", "sub": "#C53030"},
    {"bg": "#EAF4E1", "text": "#0A1E0A", "accent": "#14532D", "sub": "#16A34A"},
    {"bg": "#F3E8FF", "text": "#1A0A2E", "accent": "#4C1D95", "sub": "#7C3AED"},
]

def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _font(size, style="bold"):
    path = FONT.get(style, FONT["bold"])
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()

def _make_image(size, quote_data, palette):
    w, h = size
    bg_color   = _hex(palette["bg"])
    text_color = _hex(palette["text"])
    accent     = _hex(palette["accent"])
    sub_color  = _hex(palette["sub"])

    img  = Image.new("RGB", size, bg_color)
    draw = ImageDraw.Draw(img)

    quote  = quote_data.get("quote", "")
    author = quote_data.get("author", "")
    akim   = quote_data.get("akim", "")

    quoted_text = "\u201c%s\u201d" % quote

    # Geniş kenar boşluğu
    margin    = 110
    usable_w  = w - (margin * 2)

    # Font ve satır yüksekliği
    f_q = _font(82, "bold")
    lh  = 105

    # Satırları sar — piksel bazlı
    words   = quoted_text.split()
    lines   = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0,0), test, font=f_q)
        if bbox[2] - bbox[0] > usable_w and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    # Çok uzunsa küçük font
    if len(lines) > 6:
        f_q = _font(68, "bold")
        lh  = 88
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            bbox = draw.textbbox((0,0), test, font=f_q)
            if bbox[2] - bbox[0] > usable_w and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

    total_h = len(lines) * lh
    y = int(h * 0.42) - total_h // 2

    for line in lines:
        bbox = draw.textbbox((0,0), line, font=f_q)
        lw   = bbox[2] - bbox[0]
        x    = (w - lw) // 2
        draw.text((x, y), line, font=f_q, fill=text_color)
        y += lh

    # Ayraç
    line_y = y + 45
    draw.rectangle([(w//2)-70, line_y, (w//2)+70, line_y+2], fill=accent)

    # Yazar
    f_author    = _font(56, "italic")
    author_text = "— %s" % author
    bbox        = draw.textbbox((0,0), author_text, font=f_author)
    aw          = bbox[2] - bbox[0]
    draw.text(((w-aw)//2, line_y+22), author_text, font=f_author, fill=accent)

    # Akım
    f_akim = _font(40, "regular")
    bbox   = draw.textbbox((0,0), akim, font=f_akim)
    aw2    = bbox[2] - bbox[0]
    draw.text(((w-aw2)//2, line_y+96), akim, font=f_akim, fill=sub_color)

    # @felsefe.co
    handle_y = int(h * 0.87)
    if LOGO_PATH.exists():
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = logo.resize((90, 90), Image.LANCZOS)
            img.paste(logo, ((w-90)//2, handle_y - 110), logo)
        except:
            pass

    f_handle = _font(46, "bold")
    handle   = "@felsefe.co"
    bbox     = draw.textbbox((0,0), handle, font=f_handle)
    hw       = bbox[2] - bbox[0]
    draw.text(((w-hw)//2, handle_y), handle, font=f_handle, fill=sub_color)

    return img

def create_post_image(quote_data, palette=None):
    if palette is None:
        palette = random.choice(PALETTES)
    img      = _make_image(POST_SIZE, quote_data, palette)
    safe     = re.sub(r"[^a-z0-9]", "_", quote_data.get("author","x").lower())[:20]
    filename = "post_%s_%d.jpg" % (safe, int(time.time()))
    path     = OUTPUT_DIR / filename
    img.save(str(path), "JPEG", quality=95)
    return path, palette

def create_story_image(quote_data, palette):
    img      = _make_image(STORY_SIZE, quote_data, palette)
    safe     = re.sub(r"[^a-z0-9]", "_", quote_data.get("author","x").lower())[:20]
    filename = "story_%s_%d.jpg" % (safe, int(time.time()))
    path     = OUTPUT_DIR / filename
    img.save(str(path), "JPEG", quality=95)
    return path
