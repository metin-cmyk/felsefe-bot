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
    # --- 1-10: Minimalist Beyaz ve Krem ---
    {"bg": "#FFFFFF", "text": "#1A1A1A", "accent": "#D90429", "sub": "#8D99AE"},
    {"bg": "#F8F9FA", "text": "#212529", "accent": "#343A40", "sub": "#6C757D"},
    {"bg": "#FDFDFD", "text": "#000000", "accent": "#FFB703", "sub": "#8ECAE6"},
    {"bg": "#FCFBF4", "text": "#2E3A46", "accent": "#E07A5F", "sub": "#81B29A"},
    {"bg": "#FAFAFA", "text": "#111111", "accent": "#4361EE", "sub": "#7209B7"},
    {"bg": "#FDF0D5", "text": "#003049", "accent": "#C1121F", "sub": "#669BBC"},
    {"bg": "#F1FAEE", "text": "#1D3557", "accent": "#E63946", "sub": "#457B9D"},
    {"bg": "#FDFFFC", "text": "#011627", "accent": "#2EC4B6", "sub": "#FF9F1C"},
    {"bg": "#F5F5F5", "text": "#202020", "accent": "#5A189A", "sub": "#9D4EDD"},
    {"bg": "#FEFAE0", "text": "#283618", "accent": "#DDA15E", "sub": "#BC6C25"},

    # --- 11-20: Açık Griler ve Gümüş ---
    {"bg": "#E9ECEF", "text": "#212529", "accent": "#495057", "sub": "#ADB5BD"},
    {"bg": "#E0E1DD", "text": "#0D1B2A", "accent": "#415A77", "sub": "#778DA9"},
    {"bg": "#D6D6D6", "text": "#1A1A1A", "accent": "#000000", "sub": "#4D4D4D"},
    {"bg": "#E5E5E5", "text": "#14213D", "accent": "#FCA311", "sub": "#8D99AE"},
    {"bg": "#DFE7FD", "text": "#03045E", "accent": "#0077B6", "sub": "#00B4D8"},
    {"bg": "#EAE2B7", "text": "#003049", "accent": "#D62828", "sub": "#F77F00"},
    {"bg": "#D8E2DC", "text": "#2F3E46", "accent": "#FFCAD4", "sub": "#B5838D"},
    {"bg": "#E3D5CA", "text": "#212529", "accent": "#D5BDAF", "sub": "#F5EBE0"},
    {"bg": "#CAD2C5", "text": "#2F3E46", "accent": "#52796F", "sub": "#84A98C"},
    {"bg": "#EAEAEA", "text": "#111111", "accent": "#333333", "sub": "#555555"},

    # --- 21-30: Derin Siyahlar ve Koyu Dramatik ---
    {"bg": "#000000", "text": "#FFFFFF", "accent": "#E63946", "sub": "#A8DADC"},
    {"bg": "#111111", "text": "#F8F9FA", "accent": "#FFD166", "sub": "#06D6A0"},
    {"bg": "#0D1117", "text": "#C9D1D9", "accent": "#58A6FF", "sub": "#8B949E"},
    {"bg": "#121212", "text": "#E0E0E0", "accent": "#BB86FC", "sub": "#03DAC6"},
    {"bg": "#0A0908", "text": "#F2F4F3", "accent": "#A9927D", "sub": "#5E503F"},
    {"bg": "#050505", "text": "#FAFAFA", "accent": "#F72585", "sub": "#4CC9F0"},
    {"bg": "#1A1A1A", "text": "#FFFFFF", "accent": "#D4AF37", "sub": "#C0C0C0"},
    {"bg": "#000000", "text": "#EAEAEA", "accent": "#39FF14", "sub": "#555555"},
    {"bg": "#0F0F0F", "text": "#F5F5F5", "accent": "#FF5733", "sub": "#C70039"},
    {"bg": "#080808", "text": "#EFEFEF", "accent": "#00FFFF", "sub": "#008080"},

    # --- 31-40: Kömür, Antrasit ve Füme ---
    {"bg": "#212529", "text": "#F8F9FA", "accent": "#FFC107", "sub": "#6C757D"},
    {"bg": "#2B2D42", "text": "#EDF2F4", "accent": "#EF233C", "sub": "#8D99AE"},
    {"bg": "#1D3557", "text": "#F1FAEE", "accent": "#E63946", "sub": "#457B9D"},
    {"bg": "#264653", "text": "#E9C46A", "accent": "#E76F51", "sub": "#2A9D8F"},
    {"bg": "#22223B", "text": "#F2E9E4", "accent": "#9A8C98", "sub": "#4A4E69"},
    {"bg": "#1B263B", "text": "#E0E1DD", "accent": "#778DA9", "sub": "#415A77"},
    {"bg": "#343A40", "text": "#E9ECEF", "accent": "#17A2B8", "sub": "#ADB5BD"},
    {"bg": "#2C3E50", "text": "#ECF0F1", "accent": "#E74C3C", "sub": "#95A5A6"},
    {"bg": "#333333", "text": "#F3F3F3", "accent": "#E84545", "sub": "#903749"},
    {"bg": "#1E1E24", "text": "#FFF8F0", "accent": "#92140C", "sub": "#111D4A"},

    # --- 41-50: Sıcak Kremler ve Fildişi ---
    {"bg": "#F4E7C5", "text": "#2C1810", "accent": "#8B6914", "sub": "#6B4F12"},
    {"bg": "#FDF6E3", "text": "#1C1008", "accent": "#B8860B", "sub": "#8B6914"},
    {"bg": "#FFF3E0", "text": "#1A0800", "accent": "#E65100", "sub": "#F57C00"},
    {"bg": "#FFF8DC", "text": "#2E1A0F", "accent": "#DAA520", "sub": "#B8860B"},
    {"bg": "#FAEBD7", "text": "#3E2723", "accent": "#D84315", "sub": "#BF360C"},
    {"bg": "#FFFFF0", "text": "#111111", "accent": "#FF4500", "sub": "#FF8C00"},
    {"bg": "#F5F5DC", "text": "#2F4F4F", "accent": "#556B2F", "sub": "#8B4513"},
    {"bg": "#FAF0E6", "text": "#1A1A1A", "accent": "#A0522D", "sub": "#D2691E"},
    {"bg": "#FFF5EE", "text": "#2B2B2B", "accent": "#CD5C5C", "sub": "#F08080"},
    {"bg": "#F0FFF0", "text": "#000000", "accent": "#228B22", "sub": "#32CD32"},

    # --- 51-60: Bej, Kum ve Ahşap Tonları ---
    {"bg": "#EAD7A1", "text": "#1A1208", "accent": "#7A5C10", "sub": "#5C4510"},
    {"bg": "#D4A373", "text": "#FAEDCD", "accent": "#CCD5AE", "sub": "#E9EDC9"},
    {"bg": "#F5ECD7", "text": "#2C1810", "accent": "#A0522D", "sub": "#8B4513"},
    {"bg": "#E3D5CA", "text": "#212529", "accent": "#D5BDAF", "sub": "#D6CCC2"},
    {"bg": "#CDB4DB", "text": "#2B2D42", "accent": "#FFC8DD", "sub": "#FFAFCC"},
    {"bg": "#E9C46A", "text": "#264653", "accent": "#E76F51", "sub": "#F4A261"},
    {"bg": "#F4A261", "text": "#264653", "accent": "#E9C46A", "sub": "#2A9D8F"},
    {"bg": "#DDA15E", "text": "#283618", "accent": "#FEFAE0", "sub": "#BC6C25"},
    {"bg": "#A9927D", "text": "#0A0908", "accent": "#5E503F", "sub": "#F2F4F3"},
    {"bg": "#C89F9C", "text": "#4A4E69", "accent": "#F2E9E4", "sub": "#9A8C98"},

    # --- 61-70: Kahverengi, Toprak ve Çikolata ---
    {"bg": "#4A3728", "text": "#F5E6D3", "accent": "#D4A373", "sub": "#C49A6C"},
    {"bg": "#3E2723", "text": "#D7CCC8", "accent": "#FF7043", "sub": "#8D6E63"},
    {"bg": "#2C1810", "text": "#F4E7C5", "accent": "#8B6914", "sub": "#A0522D"},
    {"bg": "#3B2F2F", "text": "#E6E2DD", "accent": "#C4A484", "sub": "#8B7355"},
    {"bg": "#5C4033", "text": "#F5F5DC", "accent": "#D2B48C", "sub": "#DEB887"},
    {"bg": "#654321", "text": "#FFE4C4", "accent": "#8B4513", "sub": "#A0522D"},
    {"bg": "#483C32", "text": "#FFF8DC", "accent": "#C19A6B", "sub": "#8B4513"},
    {"bg": "#3D2B1F", "text": "#EEDD82", "accent": "#B8860B", "sub": "#DAA520"},
    {"bg": "#493D26", "text": "#F0E68C", "accent": "#D4AF37", "sub": "#BDB76B"},
    {"bg": "#2B1B17", "text": "#E5E4E2", "accent": "#C0C0C0", "sub": "#736F6E"},

    # --- 71-80: Kiremit, Bakır ve Rustik ---
    {"bg": "#9C2A00", "text": "#FDECEF", "accent": "#FFB347", "sub": "#E6873C"},
    {"bg": "#8A3324", "text": "#FDF5E6", "accent": "#E9967A", "sub": "#CD5C5C"},
    {"bg": "#B22222", "text": "#FFFAFA", "accent": "#FF6347", "sub": "#CD5C5C"},
    {"bg": "#A0522D", "text": "#FFFFF0", "accent": "#D2691E", "sub": "#CD853F"},
    {"bg": "#8B4513", "text": "#FFF5EE", "accent": "#F4A460", "sub": "#D2B48C"},
    {"bg": "#D2691E", "text": "#1A1A1A", "accent": "#8B4513", "sub": "#A0522D"},
    {"bg": "#CD5C5C", "text": "#FFFFFF", "accent": "#8B0000", "sub": "#B22222"},
    {"bg": "#E9967A", "text": "#2F4F4F", "accent": "#8B0000", "sub": "#A52A2A"},
    {"bg": "#FF7F50", "text": "#191970", "accent": "#FF4500", "sub": "#DC143C"},
    {"bg": "#8B3A3A", "text": "#FFE4E1", "accent": "#FFC0CB", "sub": "#FFB6C1"},

    # --- 81-90: Pastel Pembe ve Yumuşak Tonlar ---
    {"bg": "#FFF0F3", "text": "#3D0010", "accent": "#C9184A", "sub": "#FF4D6D"},
    {"bg": "#FDF2F8", "text": "#2D0A1E", "accent": "#9D174D", "sub": "#BE185D"},
    {"bg": "#FCE4EC", "text": "#1A0010", "accent": "#AD1457", "sub": "#C2185B"},
    {"bg": "#FFC8DD", "text": "#2B2D42", "accent": "#CDB4DB", "sub": "#FFAFCC"},
    {"bg": "#FFE4E1", "text": "#8B0000", "accent": "#CD5C5C", "sub": "#F08080"},
    {"bg": "#FFB6C1", "text": "#2F4F4F", "accent": "#FF1493", "sub": "#C71585"},
    {"bg": "#FF69B4", "text": "#FFFFFF", "accent": "#C71585", "sub": "#FF1493"},
    {"bg": "#DB7093", "text": "#FFF0F5", "accent": "#C71585", "sub": "#FF69B4"},
    {"bg": "#F8B195", "text": "#355C7D", "accent": "#F67280", "sub": "#C06C84"},
    {"bg": "#FFDAB9", "text": "#191970", "accent": "#FF8C00", "sub": "#FFA500"},

    # --- 91-100: Bordo, Şarap ve Kırmızı ---
    {"bg": "#4A0404", "text": "#FDE8E8", "accent": "#FF4D4D", "sub": "#E53E3E"},
    {"bg": "#800000", "text": "#FFFAFA", "accent": "#FF0000", "sub": "#DC143C"},
    {"bg": "#8B0000", "text": "#FFFFF0", "accent": "#B22222", "sub": "#CD5C5C"},
    {"bg": "#A52A2A", "text": "#FFF5EE", "accent": "#FF4500", "sub": "#FF6347"},
    {"bg": "#DC143C", "text": "#FFFFFF", "accent": "#8B0000", "sub": "#B22222"},
    {"bg": "#C70039", "text": "#FDFDFD", "accent": "#FF5733", "sub": "#900C3F"},
    {"bg": "#900C3F", "text": "#FAFAFA", "accent": "#C70039", "sub": "#FF5733"},
    {"bg": "#581845", "text": "#F5F5F5", "accent": "#900C3F", "sub": "#C70039"},
    {"bg": "#660000", "text": "#EAEAEA", "accent": "#CC0000", "sub": "#FF0000"},
    {"bg": "#330000", "text": "#CCCCCC", "accent": "#990000", "sub": "#FF3333"},

    # --- 101-110: Leylak ve Lavanta ---
    {"bg": "#F3E8FF", "text": "#1A0A2E", "accent": "#7C3AED", "sub": "#6D28D9"},
    {"bg": "#E6E6FA", "text": "#4B0082", "accent": "#8A2BE2", "sub": "#9370DB"},
    {"bg": "#D8BFD8", "text": "#2F4F4F", "accent": "#800080", "sub": "#DA70D6"},
    {"bg": "#DDA0DD", "text": "#191970", "accent": "#8B008B", "sub": "#9932CC"},
    {"bg": "#EE82EE", "text": "#FFFFFF", "accent": "#800080", "sub": "#9400D3"},
    {"bg": "#FF00FF", "text": "#000000", "accent": "#8A2BE2", "sub": "#9932CC"},
    {"bg": "#BA55D3", "text": "#F0FFF0", "accent": "#4B0082", "sub": "#800080"},
    {"bg": "#9370DB", "text": "#FFFFF0", "accent": "#483D8B", "sub": "#6A5ACD"},
    {"bg": "#8A2BE2", "text": "#F5F5F5", "accent": "#000000", "sub": "#4B0082"},
    {"bg": "#9400D3", "text": "#FFFFFF", "accent": "#FF1493", "sub": "#FF69B4"},

    # --- 111-120: Derin Mor ve Mistik Tonlar ---
    {"bg": "#2D1B69", "text": "#EDE9FE", "accent": "#C4B5FD", "sub": "#A78BFA"},
    {"bg": "#4A0E8F", "text": "#F3E8FF", "accent": "#E9D5FF", "sub": "#D8B4FE"},
    {"bg": "#4B0082", "text": "#E6E6FA", "accent": "#9370DB", "sub": "#BA55D3"},
    {"bg": "#800080", "text": "#FFFFFF", "accent": "#DA70D6", "sub": "#EE82EE"},
    {"bg": "#8B008B", "text": "#FDFDFD", "accent": "#DDA0DD", "sub": "#FF00FF"},
    {"bg": "#1A0A2E", "text": "#F3E8FF", "accent": "#7C3AED", "sub": "#9333EA"},
    {"bg": "#311B92", "text": "#EDE7F6", "accent": "#B39DDB", "sub": "#7E57C2"},
    {"bg": "#4A148C", "text": "#F3E5F5", "accent": "#CE93D8", "sub": "#AB47BC"},
    {"bg": "#2A0845", "text": "#F5F5F5", "accent": "#6441A5", "sub": "#8E2DE2"},
    {"bg": "#190033", "text": "#EAEAEA", "accent": "#6600CC", "sub": "#9933FF"},

    # --- 121-130: Buz Mavisi ve Gök Mavisi ---
    {"bg": "#EFF6FF", "text": "#0A1628", "accent": "#1D4ED8", "sub": "#3B82F6"},
    {"bg": "#E0F4FF", "text": "#023E8A", "accent": "#0077B6", "sub": "#0096C7"},
    {"bg": "#F0F8FF", "text": "#000080", "accent": "#4682B4", "sub": "#5F9EA0"},
    {"bg": "#E6E6FA", "text": "#00008B", "accent": "#0000CD", "sub": "#4169E1"},
    {"bg": "#B0E0E6", "text": "#191970", "accent": "#00BFFF", "sub": "#1E90FF"},
    {"bg": "#ADD8E6", "text": "#000000", "accent": "#0000FF", "sub": "#00BFFF"},
    {"bg": "#87CEEB", "text": "#2F4F4F", "accent": "#4682B4", "sub": "#5F9EA0"},
    {"bg": "#87CEFA", "text": "#1A1A1A", "accent": "#0000CD", "sub": "#0000FF"},
    {"bg": "#00BFFF", "text": "#FFFFFF", "accent": "#000080", "sub": "#00008B"},
    {"bg": "#1E90FF", "text": "#F5F5F5", "accent": "#0000CD", "sub": "#0000FF"},

    # --- 131-140: Lacivert ve Gece Mavisi ---
    {"bg": "#03045E", "text": "#CAF0F8", "accent": "#90E0EF", "sub": "#48CAE4"},
    {"bg": "#023E8A", "text": "#E0F4FF", "accent": "#ADE8F4", "sub": "#90E0EF"},
    {"bg": "#0D1B2A", "text": "#E8F4FD", "accent": "#4A90D9", "sub": "#2E6DA4"},
    {"bg": "#000080", "text": "#F0F8FF", "accent": "#4682B4", "sub": "#5F9EA0"},
    {"bg": "#00008B", "text": "#E6E6FA", "accent": "#4169E1", "sub": "#1E90FF"},
    {"bg": "#191970", "text": "#ADD8E6", "accent": "#00BFFF", "sub": "#87CEEB"},
    {"bg": "#0A192F", "text": "#CCD6F6", "accent": "#64FFDA", "sub": "#8892B0"},
    {"bg": "#172A45", "text": "#E6F1FF", "accent": "#64FFDA", "sub": "#A8B2D1"},
    {"bg": "#001233", "text": "#FFFFFF", "accent": "#FF595E", "sub": "#FFCA3A"},
    {"bg": "#0B132B", "text": "#F5F5F5", "accent": "#5BC0BE", "sub": "#3A506B"},

    # --- 141-150: Turkuaz, Cyan ve Teal ---
    {"bg": "#ECFEFF", "text": "#0A1E1F", "accent": "#0E7490", "sub": "#0891B2"},
    {"bg": "#134E4A", "text": "#F0FDFA", "accent": "#5EEAD4", "sub": "#2DD4BF"},
    {"bg": "#E0FFFF", "text": "#008B8B", "accent": "#00CED1", "sub": "#20B2AA"},
    {"bg": "#AFEEEE", "text": "#2F4F4F", "accent": "#008080", "sub": "#008B8B"},
    {"bg": "#40E0D0", "text": "#FFFFFF", "accent": "#008080", "sub": "#008B8B"},
    {"bg": "#48D1CC", "text": "#000000", "accent": "#008B8B", "sub": "#008080"},
    {"bg": "#00CED1", "text": "#FAFAFA", "accent": "#008B8B", "sub": "#008080"},
    {"bg": "#008B8B", "text": "#E0FFFF", "accent": "#40E0D0", "sub": "#48D1CC"},
    {"bg": "#008080", "text": "#F5F5F5", "accent": "#20B2AA", "sub": "#48D1CC"},
    {"bg": "#2F4F4F", "text": "#AFEEEE", "accent": "#00CED1", "sub": "#40E0D0"},

    # --- 151-160: Nane, Adaçayı ve Açık Yeşil ---
    {"bg": "#ECFDF5", "text": "#0A2618", "accent": "#065F46", "sub": "#059669"},
    {"bg": "#F0FFF4", "text": "#0A2E14", "accent": "#2D6A4F", "sub": "#40916C"},
    {"bg": "#F5FFFA", "text": "#2E8B57", "accent": "#3CB371", "sub": "#8FBC8F"},
    {"bg": "#F0FFF0", "text": "#006400", "accent": "#228B22", "sub": "#32CD32"},
    {"bg": "#98FB98", "text": "#000000", "accent": "#008000", "sub": "#006400"},
    {"bg": "#90EE90", "text": "#1A1A1A", "accent": "#228B22", "sub": "#32CD32"},
    {"bg": "#8FBC8F", "text": "#FFFFFF", "accent": "#2E8B57", "sub": "#3CB371"},
    {"bg": "#3CB371", "text": "#FDFDFD", "accent": "#006400", "sub": "#008000"},
    {"bg": "#2E8B57", "text": "#F5FFFA", "accent": "#3CB371", "sub": "#8FBC8F"},
    {"bg": "#E9EDC9", "text": "#4A5D23", "accent": "#A3B18A", "sub": "#588157"},

    # --- 161-170: Orman Yeşili ve Zeytin ---
    {"bg": "#0D1F0D", "text": "#E8F5E8", "accent": "#4ADE80", "sub": "#22C55E"},
    {"bg": "#3B4A2F", "text": "#F0F5E8", "accent": "#A8C570", "sub": "#8BAF4E"},
    {"bg": "#556B2F", "text": "#F5F0E0", "accent": "#F0E68C", "sub": "#DAA520"},
    {"bg": "#006400", "text": "#F0FFF0", "accent": "#32CD32", "sub": "#228B22"},
    {"bg": "#008000", "text": "#FFFFFF", "accent": "#90EE90", "sub": "#98FB98"},
    {"bg": "#228B22", "text": "#FAFAFA", "accent": "#006400", "sub": "#008000"},
    {"bg": "#32CD32", "text": "#000000", "accent": "#006400", "sub": "#008000"},
    {"bg": "#6B8E23", "text": "#F5F5F5", "accent": "#556B2F", "sub": "#808000"},
    {"bg": "#808000", "text": "#FFFFF0", "accent": "#BDB76B", "sub": "#6B8E23"},
    {"bg": "#1A4314", "text": "#D9F0D3", "accent": "#5A9367", "sub": "#446DF6"},

    # --- 171-180: Hardal, Altın ve Sarı Tonlar ---
    {"bg": "#FFFDE7", "text": "#4E342E", "accent": "#FBC02D", "sub": "#F57F17"},
    {"bg": "#FFF9C4", "text": "#3E2723", "accent": "#F9A825", "sub": "#F57F17"},
    {"bg": "#FFF59D", "text": "#212121", "accent": "#F57F17", "sub": "#E65100"},
    {"bg": "#FFEB3B", "text": "#000000", "accent": "#FF9800", "sub": "#F57C00"},
    {"bg": "#FBC02D", "text": "#1A1A1A", "accent": "#E65100", "sub": "#BF360C"},
    {"bg": "#F9A825", "text": "#FAFAFA", "accent": "#D84315", "sub": "#BF360C"},
    {"bg": "#F57F17", "text": "#FFFFFF", "accent": "#BF360C", "sub": "#3E2723"},
    {"bg": "#FFD700", "text": "#2C3E50", "accent": "#E74C3C", "sub": "#C0392B"},
    {"bg": "#DAA520", "text": "#F0F8FF", "accent": "#8B0000", "sub": "#B22222"},
    {"bg": "#B8860B", "text": "#F5F5DC", "accent": "#556B2F", "sub": "#8B4513"},

    # --- 181-190: Günbatımı, Turuncu ve Somon ---
    {"bg": "#FFF3E0", "text": "#E65100", "accent": "#FF9800", "sub": "#FFB74D"},
    {"bg": "#FFE0B2", "text": "#BF360C", "accent": "#F57C00", "sub": "#FF9800"},
    {"bg": "#FFCC80", "text": "#1A1A1A", "accent": "#E65100", "sub": "#F57C00"},
    {"bg": "#FFB74D", "text": "#000000", "accent": "#D84315", "sub": "#E65100"},
    {"bg": "#FFA726", "text": "#FFFFFF", "accent": "#BF360C", "sub": "#D84315"},
    {"bg": "#FF9800", "text": "#FAFAFA", "accent": "#E65100", "sub": "#BF360C"},
    {"bg": "#FB8C00", "text": "#F5F5F5", "accent": "#D84315", "sub": "#BF360C"},
    {"bg": "#F57C00", "text": "#EAEAEA", "accent": "#BF360C", "sub": "#3E2723"},
    {"bg": "#EF6C00", "text": "#F0F0F0", "accent": "#E65100", "sub": "#3E2723"},
    {"bg": "#E65100", "text": "#FFFFFF", "accent": "#BF360C", "sub": "#212121"},

    # --- 191-200: Cyberpunk, Neon ve Ekstrem Kontrast ---
    {"bg": "#0D0B14", "text": "#FFFFFF", "accent": "#FF007F", "sub": "#00F0FF"},
    {"bg": "#120458", "text": "#F5F5F5", "accent": "#FF00E4", "sub": "#00FFFF"},
    {"bg": "#050014", "text": "#E0E0E0", "accent": "#00FF66", "sub": "#FF003C"},
    {"bg": "#1A0021", "text": "#FAFAFA", "accent": "#FF0055", "sub": "#00E5FF"},
    {"bg": "#000B18", "text": "#FFFFFF", "accent": "#FF9900", "sub": "#00FFCC"},
    {"bg": "#1C1C1C", "text": "#F3F3F3", "accent": "#FFE800", "sub": "#FF0044"},
    {"bg": "#0A0A0A", "text": "#FFFFFF", "accent": "#00FF9D", "sub": "#7000FF"},
    {"bg": "#220033", "text": "#EEEEEE", "accent": "#FF007A", "sub": "#00F5FF"},
    {"bg": "#0F001A", "text": "#F0F0F0", "accent": "#00FFEA", "sub": "#FF0055"},
    {"bg": "#111111", "text": "#FFFFFF", "accent": "#FF3366", "sub": "#20E3B2"},
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
