import os, json, logging, threading, requests
from urllib.parse import quote as url_quote
from pathlib import Path

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_last_offset = 0

def send_notification(post_img, story_img, quote_data):
    key = "quote_%d" % int(__import__("time").time())

    # Post + Story görsellerini birlikte gonder
    with open(post_img, "rb") as pf, open(story_img, "rb") as sf:
        requests.post(
            "https://api.telegram.org/bot%s/sendMediaGroup" % TELEGRAM_TOKEN,
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={
                "media": (None, '[{"type":"photo","media":"attach://post","caption":"📐 POST (1080x1350)"},{"type":"photo","media":"attach://story","caption":"📱 STORY (1080x1920)"}]'),
                "post":  ("post.jpg",  pf, "image/jpeg"),
                "story": ("story.jpg", sf, "image/jpeg"),
            },
            timeout=30,
        )

    # Metin (Yalnızca bilgi amaçlı)
    twitter_text = quote_data.get("twitter") or quote_data["quote"]
    preview = twitter_text[:280]

    # Sadece Yeni İçerik Üret butonu kalıyor
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔄 Yeni İçerik Üret", "callback_data": "new_%s" % key},
            ],
        ]
    }

    r = requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        json={
            "chat_id":      TELEGRAM_CHAT_ID,
            "text":         preview,
            "reply_markup": keyboard,
        },
        timeout=15,
    )
    log.info("Mesaj gonderildi. HTTP %d: %s" % (r.status_code, r.text[:200]))

def _send_msg(text):
    requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )

def _poll():
    global _last_offset
    from quote_generator import generate_quote
    from image_generator import create_post_image, create_story_image

    while True:
        try:
            r = requests.get(
                "https://api.telegram.org/bot%s/getUpdates" % TELEGRAM_TOKEN,
                params={"offset": _last_offset + 1, "timeout": 30},
                timeout=40,
            )
            for update in r.json().get("result", []):
                _last_offset = update["update_id"]

                # Buton tiklama
                cb = update.get("callback_query", {})
                if cb:
                    data = cb.get("data", "")
                    requests.post(
                        "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
                        data={"callback_query_id": cb["id"]},
                        timeout=10,
                    )

                    if data.startswith("new_"):
                        _send_msg("Yeni icerik uretiliyor ve aninda yayinlaniyor...")
                        def _regen():
                            qd = generate_quote()
                            pi, pal = create_post_image(qd)
                            si = create_story_image(qd, pal)
                            from bot import _publish
                            _publish(qd, pi, si) # <-- Direk WordPress ve sosyal medyaya atar
                            send_notification(pi, si, qd) # <-- Sonucu Telegram'a bildirir
                        threading.Thread(target=_regen, daemon=True).start()

                # Komutlar
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()

                if text == "/start":
                    _send_msg(
                        "FelsefeCo Bot aktif!\n\n"
                        "Komutlar:\n"
                        "/yeni - hemen yeni icerik uret ve yayinla\n"
                        "/durum - bot durumu"
                    )
                elif text == "/yeni":
                    _send_msg("Yeni icerik uretiliyor ve aninda yayinlaniyor...")
                    def _gen():
                        qd = generate_quote()
                        pi, pal = create_post_image(qd)
                        si = create_story_image(qd, pal)
                        from bot import _publish
                        _publish(qd, pi, si) # <-- Direk WordPress ve sosyal medyaya atar
                        send_notification(pi, si, qd) # <-- Sonucu Telegram'a bildirir
                    threading.Thread(target=_gen, daemon=True).start()

                elif text == "/durum":
                    posted_file = Path("posted.json")
                    count = len(json.loads(posted_file.read_text())) if posted_file.exists() else 0
                    _send_msg("Bot calisiyor!\nToplam paylasilan: %d\nZamanlama: 09:00, 13:00, 20:00" % count)

        except Exception as e:
            log.warning("Polling hatasi: %s" % e)

def start_listener():
    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    log.info("Telegram listener basladi.")
