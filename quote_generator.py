# -*- coding: utf-8 -*-
"""
Söz üretici — felsefemiz.net
Tüm veriler DB'den gelir. DB yoksa minimal fallback.
"""
import os, re, random, logging, json, time
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ── Anthropic client ──────────────────────────────────────────
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    log.info("Anthropic client hazir.")
except Exception as _e:
    client = None
    log.warning("Anthropic client baslatılamadı: %s" % _e)

# ── DB ────────────────────────────────────────────────────────
try:
    from db import query as db_query, execute as db_execute
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    db_query   = lambda *a, **k: None
    db_execute = lambda *a, **k: None

# ── Minimal fallback listeler (DB yoksa) ──────────────────────
_AKIMLAR_FALLBACK = [
    "Stoacılık", "Varoluşçuluk", "Antik Yunan Felsefesi",
    "Budizm", "Rasyonalizm", "Empirizm", "Fenomenoloji",
    "Absürdizm", "Pragmatizm", "Nihilizm", "Taoizm",
]
_FILOZOFLAR_FALLBACK = [
    "Sokrates", "Platon", "Aristoteles", "Marcus Aurelius",
    "Epiktetos", "Friedrich Nietzsche", "Albert Camus",
    "Jean-Paul Sartre", "Immanuel Kant", "Arthur Schopenhauer",
    "Seneca", "Epikür", "Herakleitos", "Spinoza",
]
_KONULAR_FALLBACK = [
    "Hayatın anlamı ve özgürlük", "Ölüm ve varoluş",
    "Aşk ve insan doğası", "Bilgi ve hakikat",
    "Ahlak ve erdem", "Toplum ve birey",
]

# ─────────────────────────────────────────────────────────────
# DB yardımcıları
# ─────────────────────────────────────────────────────────────

def _get_akimlar():
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT ad FROM akimlar ORDER BY RAND()")
            if rows: return [r["ad"] for r in rows]
        except Exception as e:
            log.warning("DB akimlar: %s" % e)
    return _AKIMLAR_FALLBACK

def _get_random_filozof(akim=None, exclude=None):
    exclude = exclude or set()
    if DB_AVAILABLE:
        try:
            if akim:
                rows = db_query(
                    "SELECT ad FROM filozoflar WHERE akim=%s ORDER BY RAND() LIMIT 30", (akim,))
            else:
                rows = db_query("SELECT ad FROM filozoflar ORDER BY RAND() LIMIT 30")
            if rows:
                candidates = [r["ad"] for r in rows if r["ad"] not in exclude]
                if candidates: return random.choice(candidates)
        except Exception as e:
            log.warning("DB filozof: %s" % e)
    candidates = [f for f in _FILOZOFLAR_FALLBACK if f not in exclude]
    return random.choice(candidates) if candidates else "Sokrates"

def _get_random_konu():
    if DB_AVAILABLE:
        try:
            row = db_query("SELECT konu FROM konular ORDER BY RAND() LIMIT 1", fetchone=True)
            if row: return row["konu"]
        except Exception as e:
            log.warning("DB konu: %s" % e)
    return random.choice(_KONULAR_FALLBACK)

def _load_recent_authors(n=15):
    if DB_AVAILABLE:
        try:
            rows = db_query(
                "SELECT filozof_ad FROM yayinlar ORDER BY yayinlandi_at DESC LIMIT %s", (n,))
            if rows is not None:
                return set(r["filozof_ad"] for r in rows if r["filozof_ad"])
        except Exception as e:
            log.warning("DB recent_authors: %s" % e)
    try:
        pf = Path("posted.json")
        if pf.exists():
            posted = json.loads(pf.read_text(encoding="utf-8"))
            return set(p.get("author", "") for p in posted[-n:])
    except Exception: pass
    return set()

