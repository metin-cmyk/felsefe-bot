import os, logging, time, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

# --- Ayarlar ---
WP_URL      = os.environ.get("WP_URL", "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER", "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

META_ACCESS_TOKEN    = os.environ.get("META_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
FACEBOOK_PAGE_ID     = os.environ.get("FACEBOOK_PAGE_ID", "")
TWITTER_CONSUMER_KEY    = os.environ.get("TWITTER_CONSUMER_KEY", "")
TWITTER_CONSUMER_SECRET = os.environ.get("TWITTER_CONSUMER_SECRET", "")
TWITTER_ACCESS_TOKEN    = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET   = os.environ.get("TWITTER_ACCESS_SECRET", "")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")
GRAPH = "https://graph.facebook.com/v19.0"

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
    """Claude'dan detayli biyografi alir. Donmayi onlemek icin iceride import edilir."""
    try:
        # KRITIK: Donmayi onlemek icin import burada yapilmali
        import quote_generator
        client = quote_generator.client
        
        prompt = (f"{term_name} kimdir? Bu düsünürün felsefesini, hayatini ve en önemli eserlerini "
                  f"anlatan akademik ve derinlikli bir yazi yaz. 3-4 paragraf olsun. "
                  f"Uydurma bilgi verme, ansiklopedik dogruluga sadik kal. "
                  f"Format kesinlikle su olsun:\nTARIH: [Dogum ve Ölüm Yili]\nBIYO: [Detayli Biyografi Metni]")
        
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
        log.error(f"AI Bilgi hatasi: {e}")
        return "Bilinmiyor", f"{term_name} üzerine felsefi bir inceleme."

def _ensure_term_with_cover(taxonomy_slug, term_name, subtitle_text):
    if not WP_APP_PASS or not term_name: return None
    search_url = f"{WP_URL}/wp-json/wp/v2/{taxonomy_slug}?search={term_name}"
    try:
        r = requests.get(search_url, auth=(WP_USER, WP_APP_PASS), timeout=30)
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == term_name.lower(): return term["id"]

        log.info(f"Yeni {taxonomy_slug} saptandi: {term_name}. Hazirliklar basliyor...")
        from image_generator import create_square_cover
        cover_path = create_square_cover(term_name, subtitle=subtitle_text)
        media_id = _wp_upload_image(cover_path)
        
        tarih, biyo = "", ""
        if taxonomy_slug == "filozof":
            tarih, biyo = _generate_philosopher_info(term_name)
        else:
            biyo = f"{term_name} akımı üzerine kapsamlı felsefi inceleme."

        payload = {
            "name": term_name,
            "description": biyo,
            "acf": {
                "filozof_kapak_resmi": media_id,
                "yasam_tarihleri": tarih,
                "kisa_biyografi": biyo
            }
        }
        r_create = requests.post(f"{WP_URL}/wp-json/wp/v2/{taxonomy_slug}", auth=(WP_USER, WP_APP_PASS), json=payload, timeout=30)
        if r_create.status_code == 201: return r_create.json()["id"]
    except Exception as e: log.error(f"Taksonomi hatasi: {e}")
    return None

def _get_or_create_wp_tag(tag_name):
    if not WP_APP_PASS or not tag_name: return None
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={tag_name}", auth=(WP_USER, WP_APP_PASS), timeout=30)
        if r.status_code == 200:
            for tag in r.json():
                if tag["name"].lower() == tag_name.lower(): return tag["id"]
        r_create = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", auth=(WP_USER, WP_APP_PASS), json={"name": tag_name}, timeout=30)
        if r_create.status_code == 201: return r_create.json()["id"]
    except Exception: pass
    return None

def _upload_to_imgbb(image_path):
    if not IMGBB_API_KEY: return None
    with open(image_path, "rb") as f: data = base64.b64encode(f.read()).decode("utf-8")
    r = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": data}, timeout=30)
    return r.json()["data"]["url"] if r.status_code == 200 else None

def post_to_wordpress(quote_data, post_img):
    if not WP_APP_PASS: return None
    akim = quote_data.get("akim", "Genel Felsefe")
    yazar = quote_data.get("author", "Anonim")
    title = f"{yazar} - {akim} Sözleri"

    cat_id = _ensure_term_with_cover("categories", akim, "Felsefi Akimlar")
    filozof_id = _ensure_term_with_cover("filozof", yazar, "Tarihe Yön Veren Düsünürler")

    raw_hashtags = quote_data.get("hashtags", "").split()
    tag_ids = [t for t in [_get_or_create_wp_tag(rt.replace("#", "").strip()) for rt in raw_hashtags] if t]
    
    media_id = None
    try: media_id = _wp_upload_image(post_img)
    except Exception: pass

    post_data = {
        "title": title, "content": "", "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "filozof": [filozof_id] if filozof_id else [],
        "tags": tag_ids,
        "acf": {
            "felsefi_soz": quote_data["quote"],
            "yazar": yazar,
            "felsefi_akim": akim,
            "aciklama": quote_data.get("aciklama", ""),
            "twitter_text": quote_data.get("twitter", "")
        }
    }
    if media_id: post_data["featured_media"] = media_id

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", auth=(WP_USER, WP_APP_PASS), json=post_data, timeout=30)
    return r.json().get("link", "")

def publish_all(quote_data, post_img, story_img):
    """
    Hem WordPress hem de Sosyal Medya paylasimlarini tek noktadan yonetir.
    """
    log.info("Paylasim zinciri tetiklendi...")
    
    # 1. WordPress Paylasimi
    wp_link = post_to_wordpress(quote_data, post_img)
    log.info(f"WordPress Tamam: {wp_link}")
    
    # 2. Sosyal Medya Hazirlik
    caption = f"{quote_data['quote']}\n\n— {quote_data['author']} | {quote_data['akim']}\n\n{quote_data.get('hashtags', '')}"

    # Instagram & Facebook
    if META_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID:
        try:
            img_url = _upload_to_imgbb(post_img)
            if img_url:
                # Instagram
                r = requests.post(f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media", data={"image_url": img_url, "caption": caption, "access_token": META_ACCESS_TOKEN}, timeout=30)
                if r.status_code == 200:
                    requests.post(f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media_publish", data={"creation_id": r.json()["id"], "access_token": META_ACCESS_TOKEN}, timeout=30)
                # Facebook
                with open(post_img, "rb") as f:
                    requests.post(f"{GRAPH}/{FACEBOOK_PAGE_ID}/photos", data={"caption": caption, "access_token": META_ACCESS_TOKEN}, files={"source": f}, timeout=60)
                log.info("Meta paylasimlari tamamlandi.")
        except Exception as e: log.error(f"Meta Hatasi: {e}")

    # Twitter
    if TWITTER_ACCESS_TOKEN:
        try:
            import tweepy
            auth = tweepy.OAuth1UserHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
            api = tweepy.API(auth)
            client_v2 = tweepy.Client(consumer_key=TWITTER_CONSUMER_KEY, consumer_secret=TWITTER_CONSUMER_SECRET, access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET)
            media = api.media_upload(post_img)
            client_v2.create_tweet(text=caption[:280], media_ids=[media.media_id])
            log.info("Twitter paylasimi tamamlandi.")
        except Exception as e: log.error(f"Twitter Hatasi: {e}")

    return wp_link
