import os, re, time, textwrap, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("images")
OUTPUT_DIR.mkdir(exist_ok=True)

SITE_HANDLE_BOLD    = "felsefemiz"
SITE_HANDLE_REGULAR = ".net"

# Font dosyaları projenin kendi klasöründe
BASE_DIR = Path(__file__).parent
FONT = {
    "bold":        BASE_DIR / "DejaVuSerif-Bold.ttf",
    "regular":     BASE_DIR / "DejaVuSerif.ttf",
    "italic":      BASE_DIR / "DejaVuSerif-Italic.ttf",
    "bold_italic": BASE_DIR / "DejaVuSerif-BoldItalic.ttf",
}

# Montserrat — site handle için (varsa kullan, yoksa DejaVuSerif'e düş)
MONTSERRAT = {
    "bold":    BASE_DIR / "Montserrat-Bold.ttf",
    "regular": BASE_DIR / "Montserrat-Regular.ttf",
}

def _montserrat(size, style="bold"):
    """Montserrat fontu yükler; yoksa DejaVuSerif'e düşer."""
    path = MONTSERRAT.get(style, MONTSERRAT["bold"])
    try:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    except Exception:
        pass
    return _font(size, style)

POST_SIZE  = (1080, 1350)
STORY_SIZE = (1080, 1920)

