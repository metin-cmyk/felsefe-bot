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
    """Wikipedia'dan ham özet metnini çeker. Önce TR, sonra EN dener."""
    for lang in ("tr", "en"):
        try:
            url = "https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (lang, urlquote(name))
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                extract = r.json().get("extract", "")
                if len(extract) > 80:
                    return extract[:3000], lang
        except Exception as e:
            log.warning("Wikipedia %s hatasi (%s): %s" % (lang, name, e))
    return "", "tr"

# ---------------------------------------------------------------------------
# Claude ile özgün metin üret
# ---------------------------------------------------------------------------

def _claude_rewrite(prompt_text):
    """Anthropic API ile özgün Türkçe paragraf üretir."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt_text}]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.error("Claude rewrite hatasi: %s" % e)
        return ""

def _build_philosopher_bio(name, wiki_raw, wiki_lang):
    """
    Filozofun biyografisini Wikipedia verisini referans alarak
    Claude'un kendi cümlesiyle yazar.
    Atatürk için özel kural: sadece doğrulanmış sözlerini kullan.
    """
    ataturk_names = ["Mustafa Kemal Atatürk", "Atatürk", "Mustafa Kemal", "M. Kemal Atatürk"]
    is_ataturk = any(n.lower() in name.lower() for n in ataturk_names)

    if is_ataturk:
        prompt = (
            "Mustafa Kemal Atatürk hakkında Türkçe, akıcı ve özgün 3 paragraf bir biyografi yaz. "
            "ÖNEMLI KURALLAR:\n"
            "1. Atatürk'e atfedilen hiçbir alıntı veya söz kullanma — yalnızca hayatını, "
            "fikirlerini ve katkılarını anlat.\n"
            "2. Bilgileri Wikipedia'dan aldım ama cümleleri tamamen kendin kur, kopyalama.\n"
            "3. Nutuk ve resmi belgelerde geçen gerçek tarihi bilgilere dayalı yaz.\n"
            "Wikipedia özeti (referans için):\n%s\n\n"
            "Sadece biyografi metnini yaz, başlık veya açıklama ekleme."
        ) % (wiki_raw[:1500] if wiki_raw else "Bilgi bulunamadı.")
    else:
        lang_note = "(İngilizce Wikipedia'dan alındı, Türkçe bulunamadı)" if wiki_lang == "en" else ""
        prompt = (
            "Aşağıdaki Wikipedia özetini referans alarak %s hakkında "
            "Türkçe, akıcı ve özgün 3 paragraf bir biyografi yaz. "
            "Wikipedia metnini kopyalama — tamamen kendi cümlelerinle anlat. "
            "Felsefi görüşlerini, yaşam hikayesini ve düşünce dünyasındaki yerini vurgula. %s\n\n"
            "Wikipedia özeti:\n%s\n\n"
            "Sadece biyografi metnini yaz, başlık veya açıklama ekleme."
        ) % (name, lang_note, wiki_raw[:1500] if wiki_raw else "Bilgi bulunamadı.")

    bio = _claude_rewrite(prompt)
    return bio if bio else (wiki_raw[:800] if wiki_raw else "")

def _build_category_description(akim, wiki_raw, wiki_lang):
    """
    Felsefi akım / kategori için Wikipedia verisini referans alarak
    Claude'un kendi cümlesiyle açıklama yazar.
    """
    lang_note = "(İngilizce Wikipedia'dan alındı)" if wiki_lang == "en" else ""
    prompt = (
        "Aşağıdaki Wikipedia özetini referans alarak '%s' felsefi akımı hakkında "
        "Türkçe, akıcı ve özgün 2-3 paragraf bir açıklama yaz. "
        "Wikipedia metnini kopyalama — tamamen kendi cümlelerinle anlat. "
        "Bu akımın temel ilkelerini, tarihsel arka planını ve günümüzdeki etkisini vurgula. %s\n\n"
        "Wikipedia özeti:\n%s\n\n"
        "Sadece açıklama metnini yaz, başlık veya açıklama ekleme."
    ) % (akim, lang_note, wiki_raw[:1500] if wiki_raw else "Bilgi bulunamadı.")

    desc = _claude_rewrite(prompt)
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
        data=img_data,
        timeout=60,
    )
    log.info("WP media upload HTTP %d" % r.status_code)
    r.raise_for_status()
    return r.json()["id"]

# ---------------------------------------------------------------------------
# Kategori ve etiket yönetimi
# ---------------------------------------------------------------------------

def _get_or_create_term(taxonomy, name, description=""):
    """Kategori/etiketi bul, yoksa açıklamayla birlikte oluştur. ID döndür."""
    try:
        r = requests.get(
            "%s/wp-json/wp/v2/%s" % (WP_URL, taxonomy),
            auth=(WP_USER, WP_APP_PASS),
            params={"search": name, "per_page": 5},
            timeout=15,
        )
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == name.lower():
                    return term["id"]

        # Yoksa oluştur
        payload = {"name": name}
        if description:
            payload["description"] = description
        r2 = requests.post(
            "%s/wp-json/wp/v2/%s" % (WP_URL, taxonomy),
            auth=(WP_USER, WP_APP_PASS),
            json=payload,
            timeout=15,
        )
        if r2.status_code in (200, 201):
            return r2.json()["id"]
    except Exception as e:
        log.warning("Terim olusturma hatasi (%s - %s): %s" % (taxonomy, name, e))
    return None

def _prepare_category(quote_data):
    """Akım için kategori oluştur — Wikipedia + Claude açıklamasıyla."""
    akim = quote_data.get("akim", "Felsefe")

    # Önce mevcut mi kontrol et
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
                    return [term["id"]]
    except Exception:
        pass

    # Yeni kategori — Wikipedia + Claude açıklaması
    log.info("Yeni kategori icin Wikipedia cekiliyor: %s" % akim)
    wiki_raw, wiki_lang = _fetch_wikipedia_raw(akim)
    description = _build_category_description(akim, wiki_raw, wiki_lang)

    cat_id = _get_or_create_term("categories", akim, description)
    return [cat_id] if cat_id else []

def _prepare_tags(quote_data):
    """Hashtag'lerden + akım + yazar + sabit etiketlerden tag ID listesi oluştur."""
    hashtags_raw = quote_data.get("hashtags", "")
    akim  = quote_data.get("akim", "")
    yazar = quote_data.get("author", "")

    tags = []
    for tag in re.findall(r"#(\w+)", hashtags_raw):
        tags.append(tag)
    if akim and akim not in tags:
        tags.append(akim)
    if yazar and yazar not in tags:
        tags.append(yazar)
    for fixed in ["Felsefe", "Bilgelik", "Felsefi Söz"]:
        if fixed not in tags:
            tags.append(fixed)

    tag_ids = []
    for tag in tags[:10]:
        tid = _get_or_create_term("tags", tag)
        if tid:
            tag_ids.append(tid)
    return tag_ids

