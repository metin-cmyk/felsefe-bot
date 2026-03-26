import os, re, random, anthropic, logging, json
from datetime import datetime
from pathlib import Path

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

# Anthropic client — hata olursa None, fallback devreye girer
try:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
except Exception as _e:
    client = None
    log.warning("Anthropic client baslatılamadı: %s" % _e)

# ---------------------------------------------------------------------------
# Atatürk — Sadece doğrulanmış, kaynaklarda belgelenmiş sözler
# Kaynak: Nutuk, TBMM tutanakları, Atatürk'ün Söylev ve Demeçleri
# ---------------------------------------------------------------------------


def _get_ataturk_quote():
    """
    Atatürk sözlerini DB'den çeker.
    Fallback: boş döner (liste kaldırıldı, DB zorunlu).
    """
    if DB_AVAILABLE:
        try:
            # Son 30 yayında olmayan Atatürk sözü seç
            recent = _load_recent_quotes(30)
            rows = db_query(
                "SELECT soz, akim, kaynak, hashtags, aciklama FROM sozler "
                "WHERE filozof_ad = %s AND dil = 'tr' ORDER BY RAND() LIMIT 20",
                ("Mustafa Kemal Atatürk",)
            )
            if rows:
                # Daha önce paylaşılmamış sözü tercih et
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
                # Hepsi paylaşılmışsa ilkini al
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
    log.error("DB mevcut degil veya Ataturk sozu bulunamadi!")
    return None

def _load_recent_authors(n=15):
    """Son n paylaşımdan yazar setini döndür. DB varsa oradan, yoksa posted.json'dan."""
    if DB_AVAILABLE:
        try:
            rows = db_query(
                "SELECT filozof_ad FROM yayinlar ORDER BY yayinlandi_at DESC LIMIT %s", (n,)
            )
            if rows is not None:
                return set(r["filozof_ad"] for r in rows if r["filozof_ad"])
        except Exception as e:
            log.warning("DB recent_authors hatası: %s" % e)
    # Fallback: posted.json
    try:
        pf = Path("posted.json")
        if not pf.exists():
            return set()
        posted = json.loads(pf.read_text(encoding="utf-8"))
        return set(p.get("author", "") for p in posted[-n:])
    except Exception:
        return set()

def _load_recent_quotes(n=30):
    """Son n paylaşımdan söz setini döndür. DB varsa oradan, yoksa posted.json'dan."""
    if DB_AVAILABLE:
        try:
            rows = db_query(
                "SELECT soz_ozet FROM yayinlar ORDER BY yayinlandi_at DESC LIMIT %s", (n,)
            )
            if rows is not None:
                return set(r["soz_ozet"] for r in rows if r["soz_ozet"])
        except Exception as e:
            log.warning("DB recent_quotes hatası: %s" % e)
    # Fallback: posted.json
    try:
        pf = Path("posted.json")
        if not pf.exists():
            return set()
        posted = json.loads(pf.read_text(encoding="utf-8"))
        return set(p.get("quote", "")[:60] for p in posted[-n:])
    except Exception:
        return set()

def _get_akimlar():
    """AKIMLAR listesini DB'den veya Python listesinden al."""
    if DB_AVAILABLE:
        try:
            rows = db_query("SELECT ad FROM akimlar ORDER BY RAND()")
            if rows:
                return [r["ad"] for r in rows]
        except Exception as e:
            log.warning("DB akimlar hatası: %s" % e)
    return AKIMLAR

def _get_random_filozof(akim, exclude=None):
    """Akıma göre rastgele filozof seç. DB varsa oradan al."""
    exclude = exclude or set()
    if DB_AVAILABLE:
        try:
            rows = db_query(
                "SELECT ad FROM filozoflar WHERE akim = %s ORDER BY RAND() LIMIT 20", (akim,)
            )
            if rows:
                candidates = [r["ad"] for r in rows if r["ad"] not in exclude]
                if candidates:
                    return random.choice(candidates)
        except Exception as e:
            log.warning("DB filozof hatası: %s" % e)
    # Fallback: Python listesi
    candidates = [f for f in FILOZOFLAR.get(akim, []) if f not in exclude]
    if candidates:
        return random.choice(candidates)
    return random.choice(FILOZOFLAR.get("Antik Yunan ve Ön-Sokratikler", ["Sokrates"]))

