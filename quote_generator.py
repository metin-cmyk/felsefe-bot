# -*- coding: utf-8 -*-
import os, re, random, logging, json, time
from datetime import datetime
from pathlib import Path
import anthropic
from google import genai

try:
    from db import query as db_query, execute as db_execute
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    db_query  = lambda *a, **k: None
    db_execute= lambda *a, **k: None

try:
    from quote_sources import fetch_all_quotes
    MULTI_SOURCE = True
except ImportError:
    MULTI_SOURCE = False

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AI İstemcilerini Başlat (Claude + Gemini Ortak Akıl)
# ---------------------------------------------------------------------------
try:
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
except Exception as _e:
    claude_client = None
    log.warning("Claude istemcisi baslatilamadi: %s" % _e)

try:
    gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as _e:
    gemini_client = None
    log.warning("Gemini istemcisi baslatilamadi: %s" % _e)

# ---------------------------------------------------------------------------
# Veritabanı ve Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------
def _get_ataturk_quote():
    if DB_AVAILABLE:
        try:
            recent = _load_recent_quotes(30)
            rows = db_query(
                "SELECT soz, akim, kaynak, hashtags, aciklama FROM sozler "
                "WHERE filozof_ad = %s AND dil = 'tr' ORDER BY RAND() LIMIT 20",
                ("Mustafa Kemal Atatürk",)
            )
            if rows:
                for row in rows:
                    if row["soz"][:60] not in recent:
                        return {
                            "quote":    row["soz"],
                            "author":   "Mustafa Kemal Atatürk",
                            "akim":     row["akim"] or "Türk Düşünce Tarihi",
                            "kaynak":   row["kaynak"] or "",
                            "hashtags": row["hashtags"] or "#Ataturk #Felsefe #Bilgelik",
                            "aciklama": row["aciklama"] or "",
                            "twitter":  row["soz"][:200] + " — Mustafa Kemal Atatürk",
                        }
                row = rows[0]
                return {
                    "quote":    row["soz"],
                    "author":   "Mustafa Kemal Atatürk",
                    "akim":     row["akim"] or "Türk Düşünce Tarihi",
                    "kaynak":   row["kaynak"] or "",
                    "hashtags": row["hashtags"] or "#Ataturk #Felsefe #Bilgelik",
                    "aciklama": row["aciklama"] or "",
                    "twitter":  row["soz"][:200] + " — Mustafa Kemal Atatürk",
                }
        except Exception as e:
            log.error("DB Ataturk soz hatasi: %s" % e)
    return None

def _load_recent_authors(n=15):
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT filozof_ad FROM yayinlar ORDER BY yayinlandi_at DESC LIMIT %s", (n,))
            if rows is not None:
                return set(r["filozof_ad"] for r in rows if r["filozof_ad"])
        except Exception as e:
            log.warning("DB recent_authors hatası: %s" % e)
    try:
        pf = Path("posted.json")
        if not pf.exists(): return set()
        posted = json.loads(pf.read_text(encoding="utf-8"))
        return set(p.get("author", "") for p in posted[-n:])
    except Exception:
        return set()

def _load_recent_quotes(n=30):
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT soz_ozet FROM yayinlar ORDER BY yayinlandi_at DESC LIMIT %s", (n,))
            if rows is not None:
                return set(r["soz_ozet"] for r in rows if r["soz_ozet"])
        except Exception as e:
            log.warning("DB recent_quotes hatası: %s" % e)
    try:
        pf = Path("posted.json")
        if not pf.exists(): return set()
        posted = json.loads(pf.read_text(encoding="utf-8"))
        return set(p.get("quote", "")[:60] for p in posted[-n:])
    except Exception:
        return set()

def _get_akimlar():
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT ad FROM akimlar ORDER BY RAND()")
            if rows: return [r["ad"] for r in rows]
        except Exception as e:
            log.warning("DB akimlar hatası: %s" % e)
    return ["Stoacılık", "Varoluşçuluk", "Antik Yunan Felsefesi", "Budizm", "Rasyonalizm", "Empirizm", "Fenomenoloji", "Absürdizm", "Pragmatizm", "Nihilizm", "Taoizm"]

