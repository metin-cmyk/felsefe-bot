import os, json, logging, threading, requests, time
from urllib.parse import quote as url_quote
from pathlib import Path

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_last_offset  = 0
_pending      = {}          # key -> (quote_data, post_img, story_img, msg_ids)
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

def _edit_msg(message_id, text, reply_markup=None):
    """Mevcut mesajı güncelle (butonları değiştir veya metni değiştir)."""
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "text":       text,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(
        "https://api.telegram.org/bot%s/editMessageText" % TELEGRAM_TOKEN,
        json=payload,
        timeout=10,
    )

def _delete_msg(message_id):
    """Telegram'dan mesajı sil."""
    requests.post(
        "https://api.telegram.org/bot%s/deleteMessage" % TELEGRAM_TOKEN,
        data={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id},
        timeout=10,
    )

def _edit_reply_markup(message_id, reply_markup):
    """Sadece butonları güncelle (inline keyboard)."""
    requests.post(
        "https://api.telegram.org/bot%s/editMessageReplyMarkup" % TELEGRAM_TOKEN,
        json={
            "chat_id":      TELEGRAM_CHAT_ID,
            "message_id":   message_id,
            "reply_markup": reply_markup,
        },
        timeout=10,
    )

# ---------------------------------------------------------------------------
# Onay mesajı gönder
# ---------------------------------------------------------------------------

def send_for_approval(post_img, story_img, quote_data):
    """
    Görselleri ve önizleme metnini Telegram'a gönderir.
    ✅ Onayla  |  🗑 Sil / Atla  |  🔄 Yeni Üret  |  🔢 Toplu Üret
    Onay gelmeden WordPress'e hiçbir şey gönderilmez.
    """
    key = "q_%d" % int(time.time())
    msg_ids = []

    # Görselleri gönder (post + story)
    try:
        with open(post_img, "rb") as pf, open(story_img, "rb") as sf:
            r = requests.post(
                "https://api.telegram.org/bot%s/sendMediaGroup" % TELEGRAM_TOKEN,
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={
                    "media": (None, '[{"type":"photo","media":"attach://post","caption":"📐 POST (1080x1350)"},{"type":"photo","media":"attach://story","caption":"📱 STORY (1080x1920)"}]'),
                    "post":  ("post.jpg",  pf, "image/jpeg"),
                    "story": ("story.jpg", sf, "image/jpeg"),
                },
                timeout=30,
            )
            result = r.json().get("result", [])
            for m in result:
                msg_ids.append(m.get("message_id"))
    except Exception as e:
        log.error("Gorsel gonderilemedi: %s" % e)

    # Önizleme metni
    twitter_text = quote_data.get("twitter") or quote_data["quote"]
    hashtags     = quote_data.get("hashtags", "")
    preview      = twitter_text[:280]
    if hashtags:
        preview += "\n\n" + hashtags

    # Butonlar
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Onayla ve Yayınla", "callback_data": "approve_%s" % key},
                {"text": "🗑 Sil / Atla",        "callback_data": "delete_%s"  % key},
            ],
            [
                {"text": "🔄 Yeni İçerik Üret",  "callback_data": "new_%s"     % key},
                {"text": "🔢 Toplu Üret",         "callback_data": "multi_%s"   % key},
            ],
        ]
    }

    r2 = requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        json={
            "chat_id":      TELEGRAM_CHAT_ID,
            "text":         preview,
            "reply_markup": keyboard,
        },
        timeout=15,
    )
    btn_msg_id = r2.json().get("result", {}).get("message_id")
    if btn_msg_id:
        msg_ids.append(btn_msg_id)

    # Pending'e kaydet
    _pending[key] = (quote_data, post_img, story_img, msg_ids, btn_msg_id)
    log.info("Onay bekleniyor: %s (msg_ids=%s)" % (key, msg_ids))

# ---------------------------------------------------------------------------
# Onay işlemi
# ---------------------------------------------------------------------------

def _do_approve(key, cb_id):
    """Onay butonuna basıldığında WordPress'e yayınlar."""
    requests.post(
        "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
        data={"callback_query_id": cb_id, "text": "Yayınlanıyor..."},
        timeout=10,
    )

    if key not in _pending:
        _send_msg("⚠️ Bu içerik artık geçerli değil.")
        return

    quote_data, post_img, story_img, msg_ids, btn_msg_id = _pending.pop(key)

    # Butonu "Onaylandı!" olarak güncelle, diğer butonları kaldır
    if btn_msg_id:
        _edit_reply_markup(btn_msg_id, {"inline_keyboard": [[
            {"text": "✅ Onaylandı!", "callback_data": "done"}
        ]]})

    # WordPress'e yayınla
    def _publish():
        from bot import publish_approved
        wp_url = publish_approved(quote_data, post_img)
        if wp_url:
            _send_msg("🌐 Yayınlandı: %s" % wp_url)
        else:
            _send_msg("❌ WordPress'e yüklenemedi, loglara bakın.")

    threading.Thread(target=_publish, daemon=True).start()