def _load_recent_quotes(n=30):
    if DB_AVAILABLE:
        try:
            rows = db_query(
                "SELECT soz_ozet FROM yayinlar ORDER BY yayinlandi_at DESC LIMIT %s", (n,))
            if rows is not None:
                return set(r["soz_ozet"] for r in rows if r["soz_ozet"])
        except Exception as e:
            log.warning("DB recent_quotes: %s" % e)
    try:
        pf = Path("posted.json")
        if pf.exists():
            posted = json.loads(pf.read_text(encoding="utf-8"))
            return set(p.get("quote", "")[:60] for p in posted[-n:])
    except Exception: pass
    return set()

def _db_get_unused_quote():
    """DB'deki hazır Türkçe söz — Atatürk hariç."""
    if not DB_AVAILABLE: return None
    try:
        recent_authors = _load_recent_authors(15)
        recent_quotes  = _load_recent_quotes(30)
        rows = db_query(
            """SELECT id, filozof_ad, soz, akim, hashtags, aciklama, kaynak
               FROM sozler
               WHERE dil='tr' AND dogrulanmis=1
                 AND filozof_ad != 'Mustafa Kemal Atatürk'
               ORDER BY RAND() LIMIT 30""")
        if not rows: return None
        for row in rows:
            if row["filozof_ad"] in recent_authors: continue
            if row["soz"][:60] in recent_quotes: continue
            log.info("DB'den soz: %s" % row["filozof_ad"])
            return _row_to_result(row)
        return _row_to_result(rows[0])
    except Exception as e:
        log.error("DB soz cekme: %s" % e)
        return None

def _row_to_result(row):
    return {
        "quote":    row["soz"],
        "author":   row["filozof_ad"],
        "akim":     row["akim"] or "Felsefe",
        "hashtags": row["hashtags"] or "#Felsefe #Bilgelik",
        "aciklama": row["aciklama"] or "",
        "kaynak":   row.get("kaynak") or "",
        "twitter":  row["soz"][:200] + " — " + row["filozof_ad"],
    }

def _db_save_quote(result):
    if not DB_AVAILABLE or not result: return
    try:
        db_execute(
            """INSERT IGNORE INTO sozler
               (filozof_ad, soz, akim, hashtags, aciklama, dil, dogrulanmis, kaynak_site)
               VALUES (%s,%s,%s,%s,%s,'tr',1,'wikiquote')""",
            (result.get("author",""), result.get("quote",""),
             result.get("akim",""), result.get("hashtags",""),
             result.get("aciklama",""))
        )
    except Exception as e:
        log.warning("DB soz kayit: %s" % e)

def _get_ataturk_quote():
    if DB_AVAILABLE:
        try:
            recent = _load_recent_quotes(30)
            rows = db_query(
                "SELECT soz, akim, kaynak, hashtags, aciklama FROM sozler "
                "WHERE filozof_ad=%s AND dil='tr' ORDER BY RAND() LIMIT 20",
                ("Mustafa Kemal Atatürk",))
            if rows:
                for row in rows:
                    if row["soz"][:60] not in recent:
                        return {
                            "quote": row["soz"], "author": "Mustafa Kemal Atatürk",
                            "akim": row["akim"] or "Türk Düşünce Tarihi",
                            "kaynak": row["kaynak"] or "",
                            "hashtags": row["hashtags"] or "#Ataturk #Felsefe #Bilgelik",
                            "aciklama": row["aciklama"] or "",
                            "twitter": row["soz"][:200] + " — Mustafa Kemal Atatürk",
                        }
                row = rows[0]
                return {"quote": row["soz"], "author": "Mustafa Kemal Atatürk",
                        "akim": row["akim"] or "Türk Düşünce Tarihi",
                        "kaynak": row["kaynak"] or "",
                        "hashtags": row["hashtags"] or "#Ataturk #Felsefe #Bilgelik",
                        "aciklama": row["aciklama"] or "",
                        "twitter": row["soz"][:200] + " — Mustafa Kemal Atatürk"}
        except Exception as e:
            log.error("DB Ataturk: %s" % e)
    log.error("Ataturk sozu bulunamadi!")
    return None

