import os, json, logging, schedule, time
from pathlib import Path
from datetime import datetime

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image
from publishers import post_to_wordpress, delete_from_wordpress
from telegram_sender import send_notification, start_listener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

POSTED_FILE = Path("posted.json")

def load_posted():
    if POSTED_FILE.exists():
        try:
            return json.loads(POSTED_FILE.read_text())
        except:
            return []
    return []

def save_posted(posted):
    POSTED_FILE.write_text(json.dumps(posted, ensure_ascii=False, indent=2))

def run():
    hour = datetime.now().hour
    if hour < 8 or hour >= 23:
        log.info("Gece modu, atlaniyor.")
        return

    log.info("--- Yeni icerik uretim sureci basladi ---")
    try:
        quote_data = generate_quote()

        if not quote_data:
            log.warning("Gercek soz bulunamadi, atlaniyor.")
            from telegram_sender import _send_msg
            _send_msg("⚠️ Gerçek söz bulunamadı, bir sonraki saatte tekrar denenecek.")
            return

        log.info("Soz: %s" % quote_data["quote"][:50])

        # Görseller
        post_img, palette = create_post_image(quote_data)
        story_img = create_story_image(quote_data, palette)

        # Otomatik WordPress yayını
        wp_result = publish_auto(quote_data, post_img)

        # Telegram bildirimi (Sil butonu ile)
        send_notification(
            post_img=post_img,
            story_img=story_img,
            quote_data=quote_data,
            wp_result=wp_result,
        )

    except Exception as e:
        log.error("Icerik uretim hatasi: %s" % e, exc_info=True)


def publish_auto(quote_data, post_img):
    """Direkt WordPress'e yayınlar, onay beklemez."""
    try:
        wp_url, wp_post_id, wp_media_id = post_to_wordpress(quote_data, post_img)
        if wp_url:
            posted = load_posted()
            posted.append({
                "quote":       quote_data["quote"],
                "author":      quote_data["author"],
                "time":        datetime.now().isoformat(),
                "wp_url":      wp_url,
                "wp_post_id":  wp_post_id,
                "wp_media_id": wp_media_id,
            })
            save_posted(posted)
            log.info("Otomatik yayinlandi: %s (post_id=%s)" % (wp_url, wp_post_id))
        return {"url": wp_url, "post_id": wp_post_id, "media_id": wp_media_id}
    except Exception as e:
        log.error("Otomatik yayinlama hatasi: %s" % e, exc_info=True)
        return {}


def main():
    log.info("Felsefemiz Bot basliyor...")
    start_listener()

    schedule.every().hour.at(":00").do(run)

    if os.getenv("RUN_NOW", "false").lower() == "true":
        run()

    log.info("Bot aktif.")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
