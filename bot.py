import os, json, logging, schedule, time, threading, queue
from pathlib import Path
from datetime import datetime

from quote_generator import generate_quote
from image_generator import create_post_image, create_story_image
from publishers import post_to_wordpress, delete_from_wordpress
from telegram_sender import send_notification, start_listener, _send_msg
from flask import Flask

# --- KEEP ALIVE (PING) SUNUCUSU ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Felsefemiz Bot 7/24 Ayakta ve Çalışıyor!"

def run_server():
    # Railway'in atadığı portu otomatik alır, bulamazsa 8080 kullanır
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    log.info("Ping sunucusu baslatildi.")
# ----------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

POSTED_FILE = Path("posted.json")

# ---------------------------------------------------------------------------
# Sıralı yayın kuyruğu — tüm içerikler buradan geçer, sırayla işlenir
# ---------------------------------------------------------------------------
_publish_queue = queue.Queue()
_queue_worker_started = False

def _queue_worker():
    """Tek thread, sırayla çalışır. API rate limit gelirse bekler."""
    log.info("Kuyruk worker baslatildi.")
    while True:
        try:
            item = _publish_queue.get(timeout=5)
            if item is None:
                break
            quote_data, post_img, story_img = item
            _do_publish(quote_data, post_img, story_img)
            _publish_queue.task_done()
            # İçerikler arası bekleme — WP API rate limit önlemi
            time.sleep(15)
        except queue.Empty:
            continue
        except Exception as e:
            log.error("Kuyruk worker hatasi: %s" % e, exc_info=True)
            _publish_queue.task_done()

def start_queue_worker():
    global _queue_worker_started
    if not _queue_worker_started:
        t = threading.Thread(target=_queue_worker, daemon=True)
        t.start()
        _queue_worker_started = True
        log.info("Kuyruk worker thread basladi.")

def enqueue(quote_data, post_img, story_img):
    """İçeriği yayın kuyruğuna ekle."""
    _publish_queue.put((quote_data, post_img, story_img))
    log.info("Kuyruga eklendi: %s (kuyruk boyutu: %d)" % (
        quote_data["author"], _publish_queue.qsize()))

# ---------------------------------------------------------------------------
# Asıl yayın işlemi — retry mekanizması ile
# ---------------------------------------------------------------------------

def _do_publish(quote_data, post_img, story_img):
    """WordPress'e yayınlar. Başarısızsa 3 kez daha dener."""
    author = quote_data.get("author", "?")
    log.info("Yayinlaniyor: %s" % author)

    MAX_RETRY = 4
    RETRY_WAIT = [20, 60, 120, 300]  # saniye — WP API rate limit için

    for attempt in range(MAX_RETRY):
        try:
            url, post_id, media_id = post_to_wordpress(quote_data, post_img)

            if url and post_id:
                # Başarılı — kaydet ve bildir
                _save_posted(quote_data, url, post_id, media_id)
                send_notification(
                    post_img=post_img,
                    story_img=story_img,
                    quote_data=quote_data,
                    wp_result={"url": url, "post_id": post_id, "media_id": media_id},
                )
                log.info("Yayinlandi (%d. deneme): %s" % (attempt + 1, url))
                return

            else:
                log.warning("Yayinlama bos dondü (deneme %d/%d)" % (attempt + 1, MAX_RETRY))

        except Exception as e:
            log.error("Yayinlama hatasi (deneme %d/%d): %s" % (attempt + 1, MAX_RETRY, e))

        if attempt < MAX_RETRY - 1:
            wait = RETRY_WAIT[attempt]
            log.info("API hatasi — %d saniye sessizce bekleniyor... (%s)" % (wait, author))
            time.sleep(wait)

    # Tüm denemeler başarısız — sadece o zaman Telegram'a bildir
    log.error("TUM DENEMELER BASARISIZ: %s" % author)
    _send_msg("❌ %s yayınlanamadı, loglara bakın." % author)

# ---------------------------------------------------------------------------
# Kayıt
# ---------------------------------------------------------------------------

def _save_posted(quote_data, url, post_id, media_id):
    try:
        posted = []
        if POSTED_FILE.exists():
            posted = json.loads(POSTED_FILE.read_text(encoding="utf-8"))
        posted.append({
            "quote":      quote_data["quote"],
            "author":     quote_data["author"],
            "time":       datetime.now().isoformat(),
            "wp_url":     url,
            "post_id":    post_id,
            "media_id":   media_id,
        })
        POSTED_FILE.write_text(json.dumps(posted, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.error("Kayit hatasi: %s" % e)

# ---------------------------------------------------------------------------
# Üretim — sadece üretir, kuyruğa ekler
# ---------------------------------------------------------------------------

def produce_and_enqueue():
    """Söz üretir, görsel yapar, kuyruğa ekler."""
    try:
        quote_data = generate_quote()
        if not quote_data:
            log.warning("Gercek soz bulunamadi, atlaniyor.")
            _send_msg("⚠️ Gerçek söz bulunamadı. /yeni ile tekrar deneyin.")
            return False

        log.info("Soz uretildi: %s — %s" % (quote_data["author"], quote_data["quote"][:40]))
        post_img, palette = create_post_image(quote_data)
        story_img = create_story_image(quote_data, palette)
        enqueue(quote_data, post_img, story_img)
        return True

    except Exception as e:
        log.error("Uretim hatasi: %s" % e, exc_info=True)
        return False

# ---------------------------------------------------------------------------
# Zamanlayıcı
# ---------------------------------------------------------------------------

def run():
    hour = datetime.now().hour
    if hour < 8 or hour >= 23:
        log.info("Gece modu, atlaniyor.")
        return
    log.info("--- Zamanlamali uretim ---")
    produce_and_enqueue()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("Felsefemiz Bot basliyor...")
    start_queue_worker()
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
