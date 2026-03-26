# -*- coding: utf-8 -*-
import os, re, random, logging, json, time
from datetime import datetime
from pathlib import Path
import anthropic
from google import genai

# Çevirmen kütüphanesi
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

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

try:
    gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as _e:
    gemini_client = None

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
            pass
    try:
        pf = Path("posted.json")
        if not pf.exists(): 
            return set()
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
            pass
    try:
        pf = Path("posted.json")
        if not pf.exists(): 
            return set()
        posted = json.loads(pf.read_text(encoding="utf-8"))
        return set(p.get("quote", "")[:60] for p in posted[-n:])
    except Exception:
        return set()

def _get_akimlar():
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT ad FROM akimlar ORDER BY RAND()")
            if rows: 
                return [r["ad"] for r in rows]
        except Exception as e:
            pass
    return ["Stoacılık", "Varoluşçuluk", "Antik Yunan Felsefesi", "Budizm", "Rasyonalizm", "Empirizm", "Fenomenoloji", "Absürdizm", "Pragmatizm", "Nihilizm", "Taoizm"]

def _get_random_filozof(akim, exclude=None):
    exclude = exclude or set()
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT ad FROM filozoflar WHERE akim = %s ORDER BY RAND() LIMIT 20", (akim,))
            if rows:
                candidates = [r["ad"] for r in rows if r["ad"] not in exclude]
                if candidates: 
                    return random.choice(candidates)
            rows2 = db_query("SELECT ad FROM filozoflar ORDER BY RAND() LIMIT 20")
            if rows2:
                candidates2 = [r["ad"] for r in rows2 if r["ad"] not in exclude]
                if candidates2: 
                    return random.choice(candidates2)
        except Exception as e:
            pass
    _fallback_filozoflar = ["Sokrates", "Platon", "Aristoteles", "Marcus Aurelius", "Epiktetos", "Friedrich Nietzsche", "Albert Camus", "Jean-Paul Sartre", "Immanuel Kant", "Arthur Schopenhauer", "Seneca", "Epikür"]
    candidates = [f for f in _fallback_filozoflar if f not in exclude]
    if candidates:
        return random.choice(candidates)
    return "Sokrates"

def _get_random_konu():
    if DB_AVAILABLE:
        try:
            row = db_query("SELECT konu FROM konular ORDER BY RAND() LIMIT 1", fetchone=True)
            if row: 
                return row["konu"]
        except Exception as e:
            pass
    return random.choice(["Hayatın anlamı ve özgürlük", "Ölüm ve varoluş", "Aşk ve insan doğası", "Bilgi ve hakikat", "Ahlak ve erdem", "Toplum ve birey"])

def _db_get_unused_quote():
    if not DB_AVAILABLE: 
        return None
    try:
        recent_authors = _load_recent_authors(15)
        recent_quotes  = _load_recent_quotes(30)
        
        rows = db_query(
            """SELECT s.id, s.filozof_ad, s.soz, s.akim, s.hashtags, s.aciklama, s.kaynak
               FROM sozler s
               WHERE s.dil = 'tr' AND s.dogrulanmis = 1 AND s.filozof_ad != 'Mustafa Kemal Atatürk'
               ORDER BY RAND() LIMIT 20"""
        )
        
        if not rows: 
            return None

        for row in rows:
            if row["filozof_ad"] in recent_authors or row["soz"][:60] in recent_quotes: 
                continue
            return {
                "quote": row["soz"], "author": row["filozof_ad"], "akim": row["akim"] or "Felsefe",
                "hashtags": row["hashtags"] or "#Felsefe #Bilgelik", "aciklama": row["aciklama"] or "",
                "kaynak": row["kaynak"] or "", "twitter": row["soz"][:200] + " — " + row["filozof_ad"],
            }
        return None
    except Exception as e:
        return None

def _db_save_quote(result):
    if not DB_AVAILABLE or not result: 
        return
    try:
        db_execute(
            """INSERT IGNORE INTO sozler (filozof_ad, soz, akim, hashtags, aciklama, dil, dogrulanmis, kaynak_site)
               VALUES (%s, %s, %s, %s, %s, 'tr', 1, 'wikiquote')""",
            (result.get("author", ""), result.get("quote", ""), result.get("akim", ""), result.get("hashtags", ""), result.get("aciklama", ""))
        )
    except Exception as e:
        pass

