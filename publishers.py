import os, logging, requests, tweepy
from pathlib import Path

log = logging.getLogger(__name__)

BUFFER_API_KEY = os.environ["BUFFER_API_KEY"]
BUFFER_API_URL = "https://api.bufferapp.com/1"

TWITTER_CONSUMER_KEY    = os.environ["TWITTER_CONSUMER_KEY"]
TWITTER_CONSUMER_SECRET = os.environ["TWITTER_CONSUMER_SECRET"]
TWITTER_ACCESS_TOKEN    = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_SECRET   = os.environ["TWITTER_ACCESS_SECRET"]

def _get_buffer_profiles():
    r = requests.get(
        "%s/profiles.json" % BUFFER_API_URL,
        params={"access_token": BUFFER_API_KEY},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def _buffer_post(image_path, caption, profile_ids):
    with open(image_path, "rb") as f:
        upload = requests.post(
            "%s/media/upload.json" % BUFFER_API_URL,
            params={"access_token": BUFFER_API_KEY},
            files={"file": f},
            timeout=30,
        )
    
    media_id = None
    if upload.status_code == 200:
        media_id = upload.json().get("id")

    data = {
        "text": caption,
        "profile_ids[]": profile_ids,
        "access_token": BUFFER_API_KEY,
        "now": "true",
    }
    if media_id:
        data["media[photo_id]"] = media_id

    r = requests.post(
        "%s/updates/create.json" % BUFFER_API_URL,
        data=data,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def _tweet(text, image_path=None):
    auth = tweepy.OAuth1UserHandler(
        TWITTER_CONSUMER_KEY,
        TWITTER_CONSUMER_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
    )
    api = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=TWITTER_CONSUMER_KEY,
        consumer_secret=TWITTER_CONSUMER_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )

    media_id = None
    if image_path and Path(image_path).exists():
        media = api.media_upload(str(image_path))
        media_id = media.media_id

    if media_id:
        client.create_tweet(text=text[:280], media_ids=[media_id])
    else:
        client.create_tweet(text=text[:280])

    log.info("Tweet atildi!")

def publish_all(quote_data, post_img, story_img):
    caption = "%s\n\n— %s | %s\n\n%s" % (
        quote_data["quote"],
        quote_data["author"],
        quote_data["akim"],
        quote_data.get("aciklama", ""),
    )

    # Buffer profil ID'lerini al
    try:
        profiles = _get_buffer_profiles()
        profile_ids = [p["id"] for p in profiles]
        log.info("Buffer profilleri: %d adet" % len(profile_ids))

        # Instagram + Facebook → Buffer
        _buffer_post(post_img, caption, profile_ids)
        log.info("Buffer'a gonderildi (Instagram + Facebook)")
    except Exception as e:
        log.error("Buffer hatasi: %s" % e)

    # Twitter → direkt
    try:
        twitter_text = quote_data.get("twitter") or (quote_data["quote"][:200] + " — " + quote_data["author"])
        _tweet(twitter_text[:280], post_img)
        log.info("Twitter'a gonderildi!")
    except Exception as e:
        log.error("Twitter hatasi: %s" % e)
