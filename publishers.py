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
                  f"Yaniti kesinlikle su formatta ver:\n"
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
    """Terimi arar, yoksa gorsel ve AI bilgileriyle birlikte olusturur."""
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
        
        # 2. AI Bilgilerini Uret
        tarih, biyo = "", ""
        if taxonomy_slug == "filozof":
            tarih, biyo = _generate_philosopher_info(term_name)
        else:
            biyo = f"{term_name} akımı üzerine incelemeler."

        # 3. WordPress'e Terimi Ekle (Senin ACF isimlerinle)
        create_url = "%s/wp-json/wp/v2/%s" % (WP_URL, taxonomy_slug)
        payload = {
            "name": term_name,
            "description": biyo,
            "acf": {
                "filozof_kapak_resmi": media_id,
                "yasam_tarihleri": tarih,
                "kisa_biyografi": biyo
            }
        }
        r_create = requests.post(create_url, auth=(WP_USER, WP_APP_PASS), json=payload, timeout=30)
        if r_create.status_code == 201: 
            return r_create.json()["id"]
            
    except Exception as e:
        log.error("Taksonomi olusturma hatasi: %s" % e)
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
    """WordPress postunu paylasir ve link doner."""
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
    link = r.json().get("link", "")
    log.info("WordPress'e yayinlandi: %s" % link)
    return link

# --- Sosyal Medya Ayarları ---
META_ACCESS_TOKEN    = os.environ.get("META_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
FACEBOOK_PAGE_ID     = os.environ.get("FACEBOOK_PAGE_ID", "")
TWITTER_CONSUMER_KEY    = os.environ.get("TWITTER_CONSUMER_KEY", "")
TWITTER_CONSUMER_SECRET = os.environ.get("TWITTER_CONSUMER_SECRET", "")
TWITTER_ACCESS_TOKEN    = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET   = os.environ.get("TWITTER_ACCESS_SECRET", "")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")
GRAPH = "https://graph.facebook.com/v19.0"

def _upload_to_imgbb(image_path):
    if not IMGBB_API_KEY: raise RuntimeError("IMGBB_API_KEY eksik!")
    with open(image_path, "rb") as f: data = base64.b64encode(f.read()).decode("utf-8")
    r = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": data}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]["url"]

def _post_instagram(image_url, caption):
    r = requests.post("%s/%s/media" % (GRAPH, INSTAGRAM_ACCOUNT_ID), data={"image_url": image_url, "caption": caption, "access_token": META_ACCESS_TOKEN}, timeout=30)
    r.raise_for_status()
    time.sleep(3)
    r2 = requests.post("%s/%s/media_publish" % (GRAPH, INSTAGRAM_ACCOUNT_ID), data={"creation_id": r.json()["id"], "access_token": META_ACCESS_TOKEN}, timeout=30)
    r2.raise_for_status()

def _post_facebook(image_path, caption):
    with open(image_path, "rb") as f:
        r = requests.post("%s/%s/photos" % (GRAPH, FACEBOOK_PAGE_ID), data={"caption": caption, "access_token": META_ACCESS_TOKEN}, files={"source": ("image.jpg", f, "image/jpeg")}, timeout=60)
    r.raise_for_status()

def _tweet_with_image(text, image_path):
    import tweepy
    auth = tweepy.OAuth1UserHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
    api_v1 = tweepy.API(auth)
    client_twitter = tweepy.Client(consumer_key=TWITTER_CONSUMER_KEY, consumer_secret=TWITTER_CONSUMER_SECRET, access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET)
    media_ids = [str(api_v1.media_upload(str(image_path)).media_id)] if image_path and Path(str(image_path)).exists() else None
    client_twitter.create_tweet(text=text[:280], media_ids=media_ids) if media_ids else client_twitter.create_tweet(text=text[:280])

def publish_all(quote_data, post_img, story_img):
    """Tum platformlarda paylasim yapar."""
    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")
    caption = "%s\n\n— %s | %s\n\n%s" % (quote_data["quote"], quote_data["author"], quote_data["akim"], hashtags)

    # 1. WordPress (Once WordPress'i paylasiriz)
    wp_link = post_to_wordpress(quote_data, post_img)

    # 2. Instagram & Facebook
    if META_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID and FACEBOOK_PAGE_ID:
        try:
            image_url = _upload_to_imgbb(post_img)
            _post_instagram(image_url, caption)
        except Exception as e: log.error("Instagram hatasi: %s" % e)
        try: _post_facebook(post_img, caption)
        except Exception as e: log.error("Facebook hatasi: %s" % e)

    # 3. Twitter
    try:
        twitter_text = quote_data.get("twitter") or ("%s\n\n— %s\n\n%s" % (quote_data["quote"][:180], quote_data["author"], hashtags))
        _tweet_with_image(twitter_text[:280], post_img)
    except Exception as e: log.error("Twitter hatasi: %s" % e)
    
    return wp_link
