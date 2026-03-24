import os, json, logging, schedule, time
from pathlib import Path
from datetime import datetime

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image
from publishers import publish_all, post_to_wordpress
from telegram_sender import send_notification, start_listener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

POSTED_FILE = Path("posted.json")

SCHEDULE = [
    "09:00",
    "13:00",
    "20:00",
]

def load_posted():
    if POSTED_FILE.exists():
        return json.loads(POSTED_FILE.read_text())
    return []

def save_posted(posted):
    POSTED_FILE.write_text(json.dumps(posted, ensure_ascii=False, indent=2))

def run():
    hour = datetime.now().hour
    if hour < 8 or hour >= 23:
        log.info("Gece modu, atlaniyor.")
        return

    log.info("Yeni icerik uretiliyor ve otomatik yayinlaniyor...")

    try:
        quote_data = generate_quote()
        log.info("Soz uretildi: %s" % quote_data["quote"][:50])

        post_img, palette = create_post_image(quote_data)
        story_img  = create_story_image(quote_data, palette)

        # Önce WordPress ve sosyal medyada anında yayınla
        _publish(quote_data, post_img, story_img)
        
        # Ardından Telegram'a görselleri ve Yeni Üret butonunu gönder
        send_notification(post_img=post_img, story_img=story_img, quote_data=quote_data)
        
    except Exception as e:
        log.error("Hata: %s" % e, exc_info=True)

def _publish(quote_data, post_img, story_img):
    try:
        from publishers import publish_all, post_to_wordpress
        wp_url = post_to_wordpress(quote_data, post_img)
        publish_all(quote_data, post_img, story_img)
        posted = load_posted()
        posted.append({
            "quote": quote_data["quote"],
            "author": quote_data["author"],
            "time": datetime.now().isoformat(),
            "wp_url": wp_url or "",
        })
        save_posted(posted)
        msg = "✅ Yayinlandi!"
        if wp_url:
            msg += "\n\n🌐 WordPress: %s" % wp_url
        log.info(msg)
        try:
            from telegram_sender import _send_msg
            _send_msg(msg)
        except Exception:
            pass
    except Exception as e:
        log.error("Yayinlama hatasi: %s" % e, exc_info=True)

def main():
    log.info("FelsefeCo Bot basliyor...")

    # Listener'ı başlat
    start_listener()

    for t in SCHEDULE:
        schedule.every().day.at(t).do(run)

    if os.getenv("RUN_NOW", "false") == "true":
        run()

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