# ─────────────────────────────────────────────────────────────
# Söz kaynakları
# ─────────────────────────────────────────────────────────────

def _name_variants(name):
    parts = name.strip().split()
    v = [name]
    if len(parts) >= 2:
        v += [parts[-1], parts[0], "%s %s" % (parts[-1], parts[0])]
    seen, out = set(), []
    for x in v:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out

def _parse_wikitext(wikitext):
    quotes = []
    for line in wikitext.split("\n"):
        s = line.strip()
        if not s.startswith("*") or s.startswith("**"): continue
        clean = s.lstrip("* ").strip()
        clean = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", clean)
        clean = re.sub(r"\{\{[^}]*\}\}", "", clean)
        clean = re.sub(r"<[^>]+>", "", clean)
        clean = re.sub(r"('''|'')", "", clean).strip().strip('"\'').strip()
        if 25 < len(clean) < 400:
            quotes.append(clean)
    return quotes

def _fetch_wikiquote(philosopher):
    import requests
    for lang in ("tr", "en"):
        for name in _name_variants(philosopher):
            try:
                r = requests.get(
                    "https://%s.wikiquote.org/w/api.php" % lang,
                    params={"action":"parse","page":name,"prop":"wikitext","format":"json"},
                    timeout=12)
                if r.status_code != 200: continue
                data = r.json()
                if "error" in data: continue
                wt = data.get("parse",{}).get("wikitext",{}).get("*","")
                quotes = _parse_wikitext(wt)
                if quotes:
                    log.info("Wikiquote %s [%s]: %d soz" % (lang.upper(), name, len(quotes)))
                    return quotes[:25]
            except Exception as e:
                log.warning("Wikiquote %s/%s: %s" % (lang, name, e))
    return []

def _fetch_azquotes(philosopher):
    import requests
    try:
        slug = re.sub(r"[^a-z0-9]+", "-", philosopher.lower()).strip("-")
        r = requests.get(
            "https://www.azquotes.com/author/%s" % slug,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12)
        if r.status_code != 200: return []
        quotes = re.findall(r'<a[^>]+class="title"[^>]*>([^<]{20,350})</a>', r.text)
        import html
        return [html.unescape(q.strip()) for q in quotes if len(q.strip()) > 20][:20]
    except Exception as e:
        log.warning("AZQuotes %s: %s" % (philosopher, e))
    return []

def _fetch_goodreads(philosopher):
    import requests
    from urllib.parse import quote as uq
    try:
        r = requests.get(
            "https://www.goodreads.com/quotes/search?q=%s" % uq(philosopher),
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12)
        if r.status_code != 200: return []
        blocks = re.findall(r'<div\s+class="quoteText">(.*?)</div>', r.text, re.DOTALL)
        quotes = []
        import html
        for b in blocks:
            text = html.unescape(re.sub(r"<[^>]+>", "", b)).strip()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                qt = lines[0].strip('"""\u201c\u201d\u2018\u2019').strip()
                if 25 < len(qt) < 400: quotes.append(qt)
        return quotes[:20]
    except Exception as e:
        log.warning("Goodreads %s: %s" % (philosopher, e))
    return []

def fetch_quotes(philosopher):
    """Tüm kaynaklardan söz topla."""
    all_q, seen = [], set()
    for fn in [_fetch_wikiquote, _fetch_azquotes, _fetch_goodreads]:
        try:
            for q in fn(philosopher):
                k = q[:60].lower()
                if k not in seen:
                    seen.add(k); all_q.append(q)
        except Exception: pass
        time.sleep(0.3)
    log.info("Toplam [%s]: %d soz" % (philosopher, len(all_q)))
    return all_q

# ─────────────────────────────────────────────────────────────
# Dil tespiti
# ─────────────────────────────────────────────────────────────

