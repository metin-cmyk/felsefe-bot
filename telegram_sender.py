import os, json, logging, threading, requests, time
from urllib.parse import quote as url_quote
from pathlib import Path

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_last_offset   = 0
_awaiting_count = False

# Bekleyen içerikler: key -> (quote_data, post_img, story_img)
_pending = {}

def send_for_approval(post_img, story_img, quote_data):
    """İçeriği Telegram'a gönder, Onayla / Sil butonları ekle."""
    key = "q_%d" % int(time.time())
    _pending[key] = (quote_data, post_img, story_img)

    # Görselleri gönder
    try:
        with open(post_img, "rb") as pf, open(story_img, "rb") as sf:
            requests.post(
                "https://api.telegram.org/bot%s/sendMediaGroup" % TELEGRAM_TOKEN,
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={
                    "media": (None, '[{"type":"photo","media":"attach://post","caption":"📐 POST"},{"type":"photo","media":"attach://story","caption":"📱 STORY"}]'),
                    "post":  ("post.jpg",  pf, "image/jpeg"),
                    "story": ("story.jpg", sf, "image/jpeg"),
                },
                timeout=30,
            )
    except Exception as e:
        log.error("Gorsel gonderilemedi: %s" % e)

    # Önizleme metin + butonlar
    soz      = quote_data.get("quote", "")
    yazar    = quote_data.get("author", "")
    akim     = quote_data.get("akim", "")
    aciklama = quote_data.get("aciklama", "")
    hashtags = quote_data.get("hashtags", "")

    preview = "%s\n\n— %s | %s" % (soz, yazar, akim)
    if aciklama:
        preview += "\n\n📝 %s" % aciklama
    if hashtags:
        preview += "\n\n%s" % hashtags

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Onayla ve Yayınla", "callback_data": "approve_%s" % key},
                {"text": "🗑 Sil / Atla",        "callback_data": "delete_%s"  % key},
            ],
            [
                {"text": "🔄 Yeniden Üret", "callback_data": "new_%s" % key},
            ],
        ]
    }

    requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": preview, "reply_markup": keyboard},
        timeout=15,
    )

def _send_msg(text):
    requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )

def _process_and_send():
    """Yeni içerik üret ve onay için gönder."""
    from quote_generator import generate_quote
    from image_generator import create_post_image, create_story_image

    try:
        _send_msg("⏳ Yeni içerik üretiliyor...")
        qd = generate_quote()
        pi, pal = create_post_image(qd)
        si = create_story_image(qd, pal)
        send_for_approval(pi, si, qd)
    except Exception as e:
        log.error("Uretim hatasi: %s" % e, exc_info=True)
        _send_msg("❌ İçerik üretilemedi: %s" % str(e)[:200])

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

                # --- Buton tıklamaları ---
                cb = update.get("callback_query", {})
                if cb:
                    data = cb.get("data", "")
                    requests.post(
                        "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
                        data={"callback_query_id": cb["id"]},
                        timeout=10,
                    )

                    if data.startswith("approve_"):
                        key = data[8:]
                        if key in _pending:
                            qd, pi, si = _pending.pop(key)
                            _send_msg("⏳ WordPress'e yükleniyor...")
                            def _publish_thread(q, p):
                                from bot import _publish
                                _publish(q, p)
                            threading.Thread(target=_publish_thread, args=(qd, pi), daemon=True).start()
                        else:
                            _send_msg("⚠️ Bu içerik artık geçerli değil.")

                    elif data.startswith("delete_"):
                        key = data[7:]
                        _pending.pop(key, None)
                        _send_msg("🗑 İçerik silindi / atlandı.")

                    elif data.startswith("new_"):
                        key = data[4:]
                        _pending.pop(key, None)
                        threading.Thread(target=_process_and_send, daemon=True).start()

                    elif data.startswith("multi_"):
                        _awaiting_count = True
                        _send_msg("🔢 Kaç adet içerik üreteyim? (1-20 arası bir sayı yaz)")

                # --- Mesaj komutları ---
                msg  = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                if not text:
                    continue

                if _awaiting_count:
                    if text.isdigit():
                        count = int(text)
                        _awaiting_count = False
                        if 0 < count <= 20:
                            _send_msg("⏳ %d adet içerik üretimi başlıyor..." % count)
                            def _gen_multi(c):
                                for i in range(c):
                                    _send_msg("🔄 Üretiliyor: %d / %d" % (i+1, c))
                                    _process_and_send()
                                    if i < c - 1:
                                        time.sleep(15)
                                _send_msg("✅ Toplu üretim tamamlandı!")
                            threading.Thread(target=_gen_multi, args=(count,), daemon=True).start()
                        else:
                            _send_msg("⚠️ Lütfen 1-20 arası sayı gir.")
                    else:
                        _awaiting_count = False
                        _send_msg("❌ Geçersiz sayı, iptal edildi.")
                    continue

                if text == "/start":
                    _send_msg("🤖 Felsefemiz Bot aktif!\n\n/yeni — içerik üret\n/cok — toplu üret\n/durum — istatistik")
                elif text == "/yeni":
                    threading.Thread(target=_process_and_send, daemon=True).start()
                elif text == "/cok":
                    _awaiting_count = True
                    _send_msg("🔢 Kaç adet üreteyim? (1-20)")
                elif text == "/durum":
                    posted_file = Path("posted.json")
                    count = len(json.loads(posted_file.read_text())) if posted_file.exists() else 0
                    _send_msg("📊 Bot çalışıyor!\nToplam yayınlanan: %d\nBekleyen onay: %d" % (count, len(_pending)))

        except Exception as e:
            log.warning("Polling hatasi: %s" % e)
            time.sleep(5)

def start_listener():
    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    log.info("Telegram listener basladi.")
