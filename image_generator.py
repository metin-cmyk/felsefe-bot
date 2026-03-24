import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

SITE_HANDLE = "felsefemiz.net"

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
    {"bg": "#1C1C1C", "text": "#E8E8E8", "accent": "#BFA15F", "sub": "#8F8F8F"},
    {"bg": "#2B2B2B", "text": "#F0F0F0", "accent": "#A38A52", "sub": "#A0A0A0"},
    {"bg": "#121A21", "text": "#E6F0F9", "accent": "#5E8BA8", "sub": "#8BA6B8"},
    {"bg": "#F9F6EE", "text": "#2C3539", "accent": "#5B7C8A", "sub": "#6D8794"}
]

def _font(size, style="regular"):
    return ImageFont.truetype(str(FONT[style]), size)

def _make_image(size, quote_data, palette):
    w, h = size
    img  = Image.new("RGB", size, palette["bg"])
    draw = ImageDraw.Draw(img)

    margin = 80
    draw.rectangle([margin, margin, w-margin, h-margin], outline=palette["accent"], width=4)

    quote  = quote_data["quote"]
    author = quote_data["author"]
    akim   = quote_data.get("akim", "")

    # Fontlar -4 punto küçültüldü
    quote_len = len(quote)
    if quote_len < 80:     f_quote, wrap_w = _font(78, "bold_italic"), 20
    elif quote_len < 160:  f_quote, wrap_w = _font(64, "bold_italic"), 25
    else:                  f_quote, wrap_w = _font(56, "bold_italic"), 32

    wrapped_quote = textwrap.fill(quote, width=wrap_w)
    
    bbox_q = draw.multiline_textbbox((0,0), wrapped_quote, font=f_quote, align="center")
    qw = bbox_q[2] - bbox_q[0]
    qh = bbox_q[3] - bbox_q[1]
    quote_y = (h - qh) // 2 - 120

    draw.multiline_text(((w-qw)//2, quote_y), wrapped_quote, font=f_quote, fill=palette["text"], align="center")

    line_y = quote_y + qh + 80
    draw.line([(w//2 - 60, line_y), (w//2 + 60, line_y)], fill=palette["accent"], width=3)

    f_author = _font(52, "italic")
    author_text = "— %s" % author
    bbox_a = draw.textbbox((0,0), author_text, font=f_author)
    aw = bbox_a[2] - bbox_a[0]
    draw.text(((w-aw)//2, line_y+22), author_text, font=f_author, fill=palette["accent"])

    f_akim = _font(36, "regular")
    bbox_ak = draw.textbbox((0,0), akim, font=f_akim)
    akw = bbox_ak[2] - bbox_ak[0]
    draw.text(((w-akw)//2, line_y+96), akim, font=f_akim, fill=palette["sub"])

    handle_y = int(h * 0.87)
    f_handle = _font(42, "bold")
    bbox_h = draw.textbbox((0,0), SITE_HANDLE, font=f_handle)
    hw = bbox_h[2] - bbox_h[0]
    draw.text(((w-hw)//2, handle_y), SITE_HANDLE, font=f_handle, fill=palette["sub"])

    return img

def create_post_image(quote_data, palette=None):
    if palette is None: palette = random.choice(PALETTES)
    img = _make_image(POST_SIZE, quote_data, palette)
    safe = re.sub(r"[^a-z0-9]", "_", quote_data["author"].lower())[:20]
    filepath = OUTPUT_DIR / f"post_{safe}_{int(time.time())}.jpg"
    img.save(filepath, "JPEG", quality=90)
    return str(filepath), palette

def create_story_image(quote_data, palette):
    img = _make_image(STORY_SIZE, quote_data, palette)
    safe = re.sub(r"[^a-z0-9]", "_", quote_data["author"].lower())[:20]
    filepath = OUTPUT_DIR / f"story_{safe}_{int(time.time())}.jpg"
    img.save(filepath, "JPEG", quality=90)
    return str(filepath)

def create_square_cover(title, subtitle="Felsefe Ansiklopedisi"):
    """Kategoriler ve Filozoflar icin ACF Kapak Gorseli uretir"""
    palette = random.choice(PALETTES)
    w, h = 1080, 1080
    img = Image.new("RGB", (w, h), palette["bg"])
    draw = ImageDraw.Draw(img)

    margin = 60
    draw.rectangle([margin, margin, w-margin, h-margin], outline=palette["accent"], width=6)

    f_title = _font(90, "bold")
    wrapped_title = textwrap.fill(title, width=15)
    
    bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=f_title, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    title_y = (h - th) // 2 - 50
    draw.multiline_text(((w - tw)//2, title_y), wrapped_title, font=f_title, fill=palette["text"], align="center")

    f_sub = _font(40, "italic")
    bbox_sub = draw.textbbox((0, 0), subtitle, font=f_sub)
    sw = bbox_sub[2] - bbox_sub[0]
    draw.text(((w - sw)//2, title_y + th + 60), subtitle, font=f_sub, fill=palette["sub"])

    f_handle = _font(36, "regular")
    bbox_h = draw.textbbox((0, 0), SITE_HANDLE, font=f_handle)
    hw = bbox_h[2] - bbox_h[0]
    draw.text(((w - hw)//2, h - margin - 50), SITE_HANDLE, font=f_handle, fill=palette["accent"])

    safe_name = re.sub(r"[^a-z0-9]", "_", title.lower())
    filepath = OUTPUT_DIR / f"cover_{safe_name}_{int(time.time())}.jpg"
    img.save(filepath, "JPEG", quality=90)
    return str(filepath)