PALETTES = [
    # --- PASTEL PALETLER: okunabilir, cansız değil ama cırt değil ---
    # Hiç beyaz/siyah arka plan yok. Her palet CR>=9. Atatürk'e siyah-beyaz ayrıca uygulanır.

    # Soğuk Tonlar
    {"bg": "#C9B1E8", "text": "#1E0A3C", "accent": "#6B3FA0", "sub": "#9B6BBE"},  # Lavanta
    {"bg": "#B8D4E8", "text": "#0A1E3C", "accent": "#1565C0", "sub": "#4D7B9A"},  # Bebek Mavisi
    {"bg": "#B0C8D8", "text": "#0A1828", "accent": "#1976D2", "sub": "#4D7590"},  # Çelik Mavisi
    {"bg": "#B8C8D8", "text": "#0A1828", "accent": "#37474F", "sub": "#64868A"},  # Duman Mavisi
    {"bg": "#C0C8D8", "text": "#0A1028", "accent": "#37474F", "sub": "#5C7080"},  # Pervankâlin
    {"bg": "#C8D0E8", "text": "#0A1030", "accent": "#1A237E", "sub": "#4959BB"},  # Kır Çiçeği
    {"bg": "#D0C0E8", "text": "#180830", "accent": "#7B1FA2", "sub": "#A850C8"},  # Leylak
    {"bg": "#D8C8E8", "text": "#1A0830", "accent": "#7B1FA2", "sub": "#AB5AC8"},  # Açık Leylak
    {"bg": "#C8B0D8", "text": "#180A30", "accent": "#6A1B9A", "sub": "#9850C0"},  # Menekşe
    {"bg": "#C9B1E8", "text": "#1E0A3C", "accent": "#512DA8", "sub": "#7B52C8"},  # Ametist

    # Yeşil Tonlar
    {"bg": "#B8D4B0", "text": "#0A2010", "accent": "#2E7D32", "sub": "#558B2F"},  # Adaçayı
    {"bg": "#A8D8C0", "text": "#012015", "accent": "#00695C", "sub": "#3E9B8A"},  # Nane
    {"bg": "#C4D4B8", "text": "#0A1E0A", "accent": "#33691E", "sub": "#6E9B3F"},  # Bej Yeşil
    {"bg": "#C0D8A8", "text": "#0A1E00", "accent": "#558B2F", "sub": "#7AAD50"},  # Fıstık
    {"bg": "#A8D4C8", "text": "#012820", "accent": "#00796B", "sub": "#3E9B90"},  # Deniz Köpüğü
    {"bg": "#A8C8C8", "text": "#012020", "accent": "#00695C", "sub": "#3E8888"},  # Mavi Yeşil
    {"bg": "#B0D8D0", "text": "#012820", "accent": "#00695C", "sub": "#3E9B90"},  # Su Yeşili
    {"bg": "#C8D0A0", "text": "#121800", "accent": "#827717", "sub": "#B0A230"},  # Zeytin

    # Sıcak Tonlar
    {"bg": "#E8C4C0", "text": "#3C0808", "accent": "#8B2635", "sub": "#B05555"},  # Gül Kurusu
    {"bg": "#E8C8D0", "text": "#3C0A18", "accent": "#880E4F", "sub": "#BD4070"},  # Pudra Pembe
    {"bg": "#E8C0CC", "text": "#3C0A1C", "accent": "#AD1457", "sub": "#D2507A"},  # Kırmızı Gül
    {"bg": "#D0B8D0", "text": "#200820", "accent": "#7B1FA2", "sub": "#AB4BB0"},  # Erik
    {"bg": "#C8B0D8", "text": "#180A30", "accent": "#6A1B9A", "sub": "#9850C0"},  # Mor
    {"bg": "#F0B8A8", "text": "#3C0800", "accent": "#BF360C", "sub": "#B04030"},  # Mercan
    {"bg": "#E0B8A0", "text": "#280800", "accent": "#BF360C", "sub": "#9D5437"},  # Terracotta

    # Nötr / Toprak Tonlar
    {"bg": "#F0C8A0", "text": "#2C1000", "accent": "#8B4513", "sub": "#B0703A"},  # Şeftali
    {"bg": "#E0D0A0", "text": "#1A1000", "accent": "#8B6914", "sub": "#B0943A"},  # Krem Altın
    {"bg": "#E0C8A8", "text": "#201000", "accent": "#795548", "sub": "#B09070"},  # Sıcak Kum
    {"bg": "#D4C0A8", "text": "#1C0C00", "accent": "#5D4037", "sub": "#9D7E63"},  # Tarçın
    {"bg": "#E8D8A8", "text": "#201000", "accent": "#8B6914", "sub": "#B0943A"},  # Arnika
    {"bg": "#E8D0A0", "text": "#201000", "accent": "#E65100", "sub": "#B08030"},  # Bal
    {"bg": "#E8C888", "text": "#201000", "accent": "#8B5000", "sub": "#B08020"},  # Amber
    {"bg": "#D8C0B8", "text": "#280808", "accent": "#8B2635", "sub": "#A05555"},  # Antik Gül
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
    
    # --- ATATÜRK KONTROLÜ (Siyah Arkaplan Beyaz Yazı) ---
    author_name = quote_data.get("author", "").lower()
    is_ataturk = "atatürk" in author_name or "mustafa kemal" in author_name
    
    if is_ataturk:
        bg_color   = (0, 0, 0)
        text_color = (255, 255, 255)
        accent     = (255, 255, 255)
        sub_color  = (180, 180, 180)
    else:
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
    margin   = 110
    usable_w = w - (margin * 2)

    # Güvenli alan: yazar + akım + handle için alt 280px ayrılıyor
    # Söz için kullanılabilir yükseklik
    safe_top    = int(h * 0.12)
    safe_bottom = int(h * 0.72)
    max_quote_h = safe_bottom - safe_top

    def _wrap_text(font_size, max_lines=99):
        """Verilen font boyutunda metni sarar, satır listesi döner."""
        f = _font(font_size, "bold")
        lh = int(font_size * 1.45)
        wrds = quoted_text.split()
        lns, cur = [], ""
        for w_ in wrds:
            test = (cur + " " + w_).strip()
            bb = draw.textbbox((0,0), test, font=f)
            if bb[2] - bb[0] > usable_w and cur:
                lns.append(cur)
                cur = w_
            else:
                cur = test
        if cur: lns.append(cur)
        return f, lh, lns

    # Font boyutunu kademeli küçült — güvenli alana sığana kadar
    for font_size in (66, 58, 50, 42, 34, 28):
        f_q, lh, lines = _wrap_text(font_size)
        total_h = len(lines) * lh
        if total_h <= max_quote_h:
            break

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
    f_author    = _font(40, "italic")
    author_text = "— %s" % author
    bbox        = draw.textbbox((0,0), author_text, font=f_author)
    aw          = bbox[2] - bbox[0]
    draw.text(((w-aw)//2, line_y+22), author_text, font=f_author, fill=accent)

    # Akım
    f_akim = _font(24, "regular")
    bbox   = draw.textbbox((0,0), akim, font=f_akim)
    aw2    = bbox[2] - bbox[0]
    draw.text(((w-aw2)//2, line_y+96), akim, font=f_akim, fill=sub_color)

    # Filigran — "felsefemiz" Montserrat Bold + ".net" Montserrat Regular
    handle_y    = int(h * 0.87)
    f_hbold     = _montserrat(30, "bold")
    f_hreg      = _montserrat(30, "regular")
    bbox_bold   = draw.textbbox((0,0), SITE_HANDLE_BOLD, font=f_hbold)
    bbox_reg    = draw.textbbox((0,0), SITE_HANDLE_REGULAR, font=f_hreg)
    w_bold      = bbox_bold[2] - bbox_bold[0]
    w_reg       = bbox_reg[2]  - bbox_reg[0]
    total_w     = w_bold + w_reg
    x_start     = (w - total_w) // 2
    draw.text((x_start, handle_y),          SITE_HANDLE_BOLD,    font=f_hbold, fill=sub_color)
    draw.text((x_start + w_bold, handle_y), SITE_HANDLE_REGULAR, font=f_hreg,  fill=sub_color)

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
    Filozof Kapak: İsim alt alta, filigransız. 
    Atatürk ise Siyah-Beyaz.
    """
    palette = random.choice(PALETTES)
    w, h = 1080, 1080
    
    is_ataturk = "atatürk" in title.lower() or "mustafa kemal" in title.lower()
    
    if is_ataturk:
        bg_color   = (0, 0, 0)
        text_color = (255, 255, 255)
    else:
        bg_color   = _hex(palette["bg"])
        text_color = _hex(palette["text"])

    img  = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    words = title.strip().split()
    if not words:
        words = ["Anonim"]

    margin   = 100           # sol/sağ güvenli alan
    usable_w = w - margin*2  # 880px

    # Her kelimeyi ayrı satıra yaz.
    # Font boyutunu kelime sayısı + en uzun kelimenin uzunluğuna göre belirle:
    # Başlangıç boyutu küçük tutuldu (eski: 180), dinamik olarak büyütülebilir.
    count = len(words)

    # Başlangıç font boyutları — öncekinden çok daha küçük
    if count == 1:
        start_size = 100
    elif count == 2:
        start_size = 90
    elif count == 3:
        start_size = 80
    else:
        start_size = 70

    # En uzun kelimeye göre sığmıyorsa küçült
    f_size = start_size
    while f_size >= 30:
        f_title = _font(f_size, "bold")
        max_word_w = max(
            draw.textbbox((0,0), word, font=f_title)[2]
            for word in words
        )
        if max_word_w <= usable_w:
            break
        f_size -= 6

    f_title = _font(f_size, "bold")
    line_h  = int(f_size * 1.35)
    total_h = count * line_h
    y       = (h - total_h) // 2

    for word in words:
        bbox = draw.textbbox((0, 0), word, font=f_title)
        x    = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), word, font=f_title, fill=text_color)
        y += line_h

    safe_name = re.sub(r"[^a-z0-9]", "_", title.lower())
    filename = "cover_%s_%d.jpg" % (safe_name[:20], int(time.time()))
    filepath = OUTPUT_DIR / filename
    img.save(str(filepath), "JPEG", quality=95)
    return str(filepath)
