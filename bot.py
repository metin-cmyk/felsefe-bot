import os, json, logging, schedule, time
from pathlib import Path
from datetime import datetime

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image
from publishers import publish_all
from telegram_sender import send_for_approval, set_approve_callback, start_listener

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

    log.info("Yeni icerik uretiliyor...")

    try:
        quote_data = generate_quote()
        log.info("Soz uretildi: %s" % quote_data["quote"][:50])

        post_img, palette = create_post_image(quote_data)
        story_img  = create_story_image(quote_data, palette)

        send_for_approval(
            post_img=post_img,
            story_img=story_img,
            quote_data=quote_data,
            on_approve=lambda: _publish(quote_data, post_img, story_img),
        )
    except Exception as e:
        log.error("Hata: %s" % e, exc_info=True)

def _publish(quote_data, post_img, story_img):
    try:
        publish_all(quote_data, post_img, story_img)
        posted = load_posted()
        posted.append({
            "quote": quote_data["quote"],
            "author": quote_data["author"],
            "time": datetime.now().isoformat()
        })
        save_posted(posted)
        log.info("Yayinlandi!")
    except Exception as e:
        log.error("Yayinlama hatasi: %s" % e, exc_info=True)

def main():
    log.info("FelsefeCo Bot basliyor...")

    set_approve_callback(_publish)
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
