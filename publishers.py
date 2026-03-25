import os, logging, requests, re
from pathlib import Path
from urllib.parse import quote as urlquote

log = logging.getLogger(__name__)

WP_URL      = os.environ.get("WP_URL", "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER", "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

# ---------------------------------------------------------------------------
# Wikipedia'dan ham metin çek
# ---------------------------------------------------------------------------

def _fetch_wikipedia_raw(name):
    """Wikipedia'dan ham özet ve description metnini çeker. Önce TR, sonra EN dener."""
    for lang in ("tr", "en"):
        try:
            url = "https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (lang, urlquote(name))
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data    = r.json()
                extract = data.get("extract", "")
                desc    = data.get("description", "")  # Örn: "German philosopher (1889–1951)"
                if len(extract) > 80:
                    log.info("Wikipedia %s bulundu: %s" % (lang.upper(), name))
                    # description'ı extract'ın başına ekle — tarih çıkarma için
                    full_text = ("%s\n%s" % (desc, extract)) if desc else extract
                    return full_text[:3000], lang
        except Exception as e:
            log.warning("Wikipedia %s hatasi (%s): %s" % (lang, name, e))
    return "", "tr"

# ---------------------------------------------------------------------------
# Claude ile özgün metin üret
# ---------------------------------------------------------------------------

def _claude_rewrite(prompt_text, max_tokens=800):
    """Anthropic API ile özgün Türkçe metin üretir."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt_text}]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.error("Claude rewrite hatasi: %s" % e)
        return ""

# ---------------------------------------------------------------------------
# Filozof biyografisi (taxonomy için)
# ---------------------------------------------------------------------------

def _build_philosopher_bio(name, wiki_raw, wiki_lang):
    """
    Filozofun biyografisini Wikipedia'yı referans alarak Claude'un
    kendi cümlesiyle yazar. Atatürk için özel kural geçerli.
    """
    ataturk_names = ["mustafa kemal atatürk", "atatürk", "mustafa kemal", "m. kemal atatürk"]
    is_ataturk = any(n in name.lower() for n in ataturk_names)

    if is_ataturk:
        prompt = (
            "Mustafa Kemal Atatürk hakkında Türkçe, akıcı ve özgün 3 paragraf biyografi yaz.\n"
            "ZORUNLU KURALLAR:\n"
            "1. Atatürk'e atfedilen hiçbir alıntı veya söz kullanma.\n"
            "2. Yalnızca hayatını, fikirlerini ve katkılarını kendi cümlelerinle anlat.\n"
            "3. Nutuk ve resmi belgelere dayalı, doğrulanmış tarihi bilgiler kullan.\n"
            "4. Wikipedia metnini kopyalama, tamamen kendi ifadelerinle yaz.\n\n"
            "Wikipedia referansı:\n%s\n\n"
            "Sadece biyografi metnini yaz."
        ) % (wiki_raw[:1500] if wiki_raw else "Bilgi bulunamadı.")
    else:
        lang_note = " (İngilizce Wikipedia)" if wiki_lang == "en" else ""
        prompt = (
            "%s hakkında Wikipedia özetini%s referans alarak "
            "Türkçe, akıcı, özgün 3 paragraf biyografi yaz. "
            "Wikipedia metnini kopyalama, tamamen kendi cümlelerinle anlat. "
            "Felsefi görüşlerini, yaşam hikayesini ve düşünce dünyasındaki yerini vurgula.\n\n"
            "Wikipedia referansı:\n%s\n\n"
            "Sadece biyografi metnini yaz."
        ) % (name, lang_note, wiki_raw[:1500] if wiki_raw else "Bilgi bulunamadı.")

    bio = _claude_rewrite(prompt, max_tokens=1000)
    return bio if bio else (wiki_raw[:800] if wiki_raw else "")

# ---------------------------------------------------------------------------
# Yaşam tarihleri çıkar
# ---------------------------------------------------------------------------

def _extract_dates(wiki_raw, name):
    """Wikipedia metninden doğum/ölüm tarihlerini çıkarır."""
    if not wiki_raw:
        return "Bilinmiyor"

    patterns = [
        # (15 Ekim 1844 – 25 Ağustos 1900) — tam tarihler
        r"\(([^)]*\d{1,2}\s+\w+\s+\d{3,4}[^)]*[\-–][^)]*\d{3,4}[^)]*)\)",
        # (MÖ 470 - MÖ 399) — antik dönem
        r"\(([^)]*MÖ[^)]*\d+[^)]*)\)",
        # (1889–1951) sadece yıllar — description alanından gelir
        r"\((\d{4}\s*[\-–]\s*\d{4})\)",
        # Genel: herhangi bir parantez içinde 3-4 haneli sayı ve tire/dash
        r"\(([^)]*\d{3,4}[^)]*[\-–][^)]*\d{3,4}[^)]*)\)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, wiki_raw[:600])
        if matches:
            # En kısa ve temiz olanı seç
            best = min(matches, key=len)
            if len(best) < 80:  # çok uzunsa atla
                return best.strip()

    return "Bilinmiyor"

# ---------------------------------------------------------------------------
# Kategori açıklaması
# ---------------------------------------------------------------------------

def _build_category_description(akim, wiki_raw, wiki_lang):
    """Felsefi akım için Wikipedia'yı referans alarak Claude ile özgün açıklama yazar."""
    lang_note = " (İngilizce Wikipedia)" if wiki_lang == "en" else ""
    prompt = (
        "'%s' felsefi akımı hakkında Wikipedia özetini%s referans alarak "
        "Türkçe, akıcı, özgün 2-3 paragraf açıklama yaz. "
        "Wikipedia metnini kopyalama, tamamen kendi cümlelerinle anlat. "
        "Temel ilkeleri, tarihsel arka planı ve günümüzdeki etkisini vurgula.\n\n"
        "Wikipedia referansı:\n%s\n\n"
        "Sadece açıklama metnini yaz."
    ) % (akim, lang_note, wiki_raw[:1500] if wiki_raw else "Bilgi bulunamadı.")
    desc = _claude_rewrite(prompt, max_tokens=600)
    return desc if desc else (wiki_raw[:500] if wiki_raw else "")

# ---------------------------------------------------------------------------
# WordPress media yükle
# ---------------------------------------------------------------------------

def _wp_upload_image(image_path):
    with open(image_path, "rb") as f:
        img_data = f.read()
    filename = Path(image_path).name
    r = requests.post(
        "%s/wp-json/wp/v2/media" % WP_URL,
        auth=(WP_USER, WP_APP_PASS),
        headers={
            "Content-Disposition": "attachment; filename=%s" % filename,
            "Content-Type": "image/jpeg",
        },
        data=img_data, timeout=60,
    )
    log.info("WP media upload HTTP %d" % r.status_code)
    r.raise_for_status()
    return r.json()["id"]

# ---------------------------------------------------------------------------
# Filozof taxonomy — bul veya oluştur
# ---------------------------------------------------------------------------

def _ensure_filozof(name, wiki_raw, wiki_lang, cover_img_path=None):
    """
    'filozof' taxonomy'sinde kaydı bul ya da yeni oluştur.
    Yeni oluştururken:
      - kisa_biyografi: Claude ile özgün biyografi
      - yasam_tarihleri: Wikipedia'dan çıkarılmış tarihler
      - filozof_kapak_resmi: kapak görseli media ID (varsa)
    Döner: term ID
    """
    # 1. Mevcut mi ara
    try:
        r = requests.get(
            "%s/wp-json/wp/v2/filozof" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            params={"search": name, "per_page": 5},
            timeout=15,
        )
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == name.lower():
                    term_id = term["id"]
                    # ACF alanları boş veya "Bilinmiyor" ise güncelle
                    acf = term.get("acf", {})
                    bio_empty = not acf.get("kisa_biyografi", "").strip()
                    date_empty = acf.get("yasam_tarihleri", "Bilinmiyor") in ("Bilinmiyor", "", None)
                    cover_empty = not acf.get("filozof_kapak_resmi", "")
                    if bio_empty or date_empty or cover_empty:
                        log.info("Filozof taxonomy bulundu ama eksik alanlar var, guncelleniyor: %s" % name)
                        return None  # Yeniden oluştur
                    log.info("Filozof taxonomy tamam: %s (id=%s)" % (name, term_id))
                    return term_id
    except Exception as e:
        log.warning("Filozof arama hatasi: %s" % e)

    # 2. Yeni oluştur
    log.info("Yeni filozof taxonomy olusturuluyor: %s" % name)

    bio      = _build_philosopher_bio(name, wiki_raw, wiki_lang)
    tarihler = _extract_dates(wiki_raw, name)

    # Kapak görseli yükle (post_img kullanılıyor, ayrı kapak yoksa)
    media_id = None
    if cover_img_path:
        try:
            media_id = _wp_upload_image(
                cover_img_path,
                alt_text  = "%s — Felsefemiz.net" % name,
                title     = "%s | Felsefemiz.net" % name,
                caption   = "%s — Felsefi düşünür profili | felsefemiz.net" % name,
                description = "%s hakkında felsefi inceleme ve biyografi. felsefemiz.net" % name,
            )
            log.info("Filozof kapak gorseli yuklendi: %s" % media_id)
        except Exception as e:
            log.error("Filozof kapak gorseli yuklenemedi: %s" % e)

    # ACF alanlarını da payload'a ekle
    payload = {
        "name":        name,
        "description": bio,
        "acf": {
            "kisa_biyografi":       bio,
            "yasam_tarihleri":      tarihler,
            "filozof_kapak_resmi":  media_id or "",
        }
    }

    try:
        r2 = requests.post(
            "%s/wp-json/wp/v2/filozof" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            json=payload, timeout=20,
        )
        log.info("Filozof taxonomy olusturma HTTP %d: %s" % (r2.status_code, r2.text[:200]))
        if r2.status_code in (200, 201):
            return r2.json()["id"]
    except Exception as e:
        log.error("Filozof taxonomy olusturma hatasi: %s" % e)
    return None

# ---------------------------------------------------------------------------
# Kategori — bul veya oluştur
# ---------------------------------------------------------------------------

def _ensure_category(akim):
    """Kategoriyi bul veya Wikipedia + Claude açıklamasıyla oluştur."""
    try:
        r = requests.get(
            "%s/wp-json/wp/v2/categories" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            params={"search": akim, "per_page": 5},
            timeout=15,
        )
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == akim.lower():
                    log.info("Kategori zaten var: %s" % akim)
                    return term["id"]
    except Exception as e:
        log.warning("Kategori arama hatasi: %s" % e)

    log.info("Yeni kategori icin Wikipedia cekiliyor: %s" % akim)
    wiki_raw, wiki_lang = _fetch_wikipedia_raw(akim)
    description = _build_category_description(akim, wiki_raw, wiki_lang)

    try:
        r2 = requests.post(
            "%s/wp-json/wp/v2/categories" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            json={"name": akim, "description": description},
            timeout=15,
        )
        if r2.status_code in (200, 201):
            return r2.json()["id"]
    except Exception as e:
        log.error("Kategori olusturma hatasi: %s" % e)
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
            timeout=15,
        )
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == name.lower():
                    return term["id"]
        # Etiket yoksa açıklama ile oluştur
        desc = "%s ile ilgili felsefi söz ve düşünceler — felsefemiz.net" % name
        r2 = requests.post(
            "%s/wp-json/wp/v2/tags" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            json={"name": name, "description": desc},
            timeout=15,
        )
        if r2.status_code in (200, 201):
            return r2.json()["id"]
    except Exception as e:
        log.warning("Tag hatasi (%s): %s" % (name, e))
    return None

