import os, logging, requests, re, time
from pathlib import Path
from urllib.parse import quote as urlquote
from image_generator import create_square_cover

log = logging.getLogger(__name__)

WP_URL      = os.environ.get("WP_URL",      "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER",     "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

# ---------------------------------------------------------------------------
# Yardımcı: WordPress görsel yükleme — meta taglarıyla birlikte
# ---------------------------------------------------------------------------

def _upload_image(image_path, alt_text="", title="", caption="", description=""):
    """
    Görseli WordPress media kütüphanesine yükler.
    Meta alanları (alt, title, caption, description) tek seferde doldurulur.
    Döner: media_id (int) veya None
    """
    if not image_path or not Path(image_path).exists():
        log.error("Gorsel dosyasi bulunamadi: %s" % image_path)
        return None
    try:
        with open(image_path, "rb") as f:
            img_data = f.read()
        filename = Path(image_path).name
        # 1. Yükle
        r = requests.post(
            "%s/wp-json/wp/v2/media" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            headers={
                "Content-Disposition": "attachment; filename=%s" % filename,
                "Content-Type":        "image/jpeg",
            },
            data=img_data,
            timeout=90,
        )
        log.info("WP media upload HTTP %d" % r.status_code)
        if r.status_code not in (200, 201):
            log.error("Gorsel yuklenemedi: HTTP %d — %s" % (r.status_code, r.text[:200]))
            return None
        media_id = r.json()["id"]

        # 2. Meta alanlarını güncelle
        meta = {}
        if alt_text:    meta["alt_text"]    = alt_text
        if title:       meta["title"]        = title
        if caption:     meta["caption"]      = caption
        if description: meta["description"]  = description
        if meta:
            r2 = requests.post(
                "%s/wp-json/wp/v2/media/%s" % (WP_URL, media_id),
                auth=(WP_USER, WP_APP_PASS),
                json=meta,
                timeout=15,
            )
            if r2.status_code not in (200, 201):
                log.warning("Gorsel meta guncellenemedi: %s" % r2.text[:100])
            else:
                log.info("Gorsel meta guncellendi: media_id=%s" % media_id)

        time.sleep(0.5)  # WP media API rate limit önlemi
        return media_id
    except Exception as e:
        log.error("_upload_image hatasi: %s" % e, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Yardımcı: Wikipedia / Claude
# ---------------------------------------------------------------------------

def _fetch_wikipedia(name):
    """Wikipedia TR → EN özetini çeker. (description + extract)"""
    for lang in ("tr", "en"):
        try:
            r = requests.get(
                "https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (lang, urlquote(name)),
                timeout=10,
            )
            if r.status_code == 200:
                data    = r.json()
                extract = data.get("extract", "")
                desc    = data.get("description", "")
                if len(extract) > 80:
                    full = ("%s\n%s" % (desc, extract)) if desc else extract
                    log.info("Wikipedia %s: %s" % (lang.upper(), name))
                    return full[:3000], lang
        except Exception as e:
            log.warning("Wikipedia %s [%s]: %s" % (lang, name, e))
    return "", "tr"


def _claude(prompt, max_tokens=800):
    """Claude ile kısa metin üretir."""
    try:
        import anthropic
        c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = c.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.error("Claude hatasi: %s" % e)
        return ""


def _extract_dates(text):
    """Wikipedia metninden tarih aralığı çıkarır. MÖ/MS ve yaklaşık tarihler dahil."""
    if not text:
        return "Bilinmiyor"

    patterns = [
        # MÖ formatı Türkçe
        (r"MÖ\s*(\d{3,4})\s*[-\u2013]\s*MÖ?\s*(\d{3,4})", "Tahmini: MÖ {0} \u2013 MÖ {1}"),
        # BC formatı İngilizce: c. 535 – c. 475 BC
        (r"c\.?\s*(\d{3,4})\s*[-\u2013]\s*c\.?\s*(\d{3,4})\s*BC", "Tahmini: MÖ {0} \u2013 MÖ {1}"),
        (r"(\d{3,4})\s*[-\u2013]\s*(\d{3,4})\s*BC", "Tahmini: MÖ {0} \u2013 MÖ {1}"),
        # Parantez içi yıl: (1844-1900)
        (r"\((\d{3,4})\s*[-\u2013]\s*(\d{3,4})\)", "{0} \u2013 {1}"),
        # "535-475 yılları"
        (r"(\d{3,4})\s*[-\u2013]\s*(\d{3,4})\s*yıl", "{0} \u2013 {1}"),
        # "Milattan önce 535-475" veya "milattan evvel"
        (r"[Mm]ilattan\s+(?:önce|evvel|once|evvel)[^\d]*(\d{3,4})[-\u2013](\d{3,4})", "Tahmini: MÖ {0} \u2013 MÖ {1}"),
        # "tahmin" + sayı
        (r"[Tt]ahmin[^\d]*(\d{3,4})[-\u2013](\d{3,4})", "Tahmini: MÖ {0} \u2013 MÖ {1}"),
        # Genel parantez: (c. 535 – c. 475)
        (r"\([^)]*?c\.?\s*(\d{3,4})[^)]*?[-\u2013][^)]*?c\.?\s*(\d{3,4})[^)]*?\)", "Tahmini: MÖ {0} \u2013 MÖ {1}"),
    ]

    for pat, fmt in patterns:
        try:
            m = re.search(pat, text[:800], re.IGNORECASE)
            if m:
                result = fmt.format(m.group(1), m.group(2))
                if len(result) < 60:
                    return result
        except Exception:
            continue

    # Son çare: herhangi bir sayı aralığı
    m = re.search(r"(\d{3,4})\s*[-\u2013]\s*(\d{3,4})", text[:500])
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 100 < a < 2100 and 100 < b < 2100 and abs(a - b) < 200:
            if a < 800:
                return "Tahmini: MÖ %d \u2013 MÖ %d" % (a, b)
            return "%d \u2013 %d" % (a, b)

    return "Bilinmiyor"

def _build_bio(name, wiki_raw, wiki_lang):
    """Wikipedia'yı referans alarak Claude ile özgün biyografi yazar."""
    ataturk = any(x in name.lower() for x in ["atatürk", "mustafa kemal"])
    if ataturk:
        prompt = (
            "Mustafa Kemal Atatürk hakkında Türkçe, akıcı, özgün 3 paragraf biyografi yaz. "
            "HİÇBİR alıntı veya söz kullanma. Sadece hayatını, fikirlerini, katkılarını anlat. "
            "Nutuk ve resmi belgelere dayalı, doğrulanmış bilgiler kullan. "
            "Wikipedia metnini kopyalama.\n\nWikipedia referansı:\n%s\n\nSadece biyografi yaz."
        ) % (wiki_raw[:1500] or "Bilgi bulunamadı.")
    else:
        lang_note = " (İngilizce Wikipedia)" if wiki_lang == "en" else ""
        prompt = (
            "%s hakkında Wikipedia özetini%s referans alarak Türkçe, akıcı, özgün 3 paragraf "
            "biyografi yaz. Kopyalama, kendi cümlelerinle anlat. "
            "Felsefi görüşlerini, yaşam hikayesini ve düşünce dünyasındaki yerini vurgula.\n\n"
            "Wikipedia referansı:\n%s\n\nSadece biyografi yaz."
        ) % (name, lang_note, wiki_raw[:1500] or "Bilgi bulunamadı.")
    bio = _claude(prompt, max_tokens=1000)
    return bio or wiki_raw[:600]



def _ensure_filozof(name, wiki_raw, wiki_lang):
    """
    Filozof taxonomy term'ini bul veya oluştur.
    Mevcut + tamam → ID döndür
    Mevcut + eksik → _update_filozof çağır
    Yok            → _create_filozof çağır
    """
    try:
        r = requests.get(
            "%s/wp-json/wp/v2/filozof" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            params={"search": name, "per_page": 10},
            timeout=15,
        )
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == name.lower():
                    acf      = term.get("acf", {})
                    bio_ok   = bool(acf.get("kisa_biyografi", "").strip())
                    cover_ok = bool(acf.get("filozof_kapak_resmi", ""))
                    if bio_ok and cover_ok:
                        log.info("Filozof tamam: %s (id=%s)" % (name, term["id"]))
                        return term["id"]
                    else:
                        log.info("Filozof eksik alanlari guncelleniyor: %s" % name)
                        return _update_filozof(term["id"], name, wiki_raw, wiki_lang)
    except Exception as e:
        log.warning("Filozof arama hatasi: %s" % e)

    return _create_filozof(name, wiki_raw, wiki_lang)

def _create_filozof(name, wiki_raw, wiki_lang):
    """Yeni filozof taxonomy term oluşturur."""
    log.info("Yeni filozof olusturuluyor: %s" % name)
    bio      = _build_bio(name, wiki_raw, wiki_lang)
    tarihler = _extract_dates(wiki_raw)

    # Kapak görseli: özel 1080x1080, sadece isim
    cover_path = create_square_cover(name)
    cover_id   = None
    if cover_path:
        cover_id = _upload_image(
            cover_path,
            alt_text    = "%s | Felsefemiz.net" % name,
            title       = "%s — Felsefemiz.net" % name,
            caption     = "%s | felsefemiz.net" % name,
            description = "%s felsefi profili — felsefemiz.net" % name,
        )
        if cover_id:
            log.info("Filozof kapak gorseli yuklendi: media_id=%s" % cover_id)
        else:
            log.warning("Filozof kapak gorseli yuklenemedi: %s" % name)
    else:
        log.warning("Kapak gorseli olusturulamadi: %s" % name)

    payload = {
        "name":        name,
        "description": bio,
        "acf": {
            "kisa_biyografi":      bio,
            "yasam_tarihleri":     tarihler,
            "filozof_kapak_resmi": cover_id or "",
        },
    }
    try:
        r = requests.post(
            "%s/wp-json/wp/v2/filozof" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            json=payload,
            timeout=30,
        )
        log.info("Filozof taxonomy POST HTTP %d" % r.status_code)
        if r.status_code in (200, 201):
            tid = r.json()["id"]
            log.info("Filozof olusturuldu: %s (id=%s)" % (name, tid))
            return tid
        else:
            log.error("Filozof POST hatasi: %s" % r.text[:300])
    except Exception as e:
        log.error("Filozof olusturma exception: %s" % e, exc_info=True)
    return None


def _update_filozof(term_id, name, wiki_raw, wiki_lang):
    """Mevcut filozofun eksik alanlarını günceller."""
    bio      = _build_bio(name, wiki_raw, wiki_lang)
    tarihler = _extract_dates(wiki_raw)
    cover_path = create_square_cover(name)
    cover_id   = None
    if cover_path:
        cover_id = _upload_image(
            cover_path,
            alt_text = "%s | Felsefemiz.net" % name,
            title    = "%s — Felsefemiz.net" % name,
        )
    payload = {
        "description": bio,
        "acf": {
            "kisa_biyografi":      bio,
            "yasam_tarihleri":     tarihler,
            "filozof_kapak_resmi": cover_id or "",
        },
    }
    try:
        r = requests.post(
            "%s/wp-json/wp/v2/filozof/%s" % (WP_URL, term_id),
            auth=(WP_USER, WP_APP_PASS),
            json=payload,
            timeout=20,
        )
        log.info("Filozof guncellendi: %s (id=%s) HTTP %d" % (name, term_id, r.status_code))
    except Exception as e:
        log.warning("Filozof guncelleme hatasi: %s" % e)
    return term_id


# ---------------------------------------------------------------------------
# Kategori
# ---------------------------------------------------------------------------

def _ensure_category(akim):
    try:
        r = requests.get(
            "%s/wp-json/wp/v2/categories" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            params={"search": akim, "per_page": 10},
            timeout=15,
        )
        if r.status_code == 200:
            for t in r.json():
                if t["name"].lower() == akim.lower():
                    return t["id"]
    except Exception as e:
        log.warning("Kategori arama: %s" % e)

    # Yeni kategori
    wiki_raw, wiki_lang = _fetch_wikipedia(akim)
    lang_note = " (İngilizce Wikipedia)" if wiki_lang == "en" else ""
    prompt = (
        "'%s' felsefi akımı hakkında Wikipedia özetini%s referans alarak "
        "Türkçe, akıcı, özgün 2-3 paragraf açıklama yaz. Kopyalama, kendi cümlelerinle anlat.\n\n"
        "Wikipedia referansı:\n%s\n\nSadece açıklama yaz."
    ) % (akim, lang_note, wiki_raw[:1500] or "Bilgi bulunamadı.")
    desc = _claude(prompt, max_tokens=600) or ""

    try:
        r2 = requests.post(
            "%s/wp-json/wp/v2/categories" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            json={"name": akim, "description": desc},
            timeout=15,
        )
        if r2.status_code in (200, 201):
            log.info("Kategori olusturuldu: %s" % akim)
            return r2.json()["id"]
        log.error("Kategori olusturulamadi: %s" % r2.text[:200])
    except Exception as e:
        log.error("Kategori exception: %s" % e)
    return None


# ---------------------------------------------------------------------------
# Etiketler
# ---------------------------------------------------------------------------

def _get_or_create_tag(name):
    try:
        r = requests.get(
            "%s/wp-json/wp/v2/tags" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            params={"search": name, "per_page": 5},
            timeout=10,
        )
        if r.status_code == 200:
            for t in r.json():
                if t["name"].lower() == name.lower():
                    return t["id"]
        r2 = requests.post(
            "%s/wp-json/wp/v2/tags" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            json={
                "name":        name,
                "description": "%s ile ilgili felsefi söz ve düşünceler — felsefemiz.net" % name,
            },
            timeout=10,
        )
        if r2.status_code in (200, 201):
            return r2.json()["id"]
    except Exception as e:
        log.warning("Tag hatasi [%s]: %s" % (name, e))
    return None


def _prepare_tags(quote_data):
    raw   = quote_data.get("hashtags", "")
    akim  = quote_data.get("akim", "")
    yazar = quote_data.get("author", "")
    tags  = list(re.findall(r"#(\w+)", raw))
    for extra in [akim, yazar, "Felsefe", "Bilgelik", "Felsefi Söz"]:
        if extra and extra not in tags:
            tags.append(extra)
    ids = []
    for tag in tags[:10]:
        tid = _get_or_create_tag(tag)
        if tid:
            ids.append(tid)
    return ids


# ---------------------------------------------------------------------------
# SEO başlık
# ---------------------------------------------------------------------------

def _build_title(quote_data):
    soz = quote_data.get("quote", "").strip()
    if len(soz) > 80:
        t = soz[:80]
        ls = t.rfind(" ")
        return (t[:ls] if ls > 50 else t).rstrip(",.;:") + "..."
    return soz.rstrip(",.;:")


# ---------------------------------------------------------------------------
# İçerik
# ---------------------------------------------------------------------------

def _build_content(quote_data):
    """
    Yazı içeriği — sadece söz blockquote'u ve hashtag'ler.
    Editörün yorumu ACF aciklama alanına yazılır, buraya değil.
    """
    soz      = quote_data.get("quote", "")
    yazar    = quote_data.get("author", "Anonim")
    akim     = quote_data.get("akim", "Felsefe")
    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")

    parts = []

    # Söz blockquote
    parts.append(
        '<blockquote class="wp-block-quote"><p><em>"%s"</em></p>'
        "<cite>— %s | %s</cite></blockquote>" % (soz, yazar, akim)
    )

    # Hashtag'ler
    parts.append('<p class="felsefemiz-tags">%s</p>' % hashtags)

    return "\n\n".join(parts)


def _build_aciklama(quote_data):
    """
    ACF aciklama alanı için editörün yorumunu Claude ile üretir.
    Yazı içeriğine değil, sadece bu alana yazılır.
    """
    soz      = quote_data.get("quote", "")
    yazar    = quote_data.get("author", "Anonim")
    akim     = quote_data.get("akim", "Felsefe")
    aciklama = quote_data.get("aciklama", "")

    prompt = (
        "Aşağıdaki felsefi sözü analiz ederek Türkçe, akıcı, özgün 4-5 cümlelik editör yorumu yaz. "
        "Sözün modern hayattaki anlamını ve felsefi arka planını vurgula. Kendi cümlelerinle yaz.\n\n"
        "Söz: %s\nYazar: %s\nAkım: %s\nMevcut açıklama: %s"
    ) % (soz, yazar, akim, aciklama)

    editor = _claude(prompt, max_tokens=600)
    return editor or aciklama or (
        "%s felsefesinin bu sözü, modern insanın varoluşsal sorularına ışık tutmaktadır." % akim
    )


# ---------------------------------------------------------------------------
# Ana yayınlama — döner: (url, post_id, media_id)
# ---------------------------------------------------------------------------

def post_to_wordpress(quote_data, post_img):
    if not WP_APP_PASS:
        log.error("WP_APP_PASS eksik!")
        return None, None, None

    yazar    = quote_data.get("author", "Anonim")
    akim     = quote_data.get("akim",   "Felsefe")
    soz      = quote_data.get("quote",  "")
    aciklama = quote_data.get("aciklama", "")

    # 1. Wikipedia biyografi verisi
    log.info("Wikipedia cekiliyor: %s" % yazar)
    wiki_raw, wiki_lang = _fetch_wikipedia(yazar)

    # 2. Filozof taxonomy (kapak görseli burada oluşturulur)
    log.info("Filozof taxonomy: %s" % yazar)
    filozof_id = _ensure_filozof(yazar, wiki_raw, wiki_lang)

    # 3. Kategori
    log.info("Kategori: %s" % akim)
    cat_id = _ensure_category(akim)

    # 4. Etiketler
    log.info("Etiketler hazirlaniyor...")
    tag_ids = _prepare_tags(quote_data)

    # Adımlar arası kısa bekleme — WP API rate limit önlemi
    time.sleep(1)

    # 5. Post görseli yükle (1080x1350 söz görseli)
    log.info("Post gorseli yukleniyor: %s" % post_img)
    soz_k    = soz[:80] + ("..." if len(soz) > 80 else "")
    media_id = _upload_image(
        post_img,
        alt_text    = "%s — %s | Felsefemiz.net" % (soz_k, yazar),
        title       = "%s sözü — %s | Felsefemiz.net" % (yazar, akim),
        caption     = "%s — %s | felsefemiz.net" % (soz_k, yazar),
        description = "%s akımından %s'ye ait felsefi söz görseli. felsefemiz.net" % (akim, yazar),
    )
    if media_id:
        log.info("Post gorseli yuklendi: media_id=%s" % media_id)
    else:
        log.warning("Post gorseli yuklenemedi, devam ediliyor.")

    time.sleep(0.5)

    # 6. Başlık & içerik
    title   = _build_title(quote_data)
    content = _build_content(quote_data)
    excerpt = aciklama or soz[:160]

    # 7. Post oluştur
    # Editörün yorumu — sadece ACF aciklama alanına yaz
    log.info("Editör yorumu üretiliyor...")
    editor_aciklama = _build_aciklama(quote_data)

    post_data = {
        "title":          title,
        "content":        content,
        "excerpt":        excerpt,
        "status":         "publish",
        "categories":     [cat_id]     if cat_id     else [],
        "tags":           tag_ids,
        "filozof":        [filozof_id] if filozof_id else [],
        "acf": {
            "felsefi_soz":  soz,
            "yazar":        yazar,
            "felsefi_akim": akim,
            "aciklama":     editor_aciklama,
            "twitter_text": quote_data.get("twitter", ""),
        },
    }
    if media_id:
        post_data["featured_media"] = media_id

    log.info("WP post olusturuluyor: %s" % title)
    try:
        r = requests.post(
            "%s/wp-json/wp/v2/posts" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            json=post_data,
            timeout=45,
        )
        log.info("WP post HTTP %d" % r.status_code)
        if r.status_code not in (200, 201):
            log.error("WP post hatasi: %s" % r.text[:300])
            return None, None, media_id
        resp    = r.json()
        url     = resp.get("link", "")
        post_id = resp.get("id")
        log.info("Yayinlandi: %s (post_id=%s, media_id=%s)" % (url, post_id, media_id))
        return url, post_id, media_id
    except Exception as e:
        log.error("WP post exception: %s" % e, exc_info=True)
        return None, None, media_id


# ---------------------------------------------------------------------------
# Sil — yazı + görsel
# ---------------------------------------------------------------------------

def delete_from_wordpress(post_id, media_id=None):
    """WordPress'ten yazıyı ve görselini kalıcı olarak siler."""
    deleted = []
    if post_id:
        try:
            r = requests.delete(
                "%s/wp-json/wp/v2/posts/%s" % (WP_URL, post_id),
                auth=(WP_USER, WP_APP_PASS),
                params={"force": True},
                timeout=15,
            )
            if r.status_code in (200, 201):
                log.info("WP post silindi: %s" % post_id)
                deleted.append("post:%s" % post_id)
            else:
                log.warning("Post silinemedi: %s" % r.text[:100])
        except Exception as e:
            log.error("Post silme hatasi: %s" % e)
    if media_id:
        try:
            r = requests.delete(
                "%s/wp-json/wp/v2/media/%s" % (WP_URL, media_id),
                auth=(WP_USER, WP_APP_PASS),
                params={"force": True},
                timeout=15,
            )
            if r.status_code in (200, 201):
                log.info("WP media silindi: %s" % media_id)
                deleted.append("media:%s" % media_id)
            else:
                log.warning("Media silinemedi: %s" % r.text[:100])
        except Exception as e:
            log.error("Media silme hatasi: %s" % e)
    return deleted
