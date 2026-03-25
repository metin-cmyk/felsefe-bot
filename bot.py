import os, json, logging, schedule, time
from pathlib import Path
from datetime import datetime

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image
from publishers import post_to_wordpress
from telegram_sender import send_for_approval, start_listener

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
        log.info("Gece modu (23:00-08:00), icerik uretimi atlaniyor.")
        return

    log.info("--- Yeni icerik uretim sureci basladi ---")

    try:
        # 1. Söz üret — Wikiquote'tan gercek soz bulunamazsa None doner
        quote_data = generate_quote()

        if quote_data is None:
            log.warning("Gercek soz bulunamadi, icerik atlaniyor.")
            try:
                from telegram_sender import _send_msg
                _send_msg("⚠️ Bu sefer Wikiquote'tan gerçek söz bulunamadı. İçerik atlandı, bir sonraki saatte tekrar denenecek.")
            except:
                pass
            return

        log.info("Soz uretildi: %s" % quote_data["quote"][:50])

        # 2. Görselleri hazırla
        post_img, palette = create_post_image(quote_data)
        story_img = create_story_image(quote_data, palette)

        # 3. Telegram'a gönder — ONAY BEKLE, otomatik yayınlama YOK
        send_for_approval(
            post_img=post_img,
            story_img=story_img,
            quote_data=quote_data,
        )

    except Exception as e:
        log.error("Icerik uretim hatasi: %s" % e, exc_info=True)

def publish_approved(quote_data, post_img):
    """Telegram'dan onay gelince çağrılır — WordPress'e yayınlar."""
    try:
        wp_url = post_to_wordpress(quote_data, post_img)

        if wp_url:
            posted = load_posted()
            posted.append({
                "quote":  quote_data["quote"],
                "author": quote_data["author"],
                "time":   datetime.now().isoformat(),
                "wp_url": wp_url,
            })
            save_posted(posted)
            log.info("Yayinlandi: %s" % wp_url)
            return wp_url
    except Exception as e:
        log.error("Yayinlama hatasi: %s" % e, exc_info=True)
    return None

def main():
    log.info("Felsefemiz Bot basliyor...")
    start_listener()

    schedule.every().hour.at(":00").do(run)

    if os.getenv("RUN_NOW", "false").lower() == "true":
        run()

    log.info("Bot aktif. Saat baslarini bekliyor...")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
