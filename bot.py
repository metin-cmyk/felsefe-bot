import os, json, logging, schedule, time
from pathlib import Path
from datetime import datetime

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image
# publish_all kaldirildi
from publishers import post_to_wordpress
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
    # Gece modu kontrolü (İsteğe bağlı, her saat başı çalışacaksa bunu kaldırabiliriz de)
    hour = datetime.now().hour
    if hour < 8 or hour >= 23:
        log.info("Gece modu (23:00-08:00), içerik üretimi atlanıyor.")
        return

    log.info("--- Yeni içerik üretim süreci başladı ---")

    try:
        # 1. Söz Üret
        quote_data = generate_quote()
        log.info("Söz üretildi: %s" % quote_data["quote"][:50])

        # 2. Görselleri Hazırla
        post_img, palette = create_post_image(quote_data)
        story_img = create_story_image(quote_data, palette)

        # 3. Sadece WordPress'e Gönder
        wp_url = _publish(quote_data, post_img)
        
        # 4. Bildirim Gönder
        send_notification(post_img=post_img, story_img=story_img, quote_data=quote_data)
        
    except Exception as e:
        log.error("İçerik üretim hatası: %s" % e, exc_info=True)

def _publish(quote_data, post_img):
    """Sadece WordPress paylaşımı yapar ve kaydeder."""
    try:
        # publish_all satırı silindi, sadece post_to_wordpress kaldı
        wp_url = post_to_wordpress(quote_data, post_img)
        
        if wp_url:
            posted = load_posted()
            posted.append({
                "quote": quote_data["quote"],
                "author": quote_data["author"],
                "time": datetime.now().isoformat(),
                "wp_url": wp_url,
            })
            save_posted(posted)
            
            msg = "✅ Siteye başarıyla yüklendi!\n🌐 WordPress: %s" % wp_url
            log.info(msg)
            
            # Telegram'a kısa mesaj gönder
            try:
                from telegram_sender import _send_msg
                _send_msg(msg)
            except:
                pass
            
            return wp_url
    except Exception as e:
        log.error("Yayınlama hatası: %s" % e, exc_info=True)
    return None

def main():
    log.info("FelsefeCo Bot (Saatlik Mod) başlatılıyor...")
    start_listener()

    # Zamanlama: Her saat başında çalışır
    schedule.every().hour.at(":00").do(run)

    # Başlangıçta hemen bir tane üretmek istersen RUN_NOW=true yapabilirsin
    if os.getenv("RUN_NOW", "false").lower() == "true":
        run()

    log.info("Bot aktif. Saat başlarını bekliyor...")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
