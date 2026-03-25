import os, logging, time, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

WP_URL      = os.environ.get("WP_URL", "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER", "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

def _wp_upload_image(image_path):
    with open(image_path, "rb") as f: img_data = f.read()
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        auth=(WP_USER, WP_APP_PASS),
        headers={"Content-Disposition": f"attachment; filename={Path(image_path).name}", "Content-Type": "image/jpeg"},
        data=img_data, timeout=60
    )
    r.raise_for_status()
    return r.json()["id"]

def _generate_philosopher_info(term_name):
    """Donmayı önlemek için import fonksiyon içindedir."""
    try:
        import quote_generator
        client = quote_generator.client
        prompt = (f"{term_name} kimdir? Hayatı ve felsefesi hakkında ansiklopedik, 3 paragraf yazı yaz. "
                  f"Format: TARIH: [Tarihler] BIYO: [Metin]")
        msg = client.messages.create(model="claude-3-5-sonnet-20240620", max_tokens=1500,
                                     messages=[{"role": "user", "content": prompt}])
        res = msg.content[0].text
        tarih, biyo = "Bilinmiyor", ""
        for line in res.split("\n"):
            if line.strip().startswith("TARIH:"): tarih = line.replace("TARIH:", "").strip()
            if line.strip().startswith("BIYO:"): biyo = line.replace("BIYO:", "").strip()
        return tarih, biyo
    except Exception as e:
        return "Bilinmiyor", f"{term_name} üzerine felsefi inceleme."

def _ensure_term_with_cover(taxonomy_slug, term_name, subtitle_text):
    search_url = f"{WP_URL}/wp-json/wp/v2/{taxonomy_slug}?search={term_name}"
    r = requests.get(search_url, auth=(WP_USER, WP_APP_PASS), timeout=30)
    if r.status_code == 200 and r.json():
        for term in r.json():
            if term["name"].lower() == term_name.lower(): return term["id"]

    from image_generator import create_square_cover
    cover_path = create_square_cover(term_name, subtitle=subtitle_text)
    media_id = _wp_upload_image(cover_path)
    tarih, biyo = ("", "") if taxonomy_slug != "filozof" else _generate_philosopher_info(term_name)
    if taxonomy_slug != "filozof": biyo = f"{term_name} akımı incelemesi."

    payload = {"name": term_name, "description": biyo,
               "acf": {"filozof_kapak_resmi": media_id, "yasam_tarihleri": tarih, "kisa_biyografi": biyo}}
    r_create = requests.post(f"{WP_URL}/wp-json/wp/v2/{taxonomy_slug}", auth=(WP_USER, WP_APP_PASS), json=payload, timeout=30)
    return r_create.json()["id"]

def post_to_wordpress(quote_data, post_img):
    akim = quote_data.get("akim", "Genel felsefe")
    yazar = quote_data.get("author", "Anonim")
    cat_id = _ensure_term_with_cover("categories", akim, "Felsefi Akımlar")
    filozof_id = _ensure_term_with_cover("filozof", yazar, "Düşünürler")
    
    media_id = _wp_upload_image(post_img)
    post_data = {
        "title": f"{yazar} - {akim} Sözleri", "status": "publish",
        "categories": [cat_id], "filozof": [filozof_id],
        "acf": {
            "felsefi_soz": quote_data["quote"], "yazar": yazar, "felsefi_akim": akim,
            "aciklama": quote_data.get("aciklama", ""), "twitter_text": quote_data.get("twitter", "")
        },
        "featured_media": media_id
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", auth=(WP_USER, WP_APP_PASS), json=post_data, timeout=30)
    return r.json().get("link", "")