def _get_random_konu():
    """Rastgele konu seç. DB varsa oradan al."""
    if DB_AVAILABLE:
        try:
            row = db_query("SELECT konu FROM konular ORDER BY RAND() LIMIT 1", fetchone=True)
            if row:
                return row["konu"]
        except Exception as e:
            log.warning("DB konu hatası: %s" % e)
    return random.choice(KONULAR)

def _db_get_unused_quote():
    """
    DB'deki sozler tablosundan daha önce yayınlanmamış Türkçe söz çeker.
    Atatürk hariç filozoflardan rastgele seçer.
    """
    if not DB_AVAILABLE:
        return None
    try:
        recent_authors = _load_recent_authors(15)
        recent_quotes  = _load_recent_quotes(30)

        # Son 15 yazardan farklı, son 30 sözden farklı, Türkçe, onaylı
        rows = db_query(
            """SELECT s.id, s.filozof_ad, s.soz, s.akim, s.hashtags, s.aciklama, s.kaynak
               FROM sozler s
               WHERE s.dil = 'tr'
                 AND s.dogrulanmis = 1
                 AND s.filozof_ad != 'Mustafa Kemal Atatürk'
                 AND s.soz_ozet NOT IN (
                     SELECT COALESCE(soz_ozet,'') FROM yayinlar 
                     ORDER BY yayinlandi_at DESC LIMIT 30
                 )
               ORDER BY RAND()
               LIMIT 20""",
        )
        if not rows:
            # Kısıtlamayı gevşet — sadece son 10 yayını hariç tut
            rows = db_query(
                """SELECT s.id, s.filozof_ad, s.soz, s.akim, s.hashtags, s.aciklama, s.kaynak
                   FROM sozler s
                   WHERE s.dil = 'tr'
                     AND s.dogrulanmis = 1
                     AND s.filozof_ad != 'Mustafa Kemal Atatürk'
                   ORDER BY RAND() LIMIT 10"""
            )
        if not rows:
            return None

        for row in rows:
            if row["filozof_ad"] in recent_authors:
                continue
            if row["soz"][:60] in recent_quotes:
                continue
            log.info("DB'den soz alindi: %s" % row["filozof_ad"])
            return {
                "quote":    row["soz"],
                "author":   row["filozof_ad"],
                "akim":     row["akim"] or "Felsefe",
                "hashtags": row["hashtags"] or "#Felsefe #Bilgelik",
                "aciklama": row["aciklama"] or "",
                "kaynak":   row["kaynak"] or "",
                "twitter":  row["soz"][:200] + " — " + row["filozof_ad"],
            }
        # Tüm filtreler başarısız — ilkini al
        row = rows[0]
        return {
            "quote":    row["soz"],
            "author":   row["filozof_ad"],
            "akim":     row["akim"] or "Felsefe",
            "hashtags": row["hashtags"] or "#Felsefe #Bilgelik",
            "aciklama": row["aciklama"] or "",
            "kaynak":   row["kaynak"] or "",
            "twitter":  row["soz"][:200] + " — " + row["filozof_ad"],
        }
    except Exception as e:
        log.error("DB soz cekme hatasi: %s" % e)
        return None


def _db_save_quote(result):
    """Üretilen sözü DB'ye kaydet (sozler tablosu)."""
    if not DB_AVAILABLE or not result:
        return
    try:
        db_execute(
            """INSERT IGNORE INTO sozler 
               (filozof_ad, soz, akim, hashtags, aciklama, dil, dogrulanmis, kaynak_site)
               VALUES (%s, %s, %s, %s, %s, 'tr', 1, 'wikiquote')""",
            (
                result.get("author", ""),
                result.get("quote", ""),
                result.get("akim", ""),
                result.get("hashtags", ""),
                result.get("aciklama", ""),
            )
        )
        log.info("Yeni soz DB'ye kaydedildi: %s" % result.get("author", ""))
    except Exception as e:
        log.warning("DB soz kayit hatasi: %s" % e)