def _is_turkish(text):
    if not text or len(text.strip()) < 5: return False
    words = set(text.lower().split())
    # Yabancı dil kelimeleri
    YABANCI = {
        # Almanca
        "der","die","das","und","oder","aber","nicht","ist","sind","hat","haben",
        "ich","du","er","sie","wir","von","zu","auf","für","mit","durch","über",
        "lässt","böses","seele","sprache","mensch","welt","tod","leben","liebe",
        # İngilizce
        "the","and","or","but","not","is","are","was","were","have","has","be",
        "in","on","at","to","of","for","with","by","from","that","this","it",
        "he","she","we","they","you","a","an","what","which","who","when","how",
        # Fransızca
        "le","la","les","un","une","des","du","et","ou","mais","est","sont",
        "que","qui","dans","sur","avec","pour","par","je","tu","il","nous","vous",
        # İspanyolca
        "el","los","las","un","una","de","y","o","pero","es","son","que","como",
        "en","con","por","para","yo","él","nosotros","ignoraba","arboles","poseian",
        # Sırpça/Hırvatça
        "znam","ne","da","nego","smijem","znati","moj","sam","je","su","biti",
        # Latince
        "est","sunt","non","sed","et","vel","aut","homo","deus","vita","amor",
        # İtalyanca
        "il","lo","gli","un","una","di","del","della","che","non","è","sono",
    }
    if len(words & YABANCI) >= 2:
        log.warning("Yabanci dil tespit edildi: %s" % text[:50])
        return False
    # Türkçe karakter
    if any(c in text for c in "çşğüöıÇŞĞÜÖİ"): return True
    # Türkçe kelimeler
    TR = {"ve","bir","bu","da","de","ile","için","ama","olan","değil","gibi",
          "kadar","daha","çok","her","biz","ben","sen","var","yok","ne",
          "hayat","insan","dünya","zaman","gerçek","akıl","bilgi","ölüm",
          "sevgi","aşk","vicdan","adalet","erdem","bilgelik","özgürlük"}
    return len(words & TR) >= 2

# ─────────────────────────────────────────────────────────────
# Claude ile söz seçimi
# ─────────────────────────────────────────────────────────────

def _select_with_claude(philosopher, akim, konu, quotes_list):
    if not client or not quotes_list: return ""
    quotes_text = "\n".join(["  %d. %s" % (i+1, q) for i, q in enumerate(quotes_list)])
    system = """Sen bir felsefe editörüsün.
KESİN KURALLAR:
1. Listede OLMAYAN söz yazma. Sadece verilen listeden seç.
2. Söz her dilde olsa MUTLAKA akıcı Türkçeye çevir.
3. SOZ alanında başka dil YASAK. Tırnak işareti KULLANMA.
4. Hashtaglerde Türkçe karakter KULLANMA (ogu,s,c,i şeklinde yaz).

Format (tam bu şekilde):
SOZ:
[Türkçe söz, tırnak yok, max 250 karakter]
---
YAZAR:
[Filozofun adı]
---
AKIM:
[Felsefi akım]
---
HASHTAG:
[5 hashtag — #Felsefe #Bilgelik zorunlu]
---
ACIKLAMA:
[2-3 cümle Türkçe felsefi yorum]
---
TWITTER:
[Türkçe söz — Yazar Adı]"""
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=700,
                system=system,
                messages=[{"role":"user","content":
                    "Düşünür: %s\nAkım: %s\nKonu: %s\n\nSözler:\n%s" % (
                    philosopher, akim, konu, quotes_text)}])
            result = msg.content[0].text.strip()
            if result: return result
        except Exception as e:
            log.warning("Claude (deneme %d): %s" % (attempt+1, e))
            if attempt < 2: time.sleep(10)
    return ""

