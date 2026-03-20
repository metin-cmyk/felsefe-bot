import os, logging, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

BUFFER_API_KEY = os.environ["BUFFER_API_KEY"]

TWITTER_CONSUMER_KEY    = os.environ["TWITTER_CONSUMER_KEY"]
TWITTER_CONSUMER_SECRET = os.environ["TWITTER_CONSUMER_SECRET"]
TWITTER_ACCESS_TOKEN    = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_SECRET   = os.environ["TWITTER_ACCESS_SECRET"]

def _get_buffer_profiles():
    r = requests.get(
        "https://api.bufferapp.com/1/profiles.json",
        params={"access_token": BUFFER_API_KEY},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def _buffer_post(image_path, caption, profile_ids):
    data = {
        "text":           caption,
        "access_token":   BUFFER_API_KEY,
        "now":            "true",
    }
    for i, pid in enumerate(profile_ids):
        data["profile_ids[%d]" % i] = pid

    # Gorsel yukle
    try:
        with open(image_path, "rb") as f:
            upload = requests.post(
                "https://api.bufferapp.com/1/media/upload.json",
                params={"access_token": BUFFER_API_KEY},
                files={"file": ("image.jpg", f, "image/jpeg")},
                timeout=30,
            )
        if upload.status_code == 200:
            media_id = upload.json().get("id")
            if media_id:
                data["media[photo_id]"] = media_id
    except Exception as e:
        log.warning("Gorsel yuklenemedi: %s" % e)

    r = requests.post(
        "https://api.bufferapp.com/1/updates/create.json",
        data=data,
        timeout=30,
    )
    log.info("Buffer response: %d %s" % (r.status_code, r.text[:200]))
    r.raise_for_status()
    return r.json()

def _tweet_with_image(text, image_path):
    """Twitter API v1.1 ile gorsel yukle, v2 ile tweet at."""
    import tweepy

    auth = tweepy.OAuth1UserHandler(
        TWITTER_CONSUMER_KEY,
        TWITTER_CONSUMER_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
    )
    api_v1 = tweepy.API(auth)
    client  = tweepy.Client(
        consumer_key=TWITTER_CONSUMER_KEY,
        consumer_secret=TWITTER_CONSUMER_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )

    media_ids = None
    if image_path and Path(str(image_path)).exists():
        media    = api_v1.media_upload(str(image_path))
        media_ids = [str(media.media_id)]
        log.info("Twitter media yuklendi: %s" % media.media_id)

    if media_ids:
        resp = client.create_tweet(text=text[:280], media_ids=media_ids)
    else:
        resp = client.create_tweet(text=text[:280])

    log.info("Tweet atildi: %s" % resp.data)

def publish_all(quote_data, post_img, story_img):
    caption = "%s\n\n— %s | %s" % (
        quote_data["quote"],
        quote_data["author"],
        quote_data["akim"],
    )

    # Buffer — Instagram + Facebook
    try:
        profiles    = _get_buffer_profiles()
        profile_ids = [p["id"] for p in profiles]
        log.info("Buffer profilleri: %s" % [p.get("service") for p in profiles])
        _buffer_post(post_img, caption, profile_ids)
        log.info("Buffer'a gonderildi!")
    except Exception as e:
        log.error("Buffer hatasi: %s" % e)

    # Twitter
    try:
        twitter_text = quote_data.get("twitter") or (
            '"%s"\n\n— %s\n\n#Felsefe #Bilgelik' % (
                quote_data["quote"][:180],
                quote_data["author"]
            )
        )
        _tweet_with_image(twitter_text[:280], post_img)
    except Exception as e:
        log.error("Twitter hatasi: %s" % e)