def generate_quote():
    bugun = datetime.now()
    ay = bugun.month
    gun = bugun.day

    # Özel günler — Atatürk
    if (ay == 11 and gun == 10) or (ay == 10 and gun == 29) or        (ay == 8 and gun == 30) or (ay == 5 and gun == 19) or (ay == 4 and gun == 23):
        return _get_ataturk_quote()

    # %20 ihtimalle Atatürk
    if random.random() < 0.20:
        return _get_ataturk_quote()

    # ── ADIM 1: DB'de hazır söz var mı? ──────────────────────
    db_result = _db_get_unused_quote()
    if db_result:
        log.info("DB'den doğrudan söz kullanılıyor: %s" % db_result["author"])
        return db_result

    # ── ADIM 2: DB'de söz yok — Wikiquote'tan çek, DB'ye kaydet ─
    log.info("DB'de uygun soz yok, Wikiquote'tan cekilecek...")
    recent_authors = _load_recent_authors(15)
    recent_quotes  = _load_recent_quotes(30)

    akimlar_list = _get_akimlar()
    for _ in range(20):
        akim    = random.choice(akimlar_list)
        filozof = _get_random_filozof(akim, exclude=recent_authors)
        if filozof not in recent_authors:
            break
    konu = _get_random_konu()
    log.info("Wikiquote'tan cekilecek: %s" % filozof)

    MAX_DENEME = 8
    for deneme in range(MAX_DENEME):
        # Çok kaynaklı söz toplama
        if MULTI_SOURCE:
            real_quotes = fetch_all_quotes(filozof)
            lang = "multi"
        else:
            real_quotes, lang = _fetch_real_quotes_from_wikipedia(filozof)

        if real_quotes:
            filtered = [q for q in real_quotes if q[:60] not in recent_quotes]
            if not filtered:
                filtered = real_quotes

            raw    = _select_best_quote(filozof, akim, konu, filtered)
            result = _parse(raw, filozof, akim)
            if result and result.get("quote"):
                if result["quote"][:60] in recent_quotes:
                    log.warning("Bu soz zaten paylasılmis, atlaniyor.")
                else:
                    # DB'ye kaydet — bir sonraki seferinde hazır olsun
                    _db_save_quote(result)
                    return result
            log.warning("Parse bos/tekrar, baska filozof deneniyor.")

        log.warning("Soz bulunamadi: %s (%d/%d)" % (filozof, deneme+1, MAX_DENEME))
        for _ in range(10):
            akim    = random.choice(akimlar_list)
            filozof = _get_random_filozof(akim, exclude=recent_authors)
            if filozof not in recent_authors:
                break
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

    # Boş söz — parse başarısız, None dön
    if not quote or len(quote.strip()) < 10:
        log.warning("Parse sonucu bos soz geldi, atlaniyor.")
        return None

    # Yabancı dil kontrolü — Türkçe değilse None dön
    if not _is_turkish(quote):
        log.warning("Parse sonucu yabanci dil sozü geldi, atlaniyor: %s" % quote[:50])
        return None

    author = get("YAZAR")
    if not author or "az bilinen" in author.lower():
        author = default_autor if "az bilinen" not in default_autor.lower() else "Anonim Bilge"

    hashtags = get("HASHTAG") or "#Felsefe #Bilgelik"
    twitter = get("TWITTER") or f"{quote}\n\n— {author}"

    return {
        "quote": quote,
        "author": author,
        "akim": get("AKIM") or default_akim,
        "hashtags": hashtags,
        "aciklama": get("ACIKLAMA"),
        "twitter": twitter
    }

# ---------------------------------------------------------------------------
# Wikiquote wikitext API — gercek sozler (dosyanin sonuna eklendi)
# ---------------------------------------------------------------------------

import re as _re
import logging as _logging
_wq_log = _logging.getLogger(__name__)