def _get_random_filozof(akim, exclude=None):
    exclude = exclude or set()
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT ad FROM filozoflar WHERE akim = %s ORDER BY RAND() LIMIT 20", (akim,))
            if rows:
                candidates = [r["ad"] for r in rows if r["ad"] not in exclude]
                if candidates: return random.choice(candidates)
            rows2 = db_query("SELECT ad FROM filozoflar ORDER BY RAND() LIMIT 20")
            if rows2:
                candidates2 = [r["ad"] for r in rows2 if r["ad"] not in exclude]
                if candidates2: return random.choice(candidates2)
        except Exception as e:
            log.warning("DB filozof hatası: %s" % e)
    _fallback_filozoflar = ["Sokrates", "Platon", "Aristoteles", "Marcus Aurelius", "Epiktetos", "Friedrich Nietzsche", "Albert Camus", "Jean-Paul Sartre", "Immanuel Kant", "Arthur Schopenhauer", "Seneca", "Epikür"]
    candidates = [f for f in _fallback_filozoflar if f not in exclude]
    return random.choice(candidates) if candidates else "Sokrates"

def _get_random_konu():
    if DB_AVAILABLE:
        try:
            row = db_query("SELECT konu FROM konular ORDER BY RAND() LIMIT 1", fetchone=True)
            if row: return row["konu"]
        except Exception as e:
            log.warning("DB konu hatası: %s" % e)
    return random.choice(["Hayatın anlamı ve özgürlük", "Ölüm ve varoluş", "Aşk ve insan doğası", "Bilgi ve hakikat", "Ahlak ve erdem", "Toplum ve birey"])

def _db_get_unused_quote():
    if not DB_AVAILABLE: return None
    try:
        recent_authors = _load_recent_authors(15)
        recent_quotes  = _load_recent_quotes(30)
        rows = db_query(
            """SELECT s.id, s.filozof_ad, s.soz, s.akim, s.hashtags, s.aciklama, s.kaynak
               FROM sozler s
               WHERE s.dil = 'tr' AND s.dogrulanmis = 1 AND s.filozof_ad != 'Mustafa Kemal Atatürk'
                 AND s.soz_ozet NOT IN (SELECT COALESCE(soz_ozet,'') FROM yayinlar ORDER BY yayinlandi_at DESC LIMIT 30)
               ORDER BY RAND() LIMIT 20"""
        )
        if not rows:
            rows = db_query("SELECT s.id, s.filozof_ad, s.soz, s.akim, s.hashtags, s.aciklama, s.kaynak FROM sozler s WHERE s.dil = 'tr' AND s.dogrulanmis = 1 AND s.filozof_ad != 'Mustafa Kemal Atatürk' ORDER BY RAND() LIMIT 10")
        if not rows: return None

        for row in rows:
            if row["filozof_ad"] in recent_authors or row["soz"][:60] in recent_quotes: continue
            return {
                "quote": row["soz"], "author": row["filozof_ad"], "akim": row["akim"] or "Felsefe",
                "hashtags": row["hashtags"] or "#Felsefe #Bilgelik", "aciklama": row["aciklama"] or "",
                "kaynak": row["kaynak"] or "", "twitter": row["soz"][:200] + " — " + row["filozof_ad"],
            }
        row = rows[0]
        return {
            "quote": row["soz"], "author": row["filozof_ad"], "akim": row["akim"] or "Felsefe",
            "hashtags": row["hashtags"] or "#Felsefe #Bilgelik", "aciklama": row["aciklama"] or "",
            "kaynak": row["kaynak"] or "", "twitter": row["soz"][:200] + " — " + row["filozof_ad"],
        }
    except Exception as e:
        log.error("DB soz cekme hatasi: %s" % e)
        return None

def _db_save_quote(result):
    if not DB_AVAILABLE or not result: return
    try:
        db_execute(
            """INSERT IGNORE INTO sozler (filozof_ad, soz, akim, hashtags, aciklama, dil, dogrulanmis, kaynak_site)
               VALUES (%s, %s, %s, %s, %s, 'tr', 1, 'wikiquote')""",
            (result.get("author", ""), result.get("quote", ""), result.get("akim", ""), result.get("hashtags", ""), result.get("aciklama", ""))
        )
    except Exception as e:
        log.warning("DB soz kayit hatasi: %s" % e)