def _prepare_tags(quote_data):
    hashtags_raw = quote_data.get("hashtags", "")
    akim  = quote_data.get("akim", "")
    yazar = quote_data.get("author", "")
    tags  = list(re.findall(r"#(\w+)", hashtags_raw))
    for extra in [akim, yazar, "Felsefe", "Bilgelik", "Felsefi Söz"]:
        if extra and extra not in tags:
            tags.append(extra)
    tag_ids = []
    for tag in tags[:10]:
        tid = _get_or_create_tag(tag)
        if tid:
            tag_ids.append(tid)
    return tag_ids

# ---------------------------------------------------------------------------
# SEO başlık
# ---------------------------------------------------------------------------

def _build_title(quote_data):
    soz   = quote_data.get("quote", "")
    yazar = quote_data.get("author", "Anonim")
    akim  = quote_data.get("akim", "")
    # SEO: "Söz — Yazar | Felsefemiz" — max 60 karakter soz
    max_len = 50
    if len(soz) > max_len:
        t = soz[:max_len]
        ls = t.rfind(" ")
        soz_k = (t[:ls] if ls > 30 else t).rstrip(",.;:") + "..."
    else:
        soz_k = soz.rstrip(",.;:")
    return "%s — %s" % (soz_k, yazar)

# ---------------------------------------------------------------------------
# İçerik (biyografi artık taxonomy'de, yazıda sadece editör yorumu)
# ---------------------------------------------------------------------------