def _name_variants(name):
    """Filozof adinin farkli Wikiquote varyantlarini uretir."""
    variants = [name]
    parts = name.strip().split()
    if len(parts) >= 2:
        variants.append(parts[-1])
        variants.append(parts[0])
        variants.append("%s %s" % (parts[-1], parts[0]))
    import re as _re2
    m = _re2.search(r"\(([^)]+)\)", name)
    if m:
        variants.append(name[:name.index("(")].strip())
        variants.append(m.group(1).strip())
    seen = set()
    result = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _fetch_wikiquote(philosopher):
    """Wikiquote TR ve EN wikitext API — en güvenilir kaynak."""
    import requests as _req

    def _parse_wikitext(wikitext):
        quotes = []
        for line in wikitext.split("\n"):
            s = line.strip()
            if not s.startswith("*") or s.startswith("**"):
                continue
            clean = s.lstrip("* ").strip()
            clean = _re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", clean)
            clean = _re.sub(r"\{\{[^}]*\}\}", "", clean)
            clean = _re.sub(r"<ref[^>]*>.*?</ref>", "", clean, flags=_re.DOTALL)
            clean = _re.sub(r"<br\s*/?>", " ", clean)
            clean = _re.sub(r"<[^>]+>", "", clean)
            clean = _re.sub(r"('''|'')", "", clean)
            clean = clean.strip().strip('"').strip("\'").strip()
            if 25 < len(clean) < 400:
                quotes.append(clean)
        return quotes

    name_variants = _name_variants(philosopher)
    for lang in ("tr", "en"):
        for name in name_variants:
            try:
                r = _req.get(
                    "https://%s.wikiquote.org/w/api.php" % lang,
                    params={"action": "parse", "page": name, "prop": "wikitext", "format": "json"},
                    timeout=12,
                )
                if r.status_code != 200:
                    continue
                data = r.json()
                if "error" in data:
                    continue
                wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
                if not wikitext:
                    continue
                quotes = _parse_wikitext(wikitext)
                if quotes:
                    log.info("Wikiquote %s [%s]: %d soz" % (lang.upper(), name, len(quotes)))
                    return quotes[:25]
            except Exception as e:
                log.warning("Wikiquote %s [%s] hatasi: %s" % (lang, name, e))
    return []


