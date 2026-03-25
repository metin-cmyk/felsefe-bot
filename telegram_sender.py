import os, json, logging, threading, requests, time
from pathlib import Path

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_last_offset    = 0
_pending        = {}   # key -> {post_id, media_id, msg_ids, btn_msg_id}
_awaiting_count = False

# ---------------------------------------------------------------------------
# Temel Telegram fonksiyonları
# ---------------------------------------------------------------------------

def _send_msg(text):
    """Düz metin mesajı gönderir, message_id döner."""
    try:
        r = requests.post(
            "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": False},
            timeout=15,
        )
        return r.json().get("result", {}).get("message_id")
    except Exception as e:
        log.error("_send_msg hatasi: %s" % e)
        return None

def _edit_text(message_id, text):
    """Mesaj metnini günceller."""
    try:
        requests.post(
            "https://api.telegram.org/bot%s/editMessageText" % TELEGRAM_TOKEN,
            json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id, "text": text,
                  "disable_web_page_preview": False},
            timeout=10,
        )
    except Exception as e:
        log.warning("_edit_text hatasi: %s" % e)

def _edit_reply_markup(message_id, reply_markup):
    """Butonları günceller."""
    try:
        requests.post(
            "https://api.telegram.org/bot%s/editMessageReplyMarkup" % TELEGRAM_TOKEN,
            json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id,
                  "reply_markup": reply_markup},
            timeout=10,
        )
    except Exception as e:
        log.warning("_edit_reply_markup hatasi: %s" % e)

def _delete_msg(message_id):
    """Mesajı siler."""
    try:
        requests.post(
            "https://api.telegram.org/bot%s/deleteMessage" % TELEGRAM_TOKEN,
            data={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id},
            timeout=10,
        )
    except Exception as e:
        log.warning("_delete_msg hatasi (mid=%s): %s" % (message_id, e))

def _answer_cb(cb_id, text=""):
    try:
        requests.post(
            "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
            data={"callback_query_id": cb_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        log.warning("_answer_cb hatasi: %s" % e)

# ---------------------------------------------------------------------------
# Bildirim gönder — içerik yayındaysa ✅ + link + Sil butonu
# ---------------------------------------------------------------------------

def send_notification(post_img, story_img, quote_data, wp_result=None):
    """
    İçerik WordPress'e yayınlandıktan SONRA Telegram'a bildirim gönderir.
    ✅ Yayında linki + 🗑 Sil butonu bulunur.
    """
    wp_result   = wp_result or {}
    wp_post_id  = wp_result.get("post_id")
    wp_media_id = wp_result.get("media_id")
    wp_url      = wp_result.get("url", "")
    key         = "q_%d" % int(time.time())
    msg_ids     = []

    # 1. Görselleri gönder
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
                timeout=60,
            )
            for m in r.json().get("result", []):
                mid = m.get("message_id")
                if mid:
                    msg_ids.append(mid)
        log.info("Gorseller gonderildi (%d mesaj)" % len(msg_ids))
    except Exception as e:
        log.error("Gorsel gonderme hatasi: %s" % e)

    # 2. Önizleme + ✅ yayın linki
    soz      = quote_data.get("quote", "")
    yazar    = quote_data.get("author", "")
    hashtags = quote_data.get("hashtags", "")
    preview  = "%s\n\n— %s" % (soz, yazar)
    if hashtags:
        preview += "\n\n" + hashtags
    if wp_url:
        preview += "\n\n✅ Yayında: %s" % wp_url

    # 3. Butonlar: Sil | Yeni İçerik | Toplu Üret
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🗑 Sil (Site + Görsel)", "callback_data": "delete_%s" % key},
                {"text": "🔄 Yeni İçerik",         "callback_data": "new_%s"    % key},
            ],
            [
                {"text": "🔢 Toplu Üret", "callback_data": "multi_%s" % key},
            ],
        ]
    }

    try:
        r2 = requests.post(
            "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": preview,
                  "reply_markup": keyboard, "disable_web_page_preview": True},
            timeout=15,
        )
        btn_mid = r2.json().get("result", {}).get("message_id")
        if btn_mid:
            msg_ids.append(btn_mid)
    except Exception as e:
        log.error("Buton mesaji gonderme hatasi: %s" % e)
        btn_mid = None

    _pending[key] = {
        "post_id":    wp_post_id,
        "media_id":   wp_media_id,
        "msg_ids":    msg_ids,
        "btn_msg_id": btn_mid,
    }
    log.info("Bildirim gonderildi: key=%s, post_id=%s, msg_ids=%s" % (key, wp_post_id, msg_ids))

# ---------------------------------------------------------------------------
# Sil — WordPress + Telegram
# ---------------------------------------------------------------------------