def _build_content(quote_data):
    soz      = quote_data.get("quote", "")
    yazar    = quote_data.get("author", "Anonim")
    akim     = quote_data.get("akim", "Felsefe")
    aciklama = quote_data.get("aciklama", "")
    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")

    parts = []

    # Ana söz
    parts.append("""<blockquote class="wp-block-quote">
<p><em>"%s"</em></p>
<cite>— %s | %s</cite>
</blockquote>""" % (soz, yazar, akim))

    # Editör yorumu — Claude ile özgün
    editor_prompt = (
        "Aşağıdaki felsefi sözü analiz ederek Türkçe, akıcı, özgün 4-5 cümlelik "
        "bir editör yorumu yaz. Sözün modern hayattaki anlamını, insana katkısını "
        "ve felsefi arka planını vurgula. Kopyalama, tamamen kendi cümlelerinle yaz.\n\n"
        "Söz: %s\nYazar: %s\nAkım: %s\nKısa açıklama: %s"
    ) % (soz, yazar, akim, aciklama)

    editor_text = _claude_rewrite(editor_prompt)
    if not editor_text:
        editor_text = aciklama if aciklama else (
            "%s felsefesinin derinliklerinden gelen bu söz, modern insanın "
            "varoluşsal sorularına ışık tutmaktadır." % akim
        )

    parts.append("""<h2>Editörün Yorumu</h2>
<p>%s</p>""" % editor_text.replace("\n\n", "</p><p>"))

    # Hashtag'ler
    parts.append("""<p class="felsefemiz-tags">%s</p>""" % hashtags)

    return "\n\n".join(parts)