def _fallback_format(philosopher, akim, quotes_list):
    """Claude yoksa Türkçe söz seç ve formatla."""
    turkce = [q for q in quotes_list if _is_turkish(q)]
    if not turkce:
        log.warning("Fallback: Turkce soz yok: %s" % philosopher)
        return ""
    turkce.sort(key=len)
    secim = re.sub(r'["""\u201c\u201d\u2018\u2019«»\']', "", turkce[0]).strip()[:250]
    if len(secim) < 15: return ""
    tag = re.sub(r"[^a-zA-Z0-9]", "", akim.split("/")[0].strip())
    yt  = re.sub(r"[^a-zA-Z0-9]", "", philosopher.split()[-1] if philosopher else "Felsefe")
    return "SOZ:\n%s\n---\nYAZAR:\n%s\n---\nAKIM:\n%s\n---\nHASHTAG:\n#Felsefe #Bilgelik #%s #%s #DusunenInsan\n---\nACIKLAMA:\n%s felsefi düşüncesinden önemli bir gözlem.\n---\nTWITTER:\n%s — %s" % (
        secim, philosopher, akim, tag, yt, philosopher, secim, philosopher)

def _clean(text):
    text = text.strip()
    for q in ['\u201c','\u201d','\u2018','\u2019','"',"'"]:
        text = text.strip(q)
    return text.strip()

def _parse(text, default_author, default_akim):
    def get(key):
        m = re.search(r"%s:\n(.*?)(?:\n---|$)" % key, text, re.DOTALL)
        return m.group(1).strip() if m else ""
    quote = _clean(get("SOZ"))
    if not quote or len(quote) < 10:
        log.warning("Parse: bos soz")
        return None
    if not _is_turkish(quote):
        log.warning("Parse: yabanci dil: %s" % quote[:50])
        return None
    author = get("YAZAR") or default_author
    return {
        "quote":    quote,
        "author":   author,
        "akim":     get("AKIM") or default_akim,
        "hashtags": get("HASHTAG") or "#Felsefe #Bilgelik",
        "aciklama": get("ACIKLAMA") or "",
        "twitter":  get("TWITTER") or "%s — %s" % (quote, author),
    }

# ─────────────────────────────────────────────────────────────
# Ana fonksiyon
# ─────────────────────────────────────────────────────────────

def generate_quote():
    bugun = datetime.now()
    ay, gun = bugun.month, bugun.day

    # Özel günler → Atatürk
    if (ay==11 and gun==10) or (ay==10 and gun==29) or \
       (ay==8 and gun==30) or (ay==5 and gun==19) or (ay==4 and gun==23):
        return _get_ataturk_quote()

    # %20 → Atatürk
    if random.random() < 0.20:
        return _get_ataturk_quote()

    # 1. DB'de hazır söz var mı?
    db_result = _db_get_unused_quote()
    if db_result:
        log.info("DB'den soz kullanildi: %s" % db_result["author"])
        return db_result

    # 2. Yok → kaynaktan çek
    log.info("DB'de soz yok, kaynaktan cekilecek...")
    recent_authors = _load_recent_authors(15)
    recent_quotes  = _load_recent_quotes(30)
    akimlar = _get_akimlar()

    for _ in range(20):
        akim    = random.choice(akimlar)
        filozof = _get_random_filozof(akim, exclude=recent_authors)
        if filozof not in recent_authors: break
    konu = _get_random_konu()

    for deneme in range(8):
        log.info("Deneme %d: %s" % (deneme+1, filozof))
        real_quotes = fetch_quotes(filozof)

        if real_quotes:
            filtered = [q for q in real_quotes if q[:60] not in recent_quotes] or real_quotes
            raw = _select_with_claude(filozof, akim, konu, filtered)
            if not raw:
                raw = _fallback_format(filozof, akim, filtered)
            result = _parse(raw, filozof, akim)
            if result and result.get("quote") and result["quote"][:60] not in recent_quotes:
                _db_save_quote(result)
                return result

        log.warning("Soz bulunamadi: %s (%d/8)" % (filozof, deneme+1))
        for _ in range(10):
            akim    = random.choice(akimlar)
            filozof = _get_random_filozof(akim, exclude=recent_authors)
            if filozof not in recent_authors: break
        konu = _get_random_konu()

    log.error("8 denemede soz bulunamadi.")
    return None
