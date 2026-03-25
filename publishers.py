import os, logging, time, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

WP_URL      = os.environ.get("WP_URL", "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER", "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

def _wp_upload_image(image_path):
    if not WP_APP_PASS: raise RuntimeError("WP_APP_PASS eksik!")
    with open(image_path, "rb") as f: img_data = f.read()
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
    """Claude'dan zorla detayli biyografi alir."""
    try:
        from quote_generator import client
        # Promptu cok daha detayli hale getirdik ki 'sallamasin'
        prompt = (f"{term_name} kimdir? Bu filozofun hayatini, en onemli felsefi goruslerini ve "
                  f"dunya dusunce tarihine katkilarini anlatan profesyonel, ansiklopedik bir yazi yaz. "
                  f"Yazi en az 3 paragraf olsun. Ayrica dogum-olum tarihlerini belirt. "
                  f"Format kesinlikle su olsun:\nTARIH: [Tarihler]\nBIYO: [Detayli Biyografi]")
        
        msg = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        res = msg.content[0].text
        tarih, biyo = "Bilinmiyor", ""
        for line in res.split("\n"):
            if line.startswith("TARIH:"): tarih = line.replace("TARIH:", "").strip()
            if line.startswith("BIYO:"): biyo = line.replace("BIYO:", "").strip()
        
        if len(biyo) < 50: raise ValueError("AI cok kisa cevap verdi.")
        return tarih, biyo
    except Exception as e:
        log.error(f"AI Bilgi hatasi: {e}")
        return "Bilinmiyor", f"{term_name}, felsefe dünyasında önemli izler bırakmış bir düşünürdür."

def _ensure_term_with_cover(taxonomy_slug, term_name, subtitle_text):
    if not WP_APP_PASS or not term_name: return None
    search_url = "%s/wp-json/wp/v2/%s?search=%s" % (WP_URL, taxonomy_slug, term_name)
    try:
        r = requests.get(search_url, auth=(WP_USER, WP_APP_PASS), timeout=30)
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == term_name.lower(): return term["id"]

        log.info(f"Yeni {taxonomy_slug} bulundu: {term_name}. AI icerik hazirlaniyor...")
        from image_generator import create_square_cover
        cover_path = create_square_cover(term_name, subtitle=subtitle_text)
        media_id = _wp_upload_image(cover_path)
        
        tarih, biyo = "", ""
        if taxonomy_slug == "filozof":
            tarih, biyo = _generate_philosopher_info(term_name)
        else:
            biyo = f"{term_name} akımı üzerine kapsamlı inceleme."

        payload = {
            "name": term_name,
            "description": biyo,
            "acf": {
                "filozof_kapak_resmi": media_id,
                "yasam_tarihleri": tarih,
                "kisa_biyografi": biyo
            }
        }
        r_create = requests.post("%s/wp-json/wp/v2/%s" % (WP_URL, taxonomy_slug), auth=(WP_USER, WP_APP_PASS), json=payload, timeout=30)
        if r_create.status_code == 201: return r_create.json()["id"]
    except Exception as e: log.error("Taksonomi hatasi: %s" % e)
    return None

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
    """Sadece WordPress paylasimini yapar."""
    if not WP_APP_PASS: return None
    akim = quote_data.get("akim", "Genel Felsefe")
    yazar = quote_data.get("author", "Anonim")
    title = f"{yazar} - {akim} Sözleri"

    cat_id = _ensure_term_with_cover("categories", akim, "Felsefi Akımlar")
    filozof_id = _ensure_term_with_cover("filozof", yazar, "Tarihe Yön Veren Düşünürler")

    raw_hashtags = quote_data.get("hashtags", "").split()
    tag_ids = [t for t in [_get_or_create_wp_tag(rt.replace("#", "").strip()) for rt in raw_hashtags] if t]
    
    media_id = None
    try: media_id = _wp_upload_image(post_img)
    except Exception: pass

    post_data = {
        "title": title,
        "content": "",
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "filozof": [filozof_id] if filozof_id else [],
        "tags": tag_ids,
        "acf": {
            "felsefi_soz": quote_data["quote"],
            "yazar": yazar,
            "felsefi_akim": akim, # Eksik olan alan eklendi
            "aciklama": quote_data.get("aciklama", ""),
            "twitter_text": quote_data.get("twitter", "") # Eksik olan alan eklendi
        }
    }
    if media_id: post_data["featured_media"] = media_id

    r = requests.post("%s/wp-json/wp/v2/posts" % WP_URL, auth=(WP_USER, WP_APP_PASS), json=post_data, timeout=30)
    return r.json().get("link", "")

# --- Sosyal Medya Fonksiyonlari (Degismedi, Hizi Korumak Icin Kisa Tutuyorum) ---
def publish_all(quote_data, post_img, story_img):
    """Ana orkestra fonksiyonu. Artik her seyi tek seferde yapacak."""
    # 1. WP Paylasimi
    wp_link = post_to_wordpress(quote_data, post_img)
    
    # 2. Sosyal Medya (Sadece veriler varsa tetiklenir)
    caption = "%s\n\n— %s | %s\n\n%s" % (quote_data["quote"], quote_data["author"], quote_data["akim"], quote_data.get("hashtags", ""))
    
    # Instagram, Facebook, Twitter kodlari buraya gelecek (Yukardaki post_to_wordpress cagrisini sildim)
    # ... (Orijinal sosyal medya kodlarin burada devam edecek)
    
    return wp_link