# ---------------------------------------------------------------------------
# SEO uyumlu başlık
# ---------------------------------------------------------------------------

def _build_title(quote_data):
    soz   = quote_data.get("quote", "")
    yazar = quote_data.get("author", "Anonim")
    max_len = 55
    if len(soz) > max_len:
        truncated = soz[:max_len]
        last_space = truncated.rfind(" ")
        soz_kisalt = (truncated[:last_space] if last_space > 30 else truncated).rstrip(",.;:") + "..."
    else:
        soz_kisalt = soz.rstrip(",.;:")
    return "%s — %s" % (soz_kisalt, yazar)

# ---------------------------------------------------------------------------
# Özgün ve uzun içerik
# ---------------------------------------------------------------------------

def _build_content(quote_data, philosopher_bio):
    soz      = quote_data.get("quote", "")
    yazar    = quote_data.get("author", "Anonim")
    akim     = quote_data.get("akim", "Felsefe")
    aciklama = quote_data.get("aciklama", "")
    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")

    parts = []

    # 1. Ana söz
    parts.append("""<blockquote class="wp-block-quote">
<p><em>"%s"</em></p>
<cite>— %s | %s</cite>
</blockquote>""" % (soz, yazar, akim))

    # 2. Editör yorumu (uzun ve özgün)
    if aciklama:
        editor_prompt = (
            "Aşağıdaki felsefi söz ve kısa açıklamasını referans alarak "
            "Türkçe, akıcı ve özgün bir editör yorumu yaz (4-5 cümle). "
            "Bu sözün modern hayattaki anlamını ve insana katkısını vurgula. "
            "Kopyalama, tamamen kendi cümlelerinle yaz.\n\n"
            "Söz: %s\nYazar: %s\nAkım: %s\nKısa açıklama: %s"
        ) % (soz, yazar, akim, aciklama)
        editor_text = _claude_rewrite(editor_prompt)
        if not editor_text:
            editor_text = aciklama
    else:
        editor_prompt = (
            "Aşağıdaki felsefi sözü analiz ederek Türkçe, akıcı ve özgün bir editör yorumu yaz (4-5 cümle). "
            "Sözün modern hayattaki anlamını, insana katkısını ve felsefi arka planını vurgula.\n\n"
            "Söz: %s\nYazar: %s\nAkım: %s"
        ) % (soz, yazar, akim)
        editor_text = _claude_rewrite(editor_prompt)
        if not editor_text:
            editor_text = "%s felsefesinin derinliklerinden gelen bu söz, modern insanın varoluşsal sorularına ışık tutmaktadır." % akim

    parts.append("""<h2>Editörün Yorumu</h2>
<p>%s</p>""" % editor_text)

    # 3. Filozof biyografisi
    if philosopher_bio:
        parts.append("""<h2>%s Kimdir?</h2>
<p>%s</p>""" % (yazar, philosopher_bio.replace("\n\n", "</p><p>")))

    # 4. Hashtag'ler
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

    # 1. Wikipedia'dan filozofun ham metnini çek
    log.info("Wikipedia'dan filozof bilgisi cekiliyor: %s" % yazar)
    wiki_raw, wiki_lang = _fetch_wikipedia_raw(yazar)

    # 2. Claude ile özgün biyografi yaz
    log.info("Claude ile biyografi yaziliyor: %s" % yazar)
    philosopher_bio = _build_philosopher_bio(yazar, wiki_raw, wiki_lang)

    # 3. Başlık
    title = _build_title(quote_data)
    log.info("Baslik: %s" % title)

    # 4. İçerik (editör yorumu + biyografi)
    content = _build_content(quote_data, philosopher_bio)

    # 5. Özet
    excerpt = aciklama if aciklama else soz[:160]

    # 6. Kategori (Wikipedia + Claude açıklamasıyla)
    log.info("Kategori hazirlaniyor: %s" % akim)
    categories = _prepare_category(quote_data)

    # 7. Etiketler
    log.info("Etiketler hazirlaniyor...")
    tag_ids = _prepare_tags(quote_data)

    # 8. Görsel yükle
    media_id = None
    try:
        media_id = _wp_upload_image(post_img)
        log.info("Gorsel yuklendi, media_id: %s" % media_id)
    except Exception as e:
        log.error("Gorsel yuklenemedi: %s" % e)

    # 9. Post oluştur
    post_data = {
        "title":          title,
        "content":        content,
        "excerpt":        excerpt,
        "status":         "publish",
        "categories":     categories,
        "tags":           tag_ids,
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
        json=post_data,
        timeout=30,
    )
    log.info("WP post HTTP %d: %s" % (r.status_code, r.text[:300]))
    r.raise_for_status()
    url = r.json().get("link", "")
    log.info("WordPress'e yayinlandi: %s" % url)
    return url