# ---------------------------------------------------------------------------
# Sil / Atla işlemi
# ---------------------------------------------------------------------------

def _do_delete(key, cb_id):
    """Sil butonuna basıldığında tüm mesajları siler."""
    requests.post(
        "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
        data={"callback_query_id": cb_id, "text": "Silindi."},
        timeout=10,
    )

    if key in _pending:
        _, _, _, msg_ids, _ = _pending.pop(key)
        for mid in msg_ids:
            try:
                _delete_msg(mid)
            except Exception as e:
                log.warning("Mesaj silinemedi %s: %s" % (mid, e))
    log.info("Icerik silindi: %s" % key)

# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

def _process_single_generation():
    from quote_generator import generate_quote
    from image_generator import create_post_image, create_story_image
    qd = generate_quote()
    if qd is None:
        _send_msg("⚠️ Wikiquote'tan gerçek söz bulunamadı. Lütfen /yeni ile tekrar deneyin.")
        return
    pi, pal = create_post_image(qd)
    si = create_story_image(qd, pal)
    send_for_approval(pi, si, qd)

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

                # Buton tıklaması
                cb = update.get("callback_query", {})
                if cb:
                    cb_id = cb["id"]
                    data  = cb.get("data", "")

                    if data.startswith("approve_"):
                        key = data[8:]
                        _do_approve(key, cb_id)

                    elif data.startswith("delete_"):
                        key = data[7:]
                        _do_delete(key, cb_id)

                    elif data.startswith("new_"):
                        key = data[4:]
                        _pending.pop(key, None)
                        requests.post(
                            "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
                            data={"callback_query_id": cb_id},
                            timeout=10,
                        )
                        _send_msg("🔄 Yeni içerik üretiliyor...")
                        threading.Thread(target=_process_single_generation, daemon=True).start()

                    elif data.startswith("multi_"):
                        requests.post(
                            "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
                            data={"callback_query_id": cb_id},
                            timeout=10,
                        )
                        _awaiting_count = True
                        _send_msg("🔢 Kaç adet üreteyim? (1-20 arası bir sayı yaz)")

                    else:
                        # "done" gibi geçersiz callback'leri sessizce yakala
                        requests.post(
                            "https://api.telegram.org/bot%s/answerCallbackQuery" % TELEGRAM_TOKEN,
                            data={"callback_query_id": cb_id},
                            timeout=10,
                        )

                # Metin komutları
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
                            _send_msg("⏳ %d içerik üretiliyor, her biri için onayınızı bekliyorum..." % count)
                            def _gen_multi(c):
                                for i in range(c):
                                    _send_msg("🔄 Üretiliyor: %d / %d" % (i+1, c))
                                    _process_single_generation()
                                    if i < c - 1:
                                        time.sleep(5)
                                _send_msg("✅ Toplu üretim tamamlandı!")
                            threading.Thread(target=_gen_multi, args=(count,), daemon=True).start()
                        else:
                            _send_msg("❌ 1 ile 20 arasında bir sayı girin.")
                    else:
                        _awaiting_count = False
                        _send_msg("❌ Geçersiz sayı, iptal edildi.")
                    continue

                if tlow == "/start":
                    _send_msg(
                        "Felsefemiz Bot aktif! 🧠\n\n"
                        "/yeni — Hemen içerik üret\n"
                        "/durum — Bot durumu"
                    )
                elif tlow == "/yeni":
                    _send_msg("🔄 Yeni içerik üretiliyor...")
                    threading.Thread(target=_process_single_generation, daemon=True).start()
                elif tlow == "/durum":
                    posted_file = Path("posted.json")
                    count = len(json.loads(posted_file.read_text())) if posted_file.exists() else 0
                    _send_msg("✅ Bot çalışıyor!\nToplam yayınlanan: %d\nZamanlama: her saat başı" % count)

        except Exception as e:
            log.warning("Polling hatasi: %s" % e)
            time.sleep(5)

def start_listener():
    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    log.info("Telegram listener basladi.")