# ---------------------------------------------------------------------------
# DİL TESPİTİ (TAMAMEN GÜÇLENDİRİLDİ)
# ---------------------------------------------------------------------------
def _is_turkish(text):
    if not text or len(text.strip()) < 3: 
        return False
    words = set(text.lower().split())
    
    # 1. İngilizce bariz kelimeler varsa DİREKT YABANCI say!
    foreign_words = {"the","is","are","was","were","and","of","to","in","that","it","for","on","with","as","you","do","at","this","but","his","by","from","they","we","say","her","she","or","an","will","my","one","all","would","there","their","what","out","if","about","who","get","which","go","me"}
    
    # Eğer 2 tane bile İngilizce kelime yakalarsak İngilizcedir (Kesin Ret)
    if len(words & foreign_words) >= 2:
        return False

    # 2. Türkçe'ye has karakterler varsa %99 Türkçedir
    turkce_chars = set("çşğüöıÇŞĞÜÖİ")
    if any(c in text for c in turkce_chars): 
        return True

    # 3. Yaygın Türkçe kelimeler
    turkce_words = {"ve","bir","bu","da","de","ile","için","ama","çünkü","eğer","olan","değil","gibi","kadar","daha","çok","her","biz","ben","sen","var","yok","en","göre","sonra","olarak","kendi","hiç","ne","o","şu","diye","bile"}
    if len(words & turkce_words) >= 1: 
        return True
        
    return False

# ---------------------------------------------------------------------------
# ANA ÜRETİM FONKSİYONU
# ---------------------------------------------------------------------------
def generate_quote():
    bugun = datetime.now()
    if (bugun.month == 11 and bugun.day == 10) or (bugun.month == 10 and bugun.day == 29) or (bugun.month == 8 and bugun.day == 30) or (bugun.month == 5 and bugun.day == 19) or (bugun.month == 4 and bugun.day == 23) or random.random() < 0.20:
        ataturk_sozu = _get_ataturk_quote()
        if ataturk_sozu: 
            return ataturk_sozu

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
        if filozof not in recent_authors: 
            break
            
    konu = _get_random_konu()

    MAX_DENEME = 8
    for deneme in range(MAX_DENEME):
        time.sleep(2) 

        if MULTI_SOURCE:
            real_quotes = fetch_all_quotes(filozof)
        else:
            real_quotes, _ = _fetch_real_quotes_from_wikipedia(filozof)

        if real_quotes:
            filtered = [q for q in real_quotes if q[:60] not in recent_quotes]
            if not filtered: 
                filtered = real_quotes

            raw = _select_best_quote(filozof, akim, konu, filtered)
            result = _parse(raw, filozof, akim)
            
            if result and result.get("quote"):
                if result["quote"][:60] not in recent_quotes:
                    _db_save_quote(result)
                    return result

        log.warning("Soz bulunamadi veya Türkçe yapılamadı: %s (%d/%d)" % (filozof, deneme+1, MAX_DENEME))
        akim = random.choice(akimlar_list)
        filozof = _get_random_filozof(akim, exclude=recent_authors)
        konu = _get_random_konu()

    log.error("8 denemede de soz olusturulamadi.")
    return None

def _clean_quotes(text):
    text = text.strip()
    for q in ['\u201c', '\u201d', '\u2018', '\u2019', '"', "'"]:
        if text.startswith(q): 
            text = text[1:]
        if text.endswith(q): 
            text = text[:-1]
    return text.strip()

