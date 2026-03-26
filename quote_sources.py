# -*- coding: utf-8 -*-
"""
Çok kaynaklı söz toplama motoru — felsefemiz.net
Kaynak önceliği:
  1. Wikiquote TR  (API — Türkçe, doğrulanmış)
  2. Wikiquote EN  (API — İngilizce, çeviri gerekir)
  3. ZenQuotes.io  (Ücretsiz API — yazar filtreli)
  4. BrainyQuote   (Scraping)
  5. AZQuotes      (Scraping)
  6. Goodreads     (Scraping)
  7. QuotesOnDesign(Scraping)
  8. ThoughtCo     (Scraping)
"""
import re, logging, time, random
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _get(url, timeout=12, params=None):
    """Güvenli HTTP GET."""
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        log.warning("HTTP hata [%s]: %s" % (url[:60], e))
        return None

def _clean(text):
    """Söz metnini temizle."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^["\'"«»„"]+|["\'"«»„"]+$', '', text).strip()
    text = text.strip('–—-').strip()
    return text

# ─────────────────────────────────────────────────────────────
# 1. WIKİQUOTE TR — Türkçe API
# ─────────────────────────────────────────────────────────────
def fetch_wikiquote_tr(name):
    """Wikiquote Türkçe — wikitext API ile söz çeker."""
    variants = _name_variants(name)
    for v in variants:
        try:
            r = _get("https://tr.wikiquote.org/w/api.php", params={
                "action": "parse", "page": v,
                "prop": "wikitext", "format": "json"
            })
            if not r: continue
            wikitext = r.json().get("parse", {}).get("wikitext", {}).get("*", "")
            quotes = _parse_wikitext(wikitext)
            if quotes:
                log.info("WikiquoteTR [%s]: %d söz" % (name, len(quotes)))
                return quotes
        except Exception as e:
            log.warning("WikiquoteTR hata [%s]: %s" % (name, e))
    return []

# ─────────────────────────────────────────────────────────────
# 2. WIKİQUOTE EN — İngilizce API
# ─────────────────────────────────────────────────────────────
def fetch_wikiquote_en(name):
    """Wikiquote İngilizce — wikitext API ile söz çeker."""
    variants = _name_variants(name)
    for v in variants:
        try:
            r = _get("https://en.wikiquote.org/w/api.php", params={
                "action": "parse", "page": v,
                "prop": "wikitext", "format": "json"
            })
            if not r: continue
            wikitext = r.json().get("parse", {}).get("wikitext", {}).get("*", "")
            quotes = _parse_wikitext(wikitext)
            if quotes:
                log.info("WikiquoteEN [%s]: %d söz" % (name, len(quotes)))
                return quotes
        except Exception as e:
            log.warning("WikiquoteEN hata [%s]: %s" % (name, e))
    return []

# ─────────────────────────────────────────────────────────────
# 3. ZENQUOTES.IO — Ücretsiz API
# ─────────────────────────────────────────────────────────────
def fetch_zenquotes(name):
    """ZenQuotes API — yazar bazlı söz çeker. 5 req/30sn limit."""
    # Soyadı ile dene
    last_name = name.split()[-1] if name.split() else name
    try:
        r = _get("https://zenquotes.io/api/quotes/author/%s" % last_name.lower())
        if r and r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                quotes = [item.get("q", "") for item in data if item.get("q")]
                quotes = [q for q in quotes if len(q) > 15]
                if quotes:
                    log.info("ZenQuotes [%s]: %d söz" % (name, len(quotes)))
                    return quotes
    except Exception as e:
        log.warning("ZenQuotes hata [%s]: %s" % (name, e))
    return []

# ─────────────────────────────────────────────────────────────
# 4. BRAINYQUOTE — Scraping
# ─────────────────────────────────────────────────────────────
def fetch_brainyquote(name):
    """BrainyQuote'tan yazar sözlerini çeker."""
    slug = name.lower().replace(" ", "_").replace("-", "_")
    slug = re.sub(r'[^a-z_]', '', slug)
    url = "https://www.brainyquote.com/authors/%s_quotes" % slug
    r = _get(url)
    if not r: return []
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        quotes = []
        for tag in soup.select("a.b-qt, .bqQt .b-qt"):
            text = _clean(tag.get_text())
            if text and len(text) > 15:
                quotes.append(text)
        if quotes:
            log.info("BrainyQuote [%s]: %d söz" % (name, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("BrainyQuote hata [%s]: %s" % (name, e))
        return []

# ─────────────────────────────────────────────────────────────
# 5. AZQUOTES — Scraping
# ─────────────────────────────────────────────────────────────
def fetch_azquotes(name):
    """AZQuotes'tan yazar sözlerini çeker."""
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r'[^a-z-]', '', slug)
    url = "https://www.azquotes.com/author/%s" % slug
    r = _get(url)
    if not r: return []
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        quotes = []
        for tag in soup.select(".wrap-block p, .lqquote"):
            text = _clean(tag.get_text())
            if text and len(text) > 15:
                quotes.append(text)
        if not quotes:
            # Alternatif selector
            for tag in soup.select("li.wrap-block"):
                p = tag.find("p")
                if p:
                    text = _clean(p.get_text())
                    if text and len(text) > 15:
                        quotes.append(text)
        if quotes:
            log.info("AZQuotes [%s]: %d söz" % (name, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("AZQuotes hata [%s]: %s" % (name, e))
        return []

# ─────────────────────────────────────────────────────────────
# 6. GOODREADS — Scraping
# ─────────────────────────────────────────────────────────────
def fetch_goodreads(name):
    """Goodreads'tan yazar sözlerini çeker."""
    search_name = "+".join(name.split())
    url = "https://www.goodreads.com/quotes/search?q=%s&commit=Search" % search_name
    r = _get(url)
    if not r: return []
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        quotes = []
        for tag in soup.select(".quoteText"):
            text = tag.get_text()
            # Alıntı kısmını temizle
            text = re.sub(r'―.*', '', text)
            text = _clean(text)
            if text and len(text) > 15:
                quotes.append(text)
        if quotes:
            log.info("Goodreads [%s]: %d söz" % (name, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("Goodreads hata [%s]: %s" % (name, e))
        return []

# ─────────────────────────────────────────────────────────────
# 7. QUOTEFANCY — Scraping
# ─────────────────────────────────────────────────────────────
def fetch_quotefancy(name):
    """QuoteFancy'den yazar sözlerini çeker."""
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r'[^a-z-]', '', slug)
    url = "https://quotefancy.com/%s-quotes" % slug
    r = _get(url)
    if not r: return []
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        quotes = []
        for tag in soup.select(".quote-text, h2.sentence"):
            text = _clean(tag.get_text())
            if text and len(text) > 15:
                quotes.append(text)
        if quotes:
            log.info("QuoteFancy [%s]: %d söz" % (name, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("QuoteFancy hata [%s]: %s" % (name, e))
        return []

# ─────────────────────────────────────────────────────────────
# 8. QUOTESLYFE — Scraping
# ─────────────────────────────────────────────────────────────
def fetch_quoteslyfe(name):
    """QuotesLyfe'dan yazar sözlerini çeker."""
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r'[^a-z-]', '', slug)
    url = "https://www.quoteslyfe.com/quote/%s-quotes" % slug
    r = _get(url)
    if not r: return []
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        quotes = []
        for tag in soup.select(".quoteText, .quote-text, p.quotes"):
            text = _clean(tag.get_text())
            if text and len(text) > 15:
                quotes.append(text)
        if quotes:
            log.info("QuotesLyfe [%s]: %d söz" % (name, len(quotes)))
        return quotes[:15]
    except Exception as e:
        log.warning("QuotesLyfe hata [%s]: %s" % (name, e))
        return []

# ─────────────────────────────────────────────────────────────
# ANA FONKSİYON — Tüm kaynaklardan topla
# ─────────────────────────────────────────────────────────────
def fetch_all_quotes(name):
    """
    Tüm kaynaklardan söz toplar, birleştirir, tekrarları kaldırır.
    Öncelik sırası: WikiTR > WikiEN > ZenQuotes > BrainyQuote > AZQuotes > Goodreads > QuoteFancy
    """
    all_quotes = []
    seen = set()

    sources = [
        ("WikiTR",      fetch_wikiquote_tr),
        ("WikiEN",      fetch_wikiquote_en),
        ("ZenQuotes",   fetch_zenquotes),
        ("BrainyQuote", fetch_brainyquote),
        ("AZQuotes",    fetch_azquotes),
        ("Goodreads",   fetch_goodreads),
        ("QuoteFancy",  fetch_quotefancy),
    ]

    for source_name, func in sources:
        try:
            quotes = func(name)
            new_count = 0
            for q in quotes:
                key = q[:60].lower()
                if key not in seen and len(q) > 15:
                    seen.add(key)
                    all_quotes.append(q)
                    new_count += 1
            if new_count > 0:
                log.info("Kaynak %s: +%d yeni söz eklendi" % (source_name, new_count))
            time.sleep(0.5)  # Rate limit önlemi
        except Exception as e:
            log.warning("Kaynak %s hatası: %s" % (source_name, e))

    log.info("TOPLAM [%s]: %d benzersiz söz, %d kaynak" % (
        name, len(all_quotes), sum(1 for s,_ in sources)))
    return all_quotes

# ─────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────
def _name_variants(name):
    """Filozof adının farklı yazım biçimlerini üret."""
    parts = name.split()
    variants = [name]
    if len(parts) >= 2:
        variants.append(parts[-1])                     # Sadece soyad
        variants.append("%s %s" % (parts[-1], parts[0]))  # Ters sıra
        variants.append("_".join(parts))               # Alt çizgili
    # Türkçe → Latin dönüşümü
    tr_map = str.maketrans("çşğüöıÇŞĞÜÖİ", "csgouiCSGUOI")
    latin = name.translate(tr_map)
    if latin != name:
        variants.append(latin)
    return list(dict.fromkeys(variants))  # Tekrarsız

def _parse_wikitext(wikitext):
    """Wikiquote wikitext'ten sözleri çıkar."""
    if not wikitext:
        return []
    quotes = []
    lines = wikitext.split("\n")
    for line in lines:
        line = line.strip()
        if not line.startswith("*") and not line.startswith("#"):
            continue
        # Wikitext etiketlerini temizle
        text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', line)
        text = re.sub(r"{{[^}]*}}", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"'{2,}", "", text)
        text = re.sub(r"^[*#:;]+\s*", "", text).strip()
        text = _clean(text)
        if len(text) > 20 and len(text) < 600:
            quotes.append(text)
    return quotes
