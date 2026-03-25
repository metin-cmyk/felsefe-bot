import os, json, logging, threading, requests, time
from urllib.parse import quote as url_quote
from pathlib import Path

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_last_offset = 0
_awaiting_count = False

def send_notification(post_img, story_img, quote_data):
    key = "quote_%d" % int(time.time())

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

    twitter_text = quote_data.get("twitter") or quote_data["quote"]
    hashtags = quote_data.get("hashtags", "")
    preview = twitter_text[:280] + ("\n\n" + hashtags if hashtags else "")

    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 Yeni İçerik Üret", "callback_data": "new_%s" % key}],
            [{"text": "🔢 X Adet Üret", "callback_data": "multi_%s" % key}],
        ]
    }

    requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": preview, "reply_markup": keyboard},
        timeout=15,
    )

def _send_msg(text):
    requests.post("https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)

def _process_single_generation():
    from quote_generator import generate_quote
    from image_generator import create_post_image, create_story_image
    from bot import _publish
    
    qd = generate_quote()
    pi, pal = create_post_image(qd)
    si = create_story_image(qd, pal)
    _publish(qd, pi)
    send_notification(pi, si, qd)

def _poll():
    global _last_offset, _awaiting_count
    while True:
        try:
            r = requests.get(
                "https://api.telegram.org/bot%s/getUpdates" % TELEGRAM_TOKEN,
                params={"offset": _last_offset + 1, "timeout": 30},
                timeout=40,
            )
            for update in r.json().get("result", []):
                _last_offset = update["update_id"]

                cb = update.get("callback_query", {})
                if cb:
                    data = cb.get("data", "")
                    requests.post("https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN, data={"callback_query_id": cb["id"]}, timeout=10)

                    if data.startswith("new_"):
                        _awaiting_count = False
                        _send_msg("Yeni icerik uretiliyor ve aninda yayinlaniyor...")
                        threading.Thread(target=_process_single_generation, daemon=True).start()

                    elif data.startswith("multi_"):
                        _awaiting_count = True
                        _send_msg("🔢 Kaç adet içerik üretmek istiyorsun? Lütfen sadece bir sayı yaz (Örn: 5)")

                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()

                if not text: continue

                if _awaiting_count:
                    if text.isdigit():
                        count = int(text)
                        _awaiting_count = False
                        if 0 < count <= 20:
                            _send_msg(f"⏳ {count} adet içerik üretimi başlıyor. Her paylaşım arası 30 sn beklenecek...")
                            def _gen_multi(c):
                                for i in range(c):
                                    _send_msg(f"🔄 Üretiliyor: {i+1} / {c}")
                                    _process_single_generation()
                                    if i < c - 1: time.sleep(30)
                                _send_msg("✅ Toplu üretim başarıyla tamamlandı!")
                            threading.Thread(target=_gen_multi, args=(count,), daemon=True).start()
                        else:
                            _send_msg("Lütfen 1 ile 20 arasında geçerli bir sayı girin.")
                    else:
                        _awaiting_count = False
                        _send_msg("❌ Geçerli sayı girmediniz. İptal edildi.")
                    continue

                if text == "/start":
                    _awaiting_count = False
                    _send_msg("FelsefeCo Bot aktif!\n/yeni - hemen uret\n/durum - bot durumu")
                elif text == "/yeni":
                    _awaiting_count = False
                    _send_msg("Yeni icerik uretiliyor...")
                    threading.Thread(target=_process_single_generation, daemon=True).start()
                elif text == "/durum":
                    posted_file = Path("posted.json")
                    count = len(json.loads(posted_file.read_text())) if posted_file.exists() else 0
                    _send_msg(f"Bot calisiyor!\nToplam paylasilan: {count}\nZamanlama: 09:00, 13:00, 20:00")

        except Exception as e:
            log.warning("Polling hatasi: %s" % e)
            time.sleep(5)

def start_listener():
    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    log.info("Telegram listener basladi.")