# ---------------------------------------------------------------------------
# ANA ÜRETİM FONKSİYONU
# ---------------------------------------------------------------------------
def generate_quote():
    bugun = datetime.now()
    if (bugun.month == 11 and bugun.day == 10) or (bugun.month == 10 and bugun.day == 29) or (bugun.month == 8 and bugun.day == 30) or (bugun.month == 5 and bugun.day == 19) or (bugun.month == 4 and bugun.day == 23) or random.random() < 0.20:
        ataturk_sozu = _get_ataturk_quote()
        if ataturk_sozu: return ataturk_sozu

    db_result = _db_get_unused_quote()
    if db_result:
        log.info("DB'den doğrudan söz kullanılıyor: %s" % db_result["author"])
        return db_result

    log.info("DB'de uygun soz yok, kaynaktan cekilecek...")
    recent_authors = _load_recent_authors(15)
    recent_quotes  = _load_recent_quotes(30)
    akimlar_list = _get_akimlar()
    
    for _ in range(20):
        akim = random.choice(akimlar_list)
        filozof = _get_random_filozof(akim, exclude=recent_authors)
        if filozof not in recent_authors: break
    konu = _get_random_konu()

    MAX_DENEME = 8
    for deneme in range(MAX_DENEME):
        if MULTI_SOURCE:
            real_quotes = fetch_all_quotes(filozof)
        else:
            real_quotes, _ = _fetch_real_quotes_from_wikipedia(filozof)

        if real_quotes:
            filtered = [q for q in real_quotes if q[:60] not in recent_quotes]
            if not filtered: filtered = real_quotes

            raw = _select_best_quote(filozof, akim, konu, filtered)
            result = _parse(raw, filozof, akim)
            
            if result and result.get("quote"):
                if result["quote"][:60] not in recent_quotes:
                    _db_save_quote(result)
                    return result

        log.warning("Soz bulunamadi: %s (%d/%d)" % (filozof, deneme+1, MAX_DENEME))
        akim = random.choice(akimlar_list)
        filozof = _get_random_filozof(akim, exclude=recent_authors)
        konu = _get_random_konu()

    log.error("8 denemede de gercek soz bulunamadi.")
    return None

def _clean_quotes(text):
    text = text.strip()
    for q in ['\u201c', '\u201d', '\u2018', '\u2019', '"', "'"]:
        if text.startswith(q): text = text[1:]
        if text.endswith(q): text = text[:-1]
    return text.strip()