def _do_delete(key, cb_id):
    _answer_cb(cb_id, "Siliniyor...")

    entry = _pending.pop(key, None)
    if not entry:
        _send_msg("⚠️ Bu içerik zaten işlendi veya bulunamadı.")
        return

    post_id  = entry.get("post_id")
    media_id = entry.get("media_id")
    msg_ids  = entry.get("msg_ids", [])
    btn_mid  = entry.get("btn_msg_id")

    def _wp_sil():
        try:
            from publishers import delete_from_wordpress
            deleted = delete_from_wordpress(post_id, media_id)
            log.info("Silindi: %s" % deleted)
        except Exception as e:
            log.error("WP silme hatasi: %s" % e)

        # Butonu güncelle
        if btn_mid:
            try:
                _edit_reply_markup(btn_mid, {"inline_keyboard": [[
                    {"text": "🗑 Silindi!", "callback_data": "done"}
                ]]})
            except Exception:
                pass

        # Tüm mesajları sil
        for mid in msg_ids:
            try:
                _delete_msg(mid)
                time.sleep(0.3)
            except Exception:
                pass

    threading.Thread(target=_wp_sil, daemon=True).start()

# ---------------------------------------------------------------------------
# Tek içerik üret — kuyruğa ekle
# ---------------------------------------------------------------------------

def _process_single_generation():
    try:
        import __main__ as bot
        ok = bot.produce_and_enqueue()
        if not ok:
            _send_msg("⚠️ Gerçek söz bulunamadı. /yeni ile tekrar deneyin.")
    except Exception as e:
        log.error("Tek uretim hatasi: %s" % e, exc_info=True)
        _send_msg("❌ Üretim hatası: %s" % str(e)[:100])

# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

def _poll():
    global _last_offset, _awaiting_count
    log.info("Telegram polling basliyor...")
    while True:
        try:
            r = requests.get(
                "https://api.telegram.org/bot%s/getUpdates" % TELEGRAM_TOKEN,
                params={"offset": _last_offset + 1, "timeout": 30},
                timeout=40,
            )
            updates = r.json().get("result", [])

            for update in updates:
                _last_offset = update["update_id"]

                # Buton tıklamaları
                cb = update.get("callback_query", {})
                if cb:
                    cb_id = cb["id"]
                    data  = cb.get("data", "")

                    if data.startswith("delete_"):
                        _do_delete(data[7:], cb_id)

                    elif data.startswith("new_"):
                        _pending.pop(data[4:], None)
                        _answer_cb(cb_id, "Üretim başlatıldı...")
                        _send_msg("⏳ Yeni içerik hazırlanıyor, birazdan gönderilecek...")
                        threading.Thread(target=_process_single_generation, daemon=True).start()

                    elif data.startswith("multi_"):
                        _answer_cb(cb_id)
                        _awaiting_count = True
                        _send_msg("🔢 Kaç adet üreteyim? (1-20 arası bir sayı yaz)")

                    else:
                        _answer_cb(cb_id)
                    continue

                # Metin mesajları
                msg  = update.get("message", {})
                text = msg.get("text", "").strip()
                if not text:
                    continue

                tlow = text.lower()

                # Toplu üretim sayısı bekleniyor
                if _awaiting_count:
                    if text.isdigit():
                        count = int(text)
                        _awaiting_count = False
                        if 1 <= count <= 20:
                            _send_msg("⏳ %d içerik sırayla üretilecek ve yayınlanacak..." % count)
                            def _gen_multi(c):
                                import __main__ as bot
                                _send_msg("⏳ %d içerik sırayla üretilip yayınlanacak." % c)
                                basarisiz = 0
                                for i in range(c):
                                    ok = bot.produce_and_enqueue()
                                    if not ok:
                                        basarisiz += 1
                                    time.sleep(5)  # üretimler arası bekleme
                                _send_msg("✅ %d/%d içerik kuyruğa eklendi, sırayla yayınlanacak." % (c - basarisiz, c))
                            threading.Thread(target=_gen_multi, args=(count,), daemon=True).start()
                        else:
                            _send_msg("❌ 1 ile 20 arasında bir sayı girin.")
                    else:
                        _awaiting_count = False
                        _send_msg("❌ Geçersiz sayı, iptal edildi.")
                    continue

                # Komutlar
                if tlow == "/start":
                    _send_msg(
                        "🧠 Felsefemiz Bot aktif!\n\n"
                        "/yeni — Hemen içerik üret ve yayınla\n"
                        "/durum — Bot durumu\n\n"
                        "İçerikler otomatik olarak yayınlanır.\n"
                        "Her içeriğin altında 🗑 Sil butonu bulunur."
                    )
                elif tlow == "/yeni":
                    _send_msg("⏳ Yeni içerik hazırlanıyor, lütfen bekleyin...")
                    threading.Thread(target=_process_single_generation, daemon=True).start()
                elif tlow == "/durum":
                    import __main__ as bot
                    posted_file = Path("posted.json")
                    count = 0
                    if posted_file.exists():
                        try:
                            count = len(json.loads(posted_file.read_text(encoding="utf-8")))
                        except Exception:
                            pass
                    q_size = bot._publish_queue.qsize()
                    _send_msg(
                        "✅ Bot çalışıyor!\n"
                        "📊 Toplam yayınlanan: %d\n"
                        "⏳ Kuyrukta bekleyen: %d" % (count, q_size)
                    )

        except Exception as e:
            log.warning("Polling hatasi: %s" % e)
            time.sleep(5)


def start_listener():
    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    log.info("Telegram listener basladi.")