# ---------------------------------------------------------------------------
# Ana yayınlama fonksiyonu
# ---------------------------------------------------------------------------

def post_to_wordpress(quote_data, post_img):
    if not WP_APP_PASS:
        log.warning("WP_APP_PASS eksik, WordPress atlaniyor.")
        return None

    yazar    = quote_data.get("author", "Anonim")
    akim     = quote_data.get("akim", "Felsefe")
    soz      = quote_data.get("quote", "")
    aciklama = quote_data.get("aciklama", "")
    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")

    # 1. Filozof taxonomy — Wikipedia + Claude biyografi + kapak görseli
    log.info("Filozof taxonomy hazirlaniyor: %s" % yazar)
    wiki_raw, wiki_lang = _fetch_wikipedia_raw(yazar)
    filozof_id = _ensure_filozof(yazar, wiki_raw, wiki_lang, cover_img_path=post_img)

    # 2. Kategori — Wikipedia + Claude açıklaması
    log.info("Kategori hazirlaniyor: %s" % akim)
    cat_id = _ensure_category(akim)

    # 3. Etiketler
    log.info("Etiketler hazirlaniyor...")
    tag_ids = _prepare_tags(quote_data)

    # 4. Başlık
    title = _build_title(quote_data)
    log.info("Baslik: %s" % title)

    # 5. İçerik (editör yorumu — biyografi taxonomy'de)
    content = _build_content(quote_data)

    # 6. Özet
    excerpt = aciklama if aciklama else soz[:160]

    # 7. Görseli yükle (post için) — meta tagları ile
    media_id = None
    try:
        soz_kisalt = soz[:80] + ("..." if len(soz) > 80 else "")
        media_id = _wp_upload_image(
            post_img,
            alt_text    = "%s — %s | Felsefemiz.net" % (soz_kisalt, yazar),
            title       = "%s sözü — %s | Felsefemiz.net" % (yazar, akim),
            caption     = "%s — %s | felsefemiz.net" % (soz_kisalt, yazar),
            description = "%s akımından %s'ye ait felsefi söz görseli. felsefemiz.net" % (akim, yazar),
        )
        log.info("Post gorseli yuklendi, media_id: %s" % media_id)
    except Exception as e:
        log.error("Post gorseli yuklenemedi: %s" % e)

    # 8. Post oluştur
    post_data = {
        "title":          title,
        "content":        content,
        "excerpt":        excerpt,
        "status":         "publish",
        "categories":     [cat_id] if cat_id else [],
        "tags":           tag_ids,
        "filozof":        [filozof_id] if filozof_id else [],
    }
    if media_id:
        post_data["featured_media"] = media_id

    # ACF alanları
    post_data["acf"] = {
        "felsefi_soz":  soz,
        "yazar":        yazar,
        "felsefi_akim": akim,
        "aciklama":     aciklama,
        "twitter_text": quote_data.get("twitter", ""),
    }

    r = requests.post(
        "%s/wp-json/wp/v2/posts" % WP_URL,
        auth=(WP_USER, WP_APP_PASS),
        json=post_data, timeout=30,
    )
    log.info("WP post HTTP %d: %s" % (r.status_code, r.text[:300]))
    r.raise_for_status()
    url = r.json().get("link", "")
    log.info("WordPress'e yayinlandi: %s" % url)
    return url