def _parse(text, default_autor, default_akim):
    def get(key):
        m = re.search(rf"{key}:\n(.*?)(?:\n---|\Z)", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    quote = _clean_quotes(get("SOZ"))
    if not quote or len(quote.strip()) < 10 or not _is_turkish(quote): return None

    author = get("YAZAR")
    if not author or "az bilinen" in author.lower(): author = default_autor
    
    return {
        "quote": quote, "author": author, "akim": get("AKIM") or default_akim,
        "hashtags": get("HASHTAG") or "#Felsefe #Bilgelik", "aciklama": get("ACIKLAMA"),
        "twitter": get("TWITTER") or f"{quote}\n\n— {author}"
    }

# ---------------------------------------------------------------------------
# AI SEÇİM FONKSİYONU (CLAUDE + GEMINI)
# ---------------------------------------------------------------------------
def _select_best_quote(philosopher, akim, konu, quotes_list):
    quotes_text = "\n".join(["  %d. %s" % (i+1, q) for i, q in enumerate(quotes_list)])

    system_instruction = """Sen uzman bir felsefe editörüsün. Sana filozofun GERÇEK sözleri verilecek.
Görev: Listeden konuya EN UYGUN sözü seç, MUTLAKA Türkçeye çevir ve formatla.

KESİN KURALLAR:
1. Listede OLMAYAN söz uydurma. Tırnak işareti kullanma.
2. ACIKLAMA kısmında; sözün felsefi arka planını ve modern insan için taşıdığı anlamı inceleyen EN AZ 3-4 PARAGRAFTAN oluşan, derinlikli bir makale yaz.

Yanıt formatı:
SOZ:
[Söz]
---
YAZAR:
[Yazar]
---
AKIM:
[Akım]
---
HASHTAG:
[#Felsefe vb.]
---
ACIKLAMA:
[En az 3 paragraf felsefi yorum]
---
TWITTER:
[Türkçe söz tırnaksız — Yazar Adı]"""

    prompt_content = f"Dusunur: {philosopher}\nAkim: {akim}\nKonu: {konu}\n\nGERCEK sozler listesi:\n{quotes_text}"

    # 1. Claude
    if claude_client:
        try:
            msg = claude_client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=900, system=system_instruction,
                messages=[{"role": "user", "content": prompt_content}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            log.warning("Claude API hatasi: %s. Gemini'ye geciliyor..." % e)

    # 2. Gemini (Yeni Kütüphane)
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"{system_instruction}\n\n{prompt_content}"
            )
            return response.text.strip()
        except Exception as e:
            log.warning("Gemini API hatasi: %s. Fallback'e geciliyor..." % e)

    # 3. Fallback
    log.warning("Her iki AI de basarisiz, manuel secim yapiliyor.")
    result = _fallback_format(philosopher, akim, quotes_list)
    return result or ""

# ---------------------------------------------------------------------------
# KAZIMA (SCRAPING) VE DİĞER YARDIMCILAR
# ---------------------------------------------------------------------------
def _name_variants(name):
    variants = [name]
    parts = name.strip().split()
    if len(parts) >= 2:
        variants.extend([parts[-1], parts[0], "%s %s" % (parts[-1], parts[0])])
    m = re.search(r"\(([^)]+)\)", name)
    if m:
        variants.extend([name[:name.index("(")].strip(), m.group(1).strip()])
    return list(dict.fromkeys(filter(None, variants)))

def _fetch_wikiquote(philosopher):
    import requests as _req
    def _parse_wikitext(wikitext):
        quotes = []
        for line in wikitext.split("\n"):
            s = line.strip()
            if not s.startswith("*") or s.startswith("**"): continue
            clean = s.lstrip("* ").strip()
            clean = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", clean)
            clean = re.sub(r"\{\{[^}]*\}\}", "", clean)
            clean = re.sub(r"<ref[^>]*>.*?</ref>", "", clean, flags=re.DOTALL)
            clean = re.sub(r"<[^>]+>", "", clean)
            clean = re.sub(r"('''|'')", "", clean).strip().strip('"').strip("\'").strip()
            if 25 < len(clean) < 400: quotes.append(clean)
        return quotes

    name_variants = _name_variants(philosopher)
    for lang in ("tr", "en"):
        for name in name_variants:
            try:
                r = _req.get("https://%s.wikiquote.org/w/api.php" % lang, params={"action": "parse", "page": name, "prop": "wikitext", "format": "json"}, timeout=12)
                if r.status_code == 200 and "error" not in r.json():
                    quotes = _parse_wikitext(r.json().get("parse", {}).get("wikitext", {}).get("*", ""))
                    if quotes: return quotes[:25]
            except Exception:
                pass
    return []

def _fetch_azquotes(philosopher):
    import requests as _req, html as _html
    try:
        slug = re.sub(r"[^a-z0-9]+", "-", philosopher.lower()).strip("-")
        r = _req.get("https://www.azquotes.com/author/%s" % slug, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if r.status_code == 200:
            quotes = [_html.unescape(q.strip()) for q in re.findall(r'<a[^>]+class="title"[^>]*>([^<]{20,350})</a>', r.text) if len(q.strip()) > 20]
            if quotes: return quotes[:20]
    except Exception: pass
    return []

def _fetch_goodreads(philosopher):
    import requests as _req, html as _html
    from urllib.parse import quote as _uq
    try:
        r = _req.get("https://www.goodreads.com/quotes/search?q=%s" % _uq(philosopher), headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if r.status_code == 200:
            quotes = []
            for block in re.findall(r'<div\s+class="quoteText">(.*?)</div>', r.text, re.DOTALL):
                text = _html.unescape(re.sub(r"<[^>]+>", "", block)).strip()
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if lines:
                    quote_text = lines[0].strip('""\u201c\u201d\u2018\u2019').strip()
                    if 25 < len(quote_text) < 400: quotes.append(quote_text)
            if quotes: return quotes[:20]
    except
