import os, logging, time, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WordPress
# ---------------------------------------------------------------------------

WP_URL      = os.environ.get("WP_URL", "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER", "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

def _wp_upload_image(image_path):
    """Görseli WordPress media kütüphanesine yükle, media ID döndür."""
    if not WP_APP_PASS:
        raise RuntimeError("WP_APP_PASS eksik!")
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
    log.info("WP media upload HTTP %d: %s" % (r.status_code, r.text[:200]))
    r.raise_for_status()
    media_id = r.json()["id"]
    log.info("WP gorsel yuklendi, media_id: %s" % media_id)
    return media_id

def post_to_wordpress(quote_data, post_img):
    """Felsefi sozu gorseliyle birlikte WordPress'e yayinla."""
    if not WP_APP_PASS:
        log.warning("WP_APP_PASS eksik, WordPress atlaniyor.")
        return None

    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")

    # Başlık: sözün ilk 60 karakteri
    title = quote_data["quote"][:60]

    # İçerik: tam söz + yazar + akım + açıklama + hashtagler
    aciklama = quote_data.get("aciklama", "")
    content = """<blockquote>
<p>%s</p>
<cite>— %s | %s</cite>
</blockquote>

%s

<p>%s</p>""" % (
        quote_data["quote"],
        quote_data["author"],
        quote_data["akim"],
        aciklama,
        hashtags,
    )

    # Önce görseli yükle
    media_id = None
    try:
        media_id = _wp_upload_image(post_img)
    except Exception as e:
        log.error("WP gorsel yuklenemedi: %s" % e, exc_info=True)

    # Post oluştur
    post_data = {
        "title":   title,
        "content": content,
        "status":  "publish",
        "categories": [],
    }
    if media_id:
        post_data["featured_media"] = media_id

    r = requests.post(
        "%s/wp-json/wp/v2/posts" % WP_URL,
        auth=(WP_USER, WP_APP_PASS),
        json=post_data,
        timeout=30,
    )
    log.info("WP post HTTP %d: %s" % (r.status_code, r.text[:300]))
    r.raise_for_status()
    post_url = r.json().get("link", "")
    log.info("WordPress'e yayinlandi: %s" % post_url)
    return post_url

META_ACCESS_TOKEN    = os.environ.get("META_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
FACEBOOK_PAGE_ID     = os.environ.get("FACEBOOK_PAGE_ID", "")

TWITTER_CONSUMER_KEY    = os.environ["TWITTER_CONSUMER_KEY"]
TWITTER_CONSUMER_SECRET = os.environ["TWITTER_CONSUMER_SECRET"]
TWITTER_ACCESS_TOKEN    = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_SECRET   = os.environ["TWITTER_ACCESS_SECRET"]

IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")

GRAPH = "https://graph.facebook.com/v19.0"

# ---------------------------------------------------------------------------
# imgbb — Instagram public URL için
# ---------------------------------------------------------------------------

def _upload_to_imgbb(image_path):
    """Görseli imgbb'ye yükle, public URL döndür."""
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY eksik! imgbb.com'dan ucretsiz alin.")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    r = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": data},
        timeout=30,
    )
    log.info("imgbb upload HTTP %d: %s" % (r.status_code, r.text[:200]))
    r.raise_for_status()
    url = r.json()["data"]["url"]
    log.info("Gorsel public URL: %s" % url)
    return url

# ---------------------------------------------------------------------------
# Instagram
# ---------------------------------------------------------------------------

def _post_instagram(image_url, caption):
    # 1. Container oluştur
    r = requests.post(
        "%s/%s/media" % (GRAPH, INSTAGRAM_ACCOUNT_ID),
        data={
            "image_url":    image_url,
            "caption":      caption,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    log.info("Instagram media create HTTP %d: %s" % (r.status_code, r.text[:300]))
    r.raise_for_status()
    creation_id = r.json()["id"]

    # 2. Yayınla
    time.sleep(3)
    r2 = requests.post(
        "%s/%s/media_publish" % (GRAPH, INSTAGRAM_ACCOUNT_ID),
        data={
            "creation_id":  creation_id,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    log.info("Instagram publish HTTP %d: %s" % (r2.status_code, r2.text[:300]))
    r2.raise_for_status()
    log.info("Instagram'a yayinlandi! Post ID: %s" % r2.json().get("id"))

# ---------------------------------------------------------------------------
# Facebook
# ---------------------------------------------------------------------------

def _post_facebook(image_path, caption):
    with open(image_path, "rb") as f:
        r = requests.post(
            "%s/%s/photos" % (GRAPH, FACEBOOK_PAGE_ID),
            data={
                "caption":      caption,
                "access_token": META_ACCESS_TOKEN,
            },
            files={"source": ("image.jpg", f, "image/jpeg")},
            timeout=60,
        )
    log.info("Facebook photo post HTTP %d: %s" % (r.status_code, r.text[:300]))
    r.raise_for_status()
    log.info("Facebook'a yayinlandi! Post ID: %s" % r.json().get("id"))

# ---------------------------------------------------------------------------
# Twitter / X
# ---------------------------------------------------------------------------

def _tweet_with_image(text, image_path):
    import tweepy

    auth = tweepy.OAuth1UserHandler(
        TWITTER_CONSUMER_KEY,
        TWITTER_CONSUMER_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
    )
    api_v1 = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=TWITTER_CONSUMER_KEY,
        consumer_secret=TWITTER_CONSUMER_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )

    media_ids = None
    if image_path and Path(str(image_path)).exists():
        media     = api_v1.media_upload(str(image_path))
        media_ids = [str(media.media_id)]
        log.info("Twitter media yuklendi: %s" % media.media_id)

    if media_ids:
        resp = client.create_tweet(text=text[:280], media_ids=media_ids)
    else:
        resp = client.create_tweet(text=text[:280])
    log.info("Tweet atildi: %s" % resp.data)

# ---------------------------------------------------------------------------
# Ana yayınlama
# ---------------------------------------------------------------------------

def publish_all(quote_data, post_img, story_img):
    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")
    caption = "%s\n\n— %s | %s\n\n%s" % (
        quote_data["quote"],
        quote_data["author"],
        quote_data["akim"],
        hashtags,
    )

    # Instagram + Facebook (Meta key'leri varsa)
    if META_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID and FACEBOOK_PAGE_ID:
        image_url = None
        try:
            image_url = _upload_to_imgbb(post_img)
        except Exception as e:
            log.error("imgbb hatasi, Instagram atlanıyor: %s" % e, exc_info=True)

        if image_url:
            try:
                _post_instagram(image_url, caption)
            except Exception as e:
                log.error("Instagram hatasi: %s" % e, exc_info=True)

        try:
            _post_facebook(post_img, caption)
        except Exception as e:
            log.error("Facebook hatasi: %s" % e, exc_info=True)
    else:
        log.warning("Meta key'leri eksik, Instagram/Facebook atlaniyor.")

    # Twitter / X
    try:
        twitter_text = quote_data.get("twitter") or (
            "%s\n\n— %s\n\n%s" % (
                quote_data["quote"][:180],
                quote_data["author"],
                hashtags,
            )
        )
        _tweet_with_image(twitter_text[:280], post_img)
    except Exception as e:
        log.error("Twitter hatasi: %s" % e, exc_info=True)
