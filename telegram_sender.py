import os, json, logging, threading, requests, time
from pathlib import Path

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_last_offset    = 0
_pending        = {}   # key -> {post_id, media_id, msg_ids, btn_msg_id}
_awaiting_count = False


# ---------------------------------------------------------------------------
# Temel mesaj fonksiyonları
# ---------------------------------------------------------------------------

def _send_msg(text):
    r = requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )
    return r.json().get("result", {}).get("message_id")

def _delete_msg(message_id):
    requests.post(
        "https://api.telegram.org/bot%s/deleteMessage" % TELEGRAM_TOKEN,
        data={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id},
        timeout=10,
    )

def _edit_reply_markup(message_id, reply_markup):
    requests.post(
        "https://api.telegram.org/bot%s/editMessageReplyMarkup" % TELEGRAM_TOKEN,
        json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id, "reply_markup": reply_markup},
        timeout=10,
    )

def _answer_cb(cb_id, text=""):
    requests.post(
        "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
        data={"callback_query_id": cb_id, "text": text},
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Bildirim gönder — içerik zaten yayında, sadece SİL butonu var
# ---------------------------------------------------------------------------

def send_notification(post_img, story_img, quote_data, wp_result=None):
    """
    İçerik WordPress'e yayınlandıktan SONRA Telegram'a bildirim gönderir.
    Sadece 🗑 Sil butonu var — sil derse WordPress'ten de siler.
    """
    wp_result  = wp_result or {}
    wp_post_id = wp_result.get("post_id")
    wp_media_id= wp_result.get("media_id")
    wp_url     = wp_result.get("url", "")
    key        = "q_%d" % int(time.time())
    msg_ids    = []

    # Görselleri gönder
    try:
        with open(post_img, "rb") as pf, open(story_img, "rb") as sf:
            r = requests.post(
                "https://api.telegram.org/bot%s/sendMediaGroup" % TELEGRAM_TOKEN,
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={
                    "media": (None, '[{"type":"photo","media":"attach://post","caption":"📐 POST"},{"type":"photo","media":"attach://story","caption":"📱 STORY"}]'),
                    "post":  ("post.jpg",  pf, "image/jpeg"),
                    "story": ("story.jpg", sf, "image/jpeg"),
                },
                timeout=30,
            )
            for m in r.json().get("result", []):
                msg_ids.append(m.get("message_id"))
    except Exception as e:
        log.error("Gorsel gonderilemedi: %s" % e)

    # Önizleme metni
    soz      = quote_data.get("quote", "")
    yazar    = quote_data.get("author", "")
    hashtags = quote_data.get("hashtags", "")
    preview  = "%s\n\n— %s" % (soz, yazar)
    if hashtags:
        preview += "\n\n" + hashtags
    if wp_url:
        preview += "\n\n✅ Yayında: %s" % wp_url

    # Sadece Sil butonu
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🗑 Sil (Site + Görsel)", "callback_data": "delete_%s" % key},
                {"text": "🔄 Yeni İçerik",        "callback_data": "new_%s"    % key},
            ],
            [
                {"text": "🔢 Toplu Üret", "callback_data": "multi_%s" % key},
            ],
        ]
    }

    r2 = requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": preview, "reply_markup": keyboard},
        timeout=15,
    )
    btn_msg_id = r2.json().get("result", {}).get("message_id")
    if btn_msg_id:
        msg_ids.append(btn_msg_id)

    _pending[key] = {
        "post_id":   wp_post_id,
        "media_id":  wp_media_id,
        "msg_ids":   msg_ids,
        "btn_msg_id": btn_msg_id,
    }
    log.info("Bildirim gönderildi: %s (wp_post_id=%s)" % (key, wp_post_id))


# ---------------------------------------------------------------------------
# Sil — WordPress + Telegram
# ---------------------------------------------------------------------------