def _fetch_azquotes(philosopher):
    """AZQuotes.com — HTML parse, genis koleksiyon."""
    import requests as _req
    from urllib.parse import quote as _uq
    try:
        # AZQuotes URL formatı: /author/first-last
        slug = philosopher.lower()
        slug = _re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        url = "https://www.azquotes.com/author/%s" % slug
        headers = {"User-Agent": "Mozilla/5.0 (compatible; felsefemiz-bot/1.0)"}
        r = _req.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return []
        # <a class="title" ...> taglerini çıkar
        quotes = _re.findall(r'<a[^>]+class="title"[^>]*>([^<]{20,350})</a>', r.text)
        # HTML entity decode
        import html as _html
        quotes = [_html.unescape(q.strip()) for q in quotes if len(q.strip()) > 20]
        if quotes:
            log.info("AZQuotes [%s]: %d soz" % (philosopher, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("AZQuotes hatasi [%s]: %s" % (philosopher, e))
    return []


def _fetch_goodreads(philosopher):
    """Goodreads quotes search — HTML parse."""
    import requests as _req
    from urllib.parse import quote as _uq
    try:
        url = "https://www.goodreads.com/quotes/search?q=%s" % _uq(philosopher)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; felsefemiz-bot/1.0)"}
        r = _req.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return []
        # <div class="quoteText"> içindeki metni çıkar
        raw_blocks = _re.findall(r'<div\s+class="quoteText">(.*?)</div>', r.text, _re.DOTALL)
        quotes = []
        for block in raw_blocks:
            # HTML temizle
            text = _re.sub(r"<[^>]+>", "", block)
            import html as _html
            text = _html.unescape(text).strip()
            # Sadece tırnak içindeki kısmı al (― ile bitmeden önce)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                quote_text = lines[0].strip('""\u201c\u201d\u2018\u2019').strip()
                if 25 < len(quote_text) < 400:
                    quotes.append(quote_text)
        if quotes:
            log.info("Goodreads [%s]: %d soz" % (philosopher, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("Goodreads hatasi [%s]: %s" % (philosopher, e))
    return []


def _fetch_felsefe_gen_tr(philosopher):
    """felsefe.gen.tr — Türkçe felsefe sitesi."""
    import requests as _req
    from urllib.parse import quote as _uq
    try:
        url = "https://felsefe.gen.tr/?s=%s" % _uq(philosopher)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; felsefemiz-bot/1.0)"}
        r = _req.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        # <blockquote> veya <p> içindeki felsefi sözleri çek
        quotes = _re.findall(r'<blockquote[^>]*>(.*?)</blockquote>', r.text, _re.DOTALL)
        result = []
        import html as _html
        for q in quotes:
            text = _re.sub(r"<[^>]+>", "", q)
            text = _html.unescape(text).strip()
            if 25 < len(text) < 400:
                result.append(text)
        if result:
            log.info("felsefe.gen.tr [%s]: %d soz" % (philosopher, len(result)))
        return result[:15]
    except Exception as e:
        log.warning("felsefe.gen.tr hatasi [%s]: %s" % (philosopher, e))
    return []


def _fetch_real_quotes_from_wikipedia(philosopher):
    """
    Çok kaynaklı söz toplama sistemi.
    Sıra: Wikiquote TR/EN → AZQuotes → Goodreads → felsefe.gen.tr
    İlk sonuç veren kaynaktan döner.
    """
    # 1. Wikiquote (en güvenilir)
    quotes = _fetch_wikiquote(philosopher)
    if quotes:
        return quotes, "wikiquote"

    # 2. AZQuotes
    quotes = _fetch_azquotes(philosopher)
    if quotes:
        return quotes, "azquotes"

    # 3. Goodreads
    quotes = _fetch_goodreads(philosopher)
    if quotes:
        return quotes, "goodreads"

    # 4. felsefe.gen.tr
    quotes = _fetch_felsefe_gen_tr(philosopher)
    if quotes:
        return quotes, "felsefe.gen.tr"

    log.warning("Hicbir kaynakta soz bulunamadi: %s" % philosopher)
    return [], "none"

def _select_best_quote(philosopher, akim, konu, quotes_list):
    """
    Cok kaynaktan gelen GERCEK sozler arasinda Claude en uygununu SECER.
    Ingilizce ise Turkce'ye cevirir, anlamini degistirmez.
    """
    quotes_text = "\n".join(["  %d. %s" % (i+1, q) for i, q in enumerate(quotes_list)])

    system = """Sen bir felsefe editörüsün. Sana filozofun GERÇEK, doğrulanmış sözleri verilecek.
Görev: Bu listeden konuya EN UYGUN ve EN GÜÇLÜ sözü seç, MUTLAKA Türkçeye çevir, formatla.

KESİN KURALLAR:
1. Listede OLMAYAN hiçbir söz yazma veya uydurma. Sadece verilen listeden seç.
2. Söz hangi dilde olursa olsun (Almanca, İngilizce, Fransızca, Latince vb.) MUTLAKA akıcı Türkçeye çevir.
3. Anlamı DEĞİŞTİRME, sadece çevir.
4. Çeviride Türkçe karakterleri MUTLAKA kullan: ç, ş, ğ, ü, ö, ı, İ, Ğ, Ş, Ç, Ü, Ö
5. SOZ alanında tırnak işareti (", ', «, ») KULLANMA.
6. SOZ alanında Almanca, İngilizce veya başka yabancı dil KULLANMA. Türkçe olmalı.
7. Hashtagleri # ile başlat, Türkçe karakter KULLANMA (o,u,s,c,i,g şeklinde yaz).
8. TWITTER alanında sadece Türkçe söz ve yazar adı olsun, hashtag YAZMA.

Yanıtını TAM OLARAK bu formatta ver:

SOZ:
[Seçilen sözün TÜRKÇE hali — başka dil YASAK, tırnak YOK, max 250 karakter]
---
YAZAR:
[Filozofun adı]
---
AKIM:
[Felsefi akım]
---
HASHTAG:
[5 hashtag — #Felsefe ve #Bilgelik zorunlu, 3 tane daha konuya uygun]
---
ACIKLAMA:
[Sözün 2-3 cümlelik Türkçe açıklaması — felsefi bağlamını anlat]
---
TWITTER:
[Türkçe söz tırnaksız — Yazar Adı]"""

    import time
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=700,
                system=system,
                messages=[{"role": "user", "content": "Dusunur: %s\nAkim: %s\nKonu: %s\n\nGERCEK sozler listesi (bu listeden sec):\n%s" % (philosopher, akim, konu, quotes_text)}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            log.warning("Claude API hatasi (deneme %d/3): %s" % (attempt+1, e))
            if attempt < 2:
                time.sleep(10)

    # Claude basarisiz — fallback ile dogrudan listeden sec (sadece Turkce)
    log.warning("Claude API basarisiz, fallback deneniyor: %s" % philosopher)
    result = _fallback_format(philosopher, akim, quotes_list)
    if result:
        return result
    # Turkce soz bulunamadi — bos don, generate_quote baska filozof dener
    return ""


def _is_turkish(text):
    """
    Metnin Türkçe olup olmadığını kontrol eder.
    Almanca, İngilizce, Fransızca, İspanyolca, Sırpça/Hırvatça, Latince vb. reddeder.
    """
    if not text or len(text.strip()) < 5:
        return False

    words = set(text.lower().split())

    # ── Yabancı dil kelimeleri — ÖNCE kontrol et ──────────────────────
    almanca = {
        "der","die","das","des","dem","den","ein","eine","einer","eines",
        "und","oder","aber","nicht","ist","sind","hat","haben","war","waren",
        "wird","werden","kann","muss","ich","du","er","sie","wir","ihr","sie",
        "von","zu","in","an","auf","für","mit","durch","über","nach","bei",
        "lässt","lasst","böses","seele","geist","mensch","leben","liebe",
        "wahrheit","welt","tod","weg","sprache","missbrauch","wenn","dann",
        "also","wie","was","wer","wo","doch","noch","schon","nur","auch",
        "diesem","dieser","diesem","welche","welcher","welches"
    }
    ingilizce = {
        "the","a","an","is","are","was","were","be","been","being",
        "have","has","had","do","does","did","will","would","shall",
        "can","could","should","may","might","must","ought",
        "and","or","but","not","nor","so","yet","for","nor",
        "in","on","at","to","for","of","with","by","from","into",
        "that","this","these","those","it","he","she","we","they",
        "you","i","my","your","his","her","our","their","its",
        "what","which","who","whom","whose","when","where","why","how",
        "all","any","both","each","every","few","more","most","other",
        "some","such","than","then","there","though","through","too",
        "very","just","about","above","after","before","between"
    }
    fransizca = {
        "le","la","les","un","une","des","du","de","et","ou","mais","donc",
        "est","sont","être","avoir","faire","dire","aller","voir","vouloir",
        "que","qui","quoi","dont","où","quand","comment","pourquoi","car",
        "dans","sur","avec","pour","par","sans","sous","entre","vers",
        "je","tu","il","elle","nous","vous","ils","elles","on","ce","se",
        "pas","plus","très","aussi","même","tout","tous","toutes","bien",
        "mon","ma","mes","ton","ta","tes","son","sa","ses","notre","votre"
    }
    ispanyolca = {
        "el","la","los","las","un","una","unos","unas","de","del","al",
        "y","o","pero","sino","que","porque","como","cuando","donde",
        "es","son","está","están","ser","estar","tener","hacer","ir",
        "yo","tú","él","ella","nosotros","vosotros","ellos","ellas",
        "mi","tu","su","nuestro","vuestro","me","te","se","nos","os",
        "en","con","por","para","sin","sobre","entre","bajo","desde",
        "si","no","sí","muy","más","menos","también","ya","así","todo",
        "toda","todos","todas","este","esta","estos","estas","ese","esa",
        "ignoraba","arboles","sentimientos","humanos","cantores","poseian",
        "inteligencia","podrian","corazon","manera","menos","tocaba"
    }
    sirpca_hırvatca = {
        "znam","ne","da","nego","smijem","znati","moj","sam","je","su",
        "se","na","za","od","do","po","pri","kao","što","koji","koja",
        "koje","ovaj","ova","ovo","taj","ta","to","jedan","jedna","jedno",
        "biti","imati","moći","znati","htjeti","reći","vidjeti","ići",
        "ali","ili","i","pa","te","ni","niti","već","ipak","samo","još",
        "sve","svi","svaki","svaka","svako","koji","čovjek","život","ljubav",
        "zivot","ljubav","mudrost","istina","sloboda","duša","dusa"
    }
    rusca_slavca = {
        "не","да","но","и","или","что","как","это","так","уже",
        "все","быть","иметь","мочь","знать","хотеть","сказать",
        "человек","жизнь","любовь","мудрость","истина","свобода"
    }
    latince = {
        "est","sunt","non","sed","et","vel","aut","ut","in","ad",
        "de","per","pro","sub","super","ante","post","inter","cum",
        "hoc","haec","hic","ille","illa","illud","qui","quae","quod",
        "omnis","omne","magnus","parva","vita","amor","veritas","mens",
        "homo","deus","natura","ratio","anima","corpus","tempus","lux"
    }
    italyanca = {
        "il","la","lo","i","gli","le","un","una","di","del","della",
        "dei","degli","delle","e","ma","o","che","non","è","sono",
        "essere","avere","fare","dire","andare","vedere","volere",
        "io","tu","lui","lei","noi","voi","loro","si","mi","ti",
        "per","con","su","in","da","tra","fra","questo","quello"
    }

    # Yabancı dil tespiti — 2+ kelime eşleşmesi yeterli
    foreign_checks = [
        (almanca,        2, "Almanca"),
        (ingilizce,      3, "Ingilizce"),
        (fransizca,      2, "Fransizca"),
        (ispanyolca,     2, "Ispanyolca"),
        (sirpca_hırvatca,2, "Sirpca/Hırvatca"),
        (rusca_slavca,   2, "Rusca/Slavca"),
        (latince,        3, "Latince"),
        (italyanca,      2, "Italyanca"),
    ]

    for word_set, threshold, lang_name in foreign_checks:
        matches = len(words & word_set)
        if matches >= threshold:
            log.warning("Yabanci dil tespit edildi (%s, %d eslesme): %s" % (lang_name, matches, text[:50]))
            return False

    # ── Türkçe karakter ve kelimeler ─────────────────────────────────
    turkce_chars = set("çşğüöıÇŞĞÜÖİ")
    if any(c in text for c in turkce_chars):
        return True

    turkce_words = {
        "ve","bir","bu","da","de","ile","için","ama","çünkü","eğer","zira",
        "olan","değil","gibi","kadar","daha","çok","her","biz","ben","sen",
        "var","yok","ne","nasıl","neden","niçin","kim","hangi","şu",
        "hayat","insan","dünya","zaman","gerçek","akıl","bilgi","ölüm",
        "güzel","iyi","kötü","büyük","küçük","yalnız","mutlu","özgür",
        "sevgi","aşk","dostluk","vicdan","adalet","erdem","bilgelik",
        "ruh","zihin","beden","kalp","can","tanrı","evren","doğa",
        "toplum","devlet","özgürlük","barış","savaş","güç","iktidar"
    }
    if len(words & turkce_words) >= 2:
        return True

    # Hiçbiri eşleşmediyse — güvenli taraf: reddet
    return False


def _fallback_format(philosopher, akim, quotes_list):
    """
    Claude API basarisiz olduğunda listeden Türkçe söz secer ve formatlar.
    İngilizce söz varsa ASLA paylaşmaz — boş döner, başka filozof denenir.
    """
    if not quotes_list:
        return ""

    # Sadece Türkçe sözleri al
    turkce_sozler = [q for q in quotes_list if _is_turkish(q)]

    if not turkce_sozler:
        # Türkçe söz yok — bu filozofu atla, boş dön
        log.warning("Fallback: Turkce soz bulunamadi (%s), atlanıyor." % philosopher)
        return ""

    # En kısa ve temiz Türkçe sözü seç (uzun sözler görsele sığmayabilir)
    turkce_sozler.sort(key=len)
    secim = turkce_sozler[0]
    secim = re.sub(r'[""\u201c\u201d\u2018\u2019«»\']', "", secim).strip()[:250]

    if len(secim) < 15:
        return ""

    akim_tag = re.sub(r"[^a-zA-Z0-9]", "", akim.split("/")[0].strip())
    yt_tag   = re.sub(r"[^a-zA-Z0-9]", "", (philosopher.split()[-1] if philosopher else "Felsefe"))
    hashtags = "#Felsefe #Bilgelik #%s #%s #DusunenInsan" % (akim_tag, yt_tag)

    return """SOZ:\n%s\n---\nYAZAR:\n%s\n---\nAKIM:\n%s\n---\nHASHTAG:\n%s\n---\nACIKLAMA:\n%s'nin felsefi düşüncesinden önemli bir gözlem.\n---\nTWITTER:\n%s — %s""" % (
        secim, philosopher, akim, hashtags, philosopher, secim, philosopher
    )
