import os, logging, time, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

# --- WordPress Ayarları ---
WP_URL      = os.environ.get("WP_URL", "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER", "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

def _wp_upload_image(image_path):
    if not WP_APP_PASS: raise RuntimeError("WP_APP_PASS eksik!")
    with open(image_path, "rb") as f: img_data = f.read()
    filename = Path(image_path).name
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        auth=(WP_USER, WP_APP_PASS),
        headers={"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"},
        data=img_data, timeout=60
    )
    r.raise_for_status()
    return r.json()["id"]

def _generate_philosopher_info(term_name):
    """Donmayı önlemek için quote_generator içeride import edilir."""
    try:
        import quote_generator
        client = quote_generator.client
        
        prompt = (f"{term_name} kimdir? Bu düşünürün felsefesini ve hayatını anlatan "
                  f"profesyonel bir yazı yaz. En az 3 paragraf olsun. "
                  f"Format kesinlikle şu olsun:\nTARIH: [Tarihler]\nBIYO: [Metin]")
        
        msg = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        res = msg.content[0].text
        tarih, biyo = "Bilinmiyor", ""
        for line in res.split("\n"):
            if line.strip().startswith("TARIH:"): tarih = line.replace("TARIH:", "").strip()
            if line.strip().startswith("BIYO:"): biyo = line.replace("BIYO:", "").strip()
        
        return tarih, biyo
    except Exception as e:
        log.error(f"AI Bilgi hatası: {e}")
        return "Bilinmiyor", f"{term_name} üzerine felsefi inceleme."

def _ensure_term_with_cover(taxonomy_slug, term_name, subtitle_text):
    if not WP_APP_PASS or not term_name: return None
    search_url = f"{WP_URL}/wp-json/wp/v2/{taxonomy_slug}?search={term_name}"
    try:
        r = requests.get(search_url, auth=(WP_USER, WP_APP_PASS), timeout=30)
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == term_name.lower(): return term["id"]

        from image_generator import create_square_cover
        cover_path = create_square_cover(term_name, subtitle=subtitle_text)
        media_id = _wp_upload_image(cover_path)
        
        tarih, biyo = ("", "") if taxonomy_slug != "filozof" else _generate_philosopher_info(term_name)
        if taxonomy_slug != "filozof": biyo = f"{term_name} akımı incelemesi."

        payload = {
            "name": term_name, "description": biyo,
            "acf": {"filozof_kapak_resmi": media_id, "yasam_tarihleri": tarih, "kisa_biyografi": biyo}
        }
        r_create = requests.post(f"{WP_URL}/wp-json/wp/v2/{taxonomy_slug}", auth=(WP_USER, WP_APP_PASS), json=payload, timeout=30)
        return r_create.json()["id"] if r_create.status_code == 201 else None
    except Exception as e: log.error(f"Taksonomi hatası: {e}"); return None

def _get_or_create_wp_tag(tag_name):
    if not WP_APP_PASS or not tag_name: return None
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={tag_name}", auth=(WP_USER, WP_APP_PASS), timeout=30)
        if r.status_code == 200:
            for tag in r.json():
                if tag["name"].lower() == tag_name.lower(): return tag["id"]
        r_create = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", auth=(WP_USER, WP_APP_PASS), json={"name": tag_name}, timeout=30)
        return r_create.json()["id"] if r_create.status_code == 201 else None
    except Exception: return None

def post_to_wordpress(quote_data, post_img):
    """Ana paylaşım fonksiyonu."""
    if not WP_APP_PASS: return None
    akim = quote_data.get("akim", "Genel felsefe")
    yazar = quote_data.get("author", "Anonim")
    
    cat_id = _ensure_term_with_cover("categories", akim, "Felsefi Akımlar")
    filozof_id = _ensure_term_with_cover("filozof", yazar, "Düşünürler")
    tag_ids = [t for t in [_get_or_create_wp_tag(rt.replace("#", "").strip()) for rt in quote_data.get("hashtags", "").split()] if t]
    
    media_id = None
    try: media_id = _wp_upload_image(post_img)
    except Exception: pass

    post_data = {
        "title": f"{yazar} - {akim} Sözleri", "content": "", "status": "publish",
        "categories": [cat_id] if cat_id else [], "filozof": [filozof_id] if filozof_id else [], "tags": tag_ids,
        "acf": {
            "felsefi_soz": quote_data["quote"], "yazar": yazar, "felsefi_akim": akim,
            "aciklama": quote_data.get("aciklama", ""), "twitter_text": quote_data.get("twitter", "")
        }
    }
    if media_id: post_data["featured_media"] = media_id
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", auth=(WP_USER, WP_APP_PASS), json=post_data, timeout=30)
    return r.json().get("link", "")

def publish_all(quote_data, post_img, story_img):
    """bot.py'ın ImportError vermemesi için bu fonksiyonu burada tutuyoruz."""
    return post_to_wordpress(quote_data, post_img)
