import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

LOGO_PATH = Path("felsefeco_logo.png")

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
    candidates = {
        "bold": [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ],
        "regular": [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ],
        "italic": [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        ],
    }
    for p in candidates.get(style, candidates["bold"]):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
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

    margin   = 100
    usable_w = w - (margin * 2)
    char_w   = 38
    max_chars = usable_w // char_w

    wrapped = textwrap.fill(quoted_text, width=max_chars)
    lines   = wrapped.split("\n")

    f_q = _font(64, "bold") if len(lines) > 5 else _font(76, "bold")
    lh  = 86 if len(lines) > 5 else 96

    total_h = len(lines) * lh
    y = int(h * 0.40) - total_h // 2 - 40

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=f_q)
        lw   = bbox[2] - bbox[0]
        x    = (w - lw) // 2
        draw.text((x, y), line, font=f_q, fill=text_color)
        y += lh

    # Ayraç
    line_y = y + 40
    draw.rectangle([(w//2)-60, line_y, (w//2)+60, line_y+2], fill=accent)

    # Yazar
    f_author    = _font(54, "italic")
    author_text = "— %s" % author
    bbox        = draw.textbbox((0,0), author_text, font=f_author)
    aw          = bbox[2] - bbox[0]
    draw.text(((w-aw)//2, line_y+20), author_text, font=f_author, fill=accent)

    # Akım
    f_akim = _font(38, "regular")
    bbox   = draw.textbbox((0,0), akim, font=f_akim)
    aw2    = bbox[2] - bbox[0]
    draw.text(((w-aw2)//2, line_y+90), akim, font=f_akim, fill=sub_color)

    # @felsefe.co — ortalı, h*0.88 civarında (daha yukarı)
    f_handle = _font(44, "bold")
    handle   = "@felsefe.co"
    bbox     = draw.textbbox((0,0), handle, font=f_handle)
    hw       = bbox[2] - bbox[0]
    handle_y = int(h * 0.88)

    if LOGO_PATH.exists():
        try:
            logo  = Image.open(LOGO_PATH).convert("RGBA")
            logo  = logo.resize((90, 90), Image.LANCZOS)
            lx    = (w - 90) // 2
            img.paste(logo, (lx, handle_y - 110), logo)
        except:
            pass

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