def _do_delete(key, cb_id):
    _answer_cb(cb_id, "Siliniyor...")

    entry = _pending.pop(key, None)
    if not entry:
        _send_msg("⚠️ Bu içerik zaten işlendi.")
        return

    post_id  = entry.get("post_id")
    media_id = entry.get("media_id")
    msg_ids  = entry.get("msg_ids", [])
    btn_msg_id = entry.get("btn_msg_id")

    # WordPress'ten sil
    def _wp_delete():
        from publishers import delete_from_wordpress
        deleted = delete_from_wordpress(post_id, media_id)
        log.info("WordPress'ten silindi: %s" % deleted)

        # Telegram butonunu güncelle
        if btn_msg_id:
            _edit_reply_markup(btn_msg_id, {"inline_keyboard": [[
                {"text": "🗑 Silindi!", "callback_data": "done"}
            ]]})
        # Tüm mesajları sil
        for mid in msg_ids:
            try:
                _delete_msg(mid)
            except Exception:
                pass

    threading.Thread(target=_wp_delete, daemon=True).start()


# ---------------------------------------------------------------------------
# Tek içerik üret
# ---------------------------------------------------------------------------

def _process_single_generation():
    from quote_generator import generate_quote
    from image_generator import create_post_image, create_story_image
    from bot import publish_auto

    qd = generate_quote()
    if not qd:
        _send_msg("⚠️ Wikiquote'tan gerçek söz bulunamadı. /yeni ile tekrar deneyin.")
        return
    pi, pal = create_post_image(qd)
    si = create_story_image(qd, pal)
    wp_result = publish_auto(qd, pi)
    send_notification(pi, si, qd, wp_result)


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

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
                    cb_id = cb["id"]
                    data  = cb.get("data", "")

                    if data.startswith("delete_"):
                        _do_delete(data[7:], cb_id)

                    elif data.startswith("new_"):
                        _pending.pop(data[4:], None)
                        _answer_cb(cb_id)
                        _send_msg("🔄 Yeni içerik üretiliyor...")
                        threading.Thread(target=_process_single_generation, daemon=True).start()

                    elif data.startswith("multi_"):
                        _answer_cb(cb_id)
                        _awaiting_count = True
                        _send_msg("🔢 Kaç adet üreteyim? (1-20)")

                    else:
                        _answer_cb(cb_id)

                msg  = update.get("message", {})
                text = msg.get("text", "").strip()
                if not text:
                    continue

                tlow = text.lower()

                if _awaiting_count:
                    if text.isdigit():
                        count = int(text)
                        _awaiting_count = False
                        if 0 < count <= 20:
                            _send_msg("⏳ %d içerik üretiliyor..." % count)
                            def _gen_multi(c):
                                for i in range(c):
                                    _send_msg("🔄 %d / %d üretiliyor..." % (i+1, c))
                                    _process_single_generation()
                                    if i < c-1: time.sleep(5)
                                _send_msg("✅ Toplu üretim tamamlandı!")
                            threading.Thread(target=_gen_multi, args=(count,), daemon=True).start()
                        else:
                            _send_msg("❌ 1-20 arası bir sayı girin.")
                    else:
                        _awaiting_count = False
                        _send_msg("❌ Geçersiz sayı, iptal edildi.")
                    continue

                if tlow == "/start":
                    _send_msg("Felsefemiz Bot aktif! 🧠\n/yeni — İçerik üret\n/durum — Durum")
                elif tlow == "/yeni":
                    _send_msg("🔄 Yeni içerik üretiliyor...")
                    threading.Thread(target=_process_single_generation, daemon=True).start()
                elif tlow == "/durum":
                    posted_file = Path("posted.json")
                    count = len(json.loads(posted_file.read_text())) if posted_file.exists() else 0
                    _send_msg("✅ Bot çalışıyor!\nToplam yayınlanan: %d" % count)

        except Exception as e:
            log.warning("Polling hatasi: %s" % e)
            time.sleep(5)


def start_listener():
    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    log.info("Telegram listener basladi.")