def _parse(text, default_autor, default_akim):
    def get(key):
        m = re.search(rf"{key}:\n(.*?)(?:\n---|\Z)", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    quote = _clean_quotes(get("SOZ"))
    
    if not quote or len(quote.strip()) < 5: 
        return None

    # ZORUNLU ÇEVİRİ AŞAMASI (Söz için)
    if TRANSLATOR_AVAILABLE and not _is_turkish(quote):
        try:
            log.info("İngilizce söz tespit edildi, zorla çevriliyor...")
            quote = GoogleTranslator(source='auto', target='tr').translate(quote)
        except Exception as e:
            log.warning("Söz çeviri hatasi: %s" % e)

    # Hala Türkçe değilse hiç yayınlama iptal et
    if not _is_turkish(quote):
        return None

    author = get("YAZAR")
    if not author or "az bilinen" in author.lower(): 
        author = default_autor
    
    # ZORUNLU ÇEVİRİ AŞAMASI (Açıklama için)
    aciklama = get("ACIKLAMA")
    if aciklama and TRANSLATOR_AVAILABLE and not _is_turkish(aciklama):
        try:
            log.info("İngilizce açıklama tespit edildi, zorla çevriliyor...")
            aciklama = GoogleTranslator(source='auto', target='tr').translate(aciklama)
        except:
            pass
            
    # ZORUNLU ÇEVİRİ AŞAMASI (Twitter Metni için)
    twitter_text = get("TWITTER") or f"{quote}\n\n— {author}"
    if twitter_text and TRANSLATOR_AVAILABLE and not _is_turkish(twitter_text):
        try:
            twitter_text = GoogleTranslator(source='auto', target='tr').translate(twitter_text)
        except:
            pass

    return {
        "quote": quote, "author": author, "akim": get("AKIM") or default_akim,
        "hashtags": get("HASHTAG") or "#Felsefe #Bilgelik", "aciklama": aciklama,
        "twitter": twitter_text
    }

# ---------------------------------------------------------------------------
# AI SEÇİM FONKSİYONU
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

    if claude_client:
        try:
            msg = claude_client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=900, system=system_instruction,
                messages=[{"role": "user", "content": prompt_content}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            pass

    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"{system_instruction}\n\n{prompt_content}"
            )
            return response.text.strip()
        except Exception as e:
            pass

    # AI Patlarsa Manuel Çek (İçeride yine otomatik çevrilecek)
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
    except Exception: pass
    return []

def _fetch_felsefe_gen_tr(philosopher):
    import requests as _req, html as _html
    from urllib.parse import quote as _uq
    try:
        r = _req.get("https://felsefe.gen.tr/?s=%s" % _uq(philosopher), headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            quotes = [_html.unescape(re.sub(r"<[^>]+>", "", q)).strip() for q in re.findall(r'<blockquote[^>]*>(.*?)</blockquote>', r.text, re.DOTALL)]
            quotes = [q for q in quotes if 25 < len(q) < 400]
            if quotes: return quotes[:15]
    except Exception: pass
    return []

def _fetch_real_quotes_from_wikipedia(philosopher):
    quotes = _fetch_wikiquote(philosopher)
    if quotes: return quotes, "wikiquote"
    quotes = _fetch_azquotes(philosopher)
    if quotes: return quotes, "azquotes"
    quotes = _fetch_goodreads(philosopher)
    if quotes: return quotes, "goodreads"
    quotes = _fetch_felsefe_gen_tr(philosopher)
    if quotes: return quotes, "felsefe.gen.tr"
    return [], "none"

def _fallback_format(philosopher, akim, quotes_list):
    if not quotes_list: 
        return ""
        
    quotes_list.sort(key=len)
    secim = re.sub(r'[""\u201c\u201d\u2018\u2019«»\']', "", quotes_list[0]).strip()[:250]
    
    if len(secim) < 15: 
        return ""

    # HER İHTİMALE KARŞI İLK AŞAMA ÇEVİRİSİ (ZORUNLU)
    if TRANSLATOR_AVAILABLE:
        try:
            secim = GoogleTranslator(source='auto', target='tr').translate(secim)
        except:
            pass

    akim_tag = re.sub(r"[^a-zA-Z0-9]", "", akim.split("/")[0].strip())
    yt_tag = re.sub(r"[^a-zA-Z0-9]", "", (philosopher.split()[-1] if philosopher else "Felsefe"))
    hashtags = f"#Felsefe #Bilgelik #{akim_tag} #{yt_tag} #DusunenInsan"

    return f"SOZ:\n{secim}\n---\nYAZAR:\n{philosopher}\n---\nAKIM:\n{akim}\n---\nHASHTAG:\n{hashtags}\n---\nACIKLAMA:\n{philosopher}'nin felsefi düşüncesinden önemli bir gözlem.\n---\nTWITTER:\n{secim} — {philosopher}"
