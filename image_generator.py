import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

SITE_HANDLE = "felsefemiz.net"

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
    # --- Klasik Krem & Altin ---
    {"bg": "#F4E7C5", "text": "#2C1810", "accent": "#8B6914", "sub": "#6B4F12"},
    {"bg": "#EAD7A1", "text": "#1A1208", "accent": "#7A5C10", "sub": "#5C4510"},
    {"bg": "#FDF6E3", "text": "#1C1008", "accent": "#B8860B", "sub": "#8B6914"},
    {"bg": "#F5ECD7", "text": "#2C1810", "accent": "#A0522D", "sub": "#8B4513"},

    # --- Koyu & Dramatik ---
    {"bg": "#1A1A2E", "text": "#E8E0F0", "accent": "#C084FC", "sub": "#A855F7"},
    {"bg": "#0F172A", "text": "#E2E8F0", "accent": "#818CF8", "sub": "#6366F1"},
    {"bg": "#1E1B18", "text": "#F5F0E8", "accent": "#D97706", "sub": "#B45309"},
    {"bg": "#12141A", "text": "#E8EAF0", "accent": "#60A5FA", "sub": "#3B82F6"},
    {"bg": "#1A0A0A", "text": "#F5E8E8", "accent": "#F87171", "sub": "#EF4444"},
    {"bg": "#0D1F0D", "text": "#E8F5E8", "accent": "#4ADE80", "sub": "#22C55E"},

    # --- Gri & Minimal ---
    {"bg": "#F8F9FA", "text": "#1A1A1A", "accent": "#495057", "sub": "#6C757D"},
    {"bg": "#EAEAEA", "text": "#111111", "accent": "#333333", "sub": "#555555"},
    {"bg": "#2D2D2D", "text": "#F0F0F0", "accent": "#CCCCCC", "sub": "#999999"},

    # --- Pastel & Soft ---
    {"bg": "#FFF0F3", "text": "#3D0010", "accent": "#C9184A", "sub": "#FF4D6D"},
    {"bg": "#F0FFF4", "text": "#0A2E14", "accent": "#2D6A4F", "sub": "#40916C"},
    {"bg": "#EFF6FF", "text": "#0A1628", "accent": "#1D4ED8", "sub": "#3B82F6"},
    {"bg": "#FFF7ED", "text": "#2D1200", "accent": "#C2410C", "sub": "#EA580C"},
    {"bg": "#F5F3FF", "text": "#1A0A2E", "accent": "#6D28D9", "sub": "#8B5CF6"},
    {"bg": "#ECFDF5", "text": "#0A2618", "accent": "#065F46", "sub": "#059669"},

    # --- Toprak & Doğa ---
    {"bg": "#D4A373", "text": "#1A0A00", "accent": "#5C3317", "sub": "#7B4226"},
    {"bg": "#A8763E", "text": "#FFF8F0", "accent": "#FFD700", "sub": "#FFC107"},
    {"bg": "#8B7355", "text": "#FFF8F0", "accent": "#F5DEB3", "sub": "#DEB887"},
    {"bg": "#4A3728", "text": "#F5E6D3", "accent": "#D4A373", "sub": "#C49A6C"},

    # --- Gece Mavisi & Derin ---
    {"bg": "#03045E", "text": "#CAF0F8", "accent": "#90E0EF", "sub": "#48CAE4"},
    {"bg": "#023E8A", "text": "#E0F4FF", "accent": "#ADE8F4", "sub": "#90E0EF"},
    {"bg": "#1B263B", "text": "#E0E8F5", "accent": "#778DA9", "sub": "#415A77"},
    {"bg": "#0D1B2A", "text": "#E8F4FD", "accent": "#4A90D9", "sub": "#2E6DA4"},

    # --- Mor & Mistik ---
    {"bg": "#2D1B69", "text": "#EDE9FE", "accent": "#C4B5FD", "sub": "#A78BFA"},
    {"bg": "#4A0E8F", "text": "#F3E8FF", "accent": "#E9D5FF", "sub": "#D8B4FE"},
    {"bg": "#F3E8FF", "text": "#1A0A2E", "accent": "#7C3AED", "sub": "#6D28D9"},

    # --- Sıcak & Enerjik ---
    {"bg": "#FFF3E0", "text": "#1A0800", "accent": "#E65100", "sub": "#F57C00"},
    {"bg": "#FFEBEE", "text": "#1A0000", "accent": "#C62828", "sub": "#D32F2F"},
    {"bg": "#FCE4EC", "text": "#1A0010", "accent": "#AD1457", "sub": "#C2185B"},

    # --- Zeytin & Haki ---
    {"bg": "#3B4A2F", "text": "#F0F5E8", "accent": "#A8C570", "sub": "#8BAF4E"},
    {"bg": "#556B2F", "text": "#F5F0E0", "accent": "#F0E68C", "sub": "#DAA520"},
    {"bg": "#F0F2E6", "text": "#1A1E0A", "accent": "#4B5320", "sub": "#6B7340"},

    # --- Pembe & Rose ---
    {"bg": "#FDF2F8", "text": "#2D0A1E", "accent": "#9D174D", "sub": "#BE185D"},
    {"bg": "#831843", "text": "#FDF2F8", "accent": "#FBCFE8", "sub": "#F9A8D4"},

    # --- Cyan & Teal ---
    {"bg": "#ECFEFF", "text": "#0A1E1F", "accent": "#0E7490", "sub": "#0891B2"},
    {"bg": "#134E4A", "text": "#F0FDFA", "accent": "#5EEAD4", "sub": "#2DD4BF"},
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

    margin    = 110
    usable_w  = w - (margin * 2)

    f_q = _font(78, "bold")
    lh  = 105

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

    if len(lines) > 6:
        f_q = _font(64, "bold")
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

    line_y = y + 45
    draw.rectangle([(w//2)-70, line_y, (w//2)+70, line_y+2], fill=accent)

    f_author    = _font(52, "italic")
    author_text = "— %s" % author
    bbox        = draw.textbbox((0,0), author_text, font=f_author)
    aw          = bbox[2] - bbox[0]
    draw.text(((w-aw)//2, line_y+22), author_text, font=f_author, fill=accent)

    f_akim = _font(36, "regular")
    bbox   = draw.textbbox((0,0), akim, font=f_akim)
    aw2    = bbox[2] - bbox[0]
    draw.text(((w-aw2)//2, line_y+96), akim, font=f_akim, fill=sub_color)

    handle_y = int(h * 0.87)
    f_handle = _font(42, "bold")
    bbox     = draw.textbbox((0,0), SITE_HANDLE, font=f_handle)
    hw       = bbox[2] - bbox[0]
    draw.text(((w-hw)//2, handle_y), SITE_HANDLE, font=f_handle, fill=sub_color)

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

def create_square_cover(title, subtitle=""):
    """
    Filozoflar/Kategoriler icin profil kapagi.
    Ismi kelime kelime boler ve dikey yazar.
    Filigran (felsefemiz.net) ve cerceve kaldirilmistir.
    """
    palette = random.choice(PALETTES)
    w, h = 1080, 1080

    bg_color   = _hex(palette["bg"])
    text_color = _hex(palette["text"])

    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Ismi kelime kelime bol (Mustafa / Kemal / Ataturk)
    words = title.strip().split()
    if not words: words = ["Anonim"]
    
    # Kelime sayisina gore dinamik font boyutu
    count = len(words)
    if count <= 2: f_size = 180
    elif count == 3: f_size = 150
    else: f_size = 120
    
    f_title = _font(f_size, "bold")
    
    # Toplam metin yuksekligini hesapla (dikeyde ortalamak icin)
    line_h = f_size * 1.15
    total_h = count * line_h
    current_y = (h - total_h) // 2

    # Kelimeleri Tek Tek Alt Alta Yaz
    for word in words:
        bbox = draw.textbbox((0, 0), word, font=f_title)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw)//2, current_y), word, font=f_title, fill=text_color)
        current_y += line_h

    # --- felsefemiz.net VE CERCEVE BURADAN KALDIRILDI ---

    safe_name = re.sub(r"[^a-z0-9]", "_", title.lower())
    filename = "cover_%s_%d.jpg" % (safe_name[:20], int(time.time()))
    filepath = OUTPUT_DIR / filename
    img.save(str(filepath), "JPEG", quality=95)
    
    return str(filepath)
