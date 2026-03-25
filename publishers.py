import os, logging, time, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

# --- WordPress Ayarları ---
WP_URL      = os.environ.get("WP_URL", "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER", "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

def _wp_upload_image(image_path):
    if not WP_APP_PASS:
        raise RuntimeError("WP_APP_PASS eksik!")
    with open(image_path, "rb") as f:
        img_data = f.read()
    filename = Path(image_path).name
    r = requests.post(
        "%s/wp-json/wp/v2/media" % WP_URL,
        auth=(WP_USER, WP_APP_PASS),
        headers={"Content-Disposition": "attachment; filename=%s" % filename, "Content-Type": "image/jpeg"},
        data=img_data, timeout=60
    )
    r.raise_for_status()
    return r.json()["id"]

def _generate_philosopher_info(term_name):
    """Filozof hakkinda biyografi ve yasam tarihlerini uretir."""
    try:
        from quote_generator import client
        
        prompt = (f"{term_name} isimli filozof hakkinda su bilgileri Turkce olarak uret:\n"
                  f"1. Yasam Tarihleri (Ornegin: MÖ 427 - MÖ 347 veya 1844 - 1900)\n"
                  f"2. Kisa Biyografi (2-3 paragraf derinlikli bilgi)\n"
                  f"Yaniti su formatta ver:\n"
                  f"TARIH: [tarih buraya]\n"
                  f"BIYO: [biyografi buraya]")
        
        msg = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        res = msg.content[0].text
        
        tarih = ""
        biyo = ""
        for line in res.split("\n"):
            if line.startswith("TARIH:"): tarih = line.replace("TARIH:", "").strip()
            if line.startswith("BIYO:"): biyo = line.replace("BIYO:", "").strip()
            
        return tarih, biyo
    except Exception as e:
        log.error(f"AI Bilgi uretme hatasi: {e}")
        return "Bilinmiyor", f"{term_name} üzerine felsefi inceleme."

def _ensure_term_with_cover(taxonomy_slug, term_name, subtitle_text):
    """Terimi arar, yoksa gorsel, biyografi ve tarihle birlikte olusturur."""
    if not WP_APP_PASS or not term_name: return None
    
    search_url = "%s/wp-json/wp/v2/%s?search=%s" % (WP_URL, taxonomy_slug, term_name)
    try:
        r = requests.get(search_url, auth=(WP_USER, WP_APP_PASS), timeout=30)
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == term_name.lower(): 
                    return term["id"]

        log.info(f"Yeni {taxonomy_slug} saptandi: {term_name}. Hazirliklar basliyor...")
        
        # 1. Kapak Gorseli Uret
        from image_generator import create_square_cover
        cover_path = create_square_cover(term_name, subtitle=subtitle_text)
        media_id = _wp_upload_image(cover_path)
        
        # 2. Sadece Filozof ise AI bilgilerini uret
        tarih, biyo = "", ""
        if taxonomy_slug == "filozof":
            tarih, biyo = _generate_philosopher_info(term_name)
        else:
            # Akimlar (Kategoriler) icin basit aciklama
            biyo = f"{term_name} akımı üzerine incelemeler."

        # 3. WordPress'e Terimi Ekle (Senin ACF isimlerinle)
        create_url = "%s/wp-json/wp/v2/%s" % (WP_URL, taxonomy_slug)
        payload = {
            "name": term_name,
            "description": biyo, # WP Standart Aciklama
            "acf": {
                "filozof_kapak_resmi": media_id, # Senin yeni slug ismin
                "yasam_tarihleri": tarih,        # Senin yeni slug ismin
                "kisa_biyografi": biyo           # Senin yeni slug ismin
            }
        }
        r_create = requests.post(create_url, auth=(WP_USER, WP_APP_PASS), json=payload, timeout=30)
        if r_create.status_code == 201: 
            return r_create.json()["id"]
            
    except Exception as e:
        log.error("Taksonomi olusturma hatasi: %s" % e)
    return None

# --- Diger Fonksiyonlar (Degismedi) ---

def _get_or_create_wp_tag(tag_name):
    if not WP_APP_PASS or not tag_name: return None
    try:
        r = requests.get("%s/wp-json/wp/v2/tags?search=%s" % (WP_URL, tag_name), auth=(WP_USER, WP_APP_PASS), timeout=30)
        if r.status_code == 200:
            for tag in r.json():
                if tag["name"].lower() == tag_name.lower(): return tag["id"]
        r_create = requests.post("%s/wp-json/wp/v2/tags" % WP_URL, auth=(WP_USER, WP_APP_PASS), json={"name": tag_name}, timeout=30)
        if r_create.status_code == 201: return r_create.json()["id"]
    except Exception: pass
    return None

def post_to_wordpress(quote_data, post_img):
    if not WP_APP_PASS: return None

    akim = quote_data.get("akim", "Genel Felsefe")
    yazar = quote_data.get("author", "Anonim")
    aciklama = quote_data.get("aciklama", "")
    title = f"{yazar} - {akim} Sözleri"

    cat_id = _ensure_term_with_cover("categories", akim, "Felsefi Akımlar")
    filozof_id = _ensure_term_with_cover("filozof", yazar, "Tarihe Yön Veren Düşünürler")

    categories = [cat_id] if cat_id else []
    filozoflar = [filozof_id] if filozof_id else []

    raw_hashtags = quote_data.get("hashtags", "").split()
    tag_ids = [t for t in [_get_or_create_wp_tag(rt.replace("#", "").strip()) for rt in raw_hashtags] if t]

    media_id = None
    try: media_id = _wp_upload_image(post_img)
    except Exception as e: log.error("WP gorsel yuklenemedi: %s" % e)

    post_data = {
        "title": title,
        "content": "",
        "status": "publish",
        "categories": categories,
        "filozof": filozoflar,
        "tags": tag_ids,
        "acf": {
            "felsefi_soz": quote_data["quote"],
            "yazar": yazar,
            "aciklama": aciklama
        }
    }
    if media_id: post_data["featured_media"] = media_id

    r = requests.post("%s/wp-json/wp/v2/posts" % WP_URL, auth=(WP_USER, WP_APP_PASS), json=post_data, timeout=30)
    r.raise_for_status()
    log.info("WordPress'e yayinlandi: %s" % r.json().get("link", ""))
    return r.json().get("link", "")

# --- Sosyal Medya Paylasim Fonksiyonlari (Ayni Kaldi) ---
# (Buradan asagisi paylastiginiz orijinal kod ile aynidir, yer kaplamamasi icin kisaltilmistir)
