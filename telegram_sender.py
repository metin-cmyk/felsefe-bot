import os, json, logging, threading, requests
from pathlib import Path

log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_approve_callback = None
_pending = {}
_last_offset = 0

def set_approve_callback(fn):
    global _approve_callback
    _approve_callback = fn

def send_for_approval(post_img, story_img, quote_data, on_approve):
    key = "quote_%d" % int(__import__("time").time())
    _pending[key] = (quote_data, post_img, story_img, on_approve)

    # Post gorseli gonder
    with open(post_img, "rb") as f:
        requests.post(
            "https://api.telegram.org/bot%s/sendPhoto" % TELEGRAM_TOKEN,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": "POST GORSELI"},
            files={"photo": f},
            timeout=30,
        )

    # Story gorseli gonder
    with open(story_img, "rb") as f:
        requests.post(
            "https://api.telegram.org/bot%s/sendPhoto" % TELEGRAM_TOKEN,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": "STORY GORSELI"},
            files={"photo": f},
            timeout=30,
        )

    # Metin + butonlar
    hashtags = quote_data.get("hashtags", "#Felsefe #Bilgelik")
    twitter_text = quote_data.get("twitter") or quote_data["quote"]

    # Tek blok — kopyalayip direkt yapistir
    preview = twitter_text[:280]

    keyboard = {
        "inline_keyboard": [[
            {"text": "Yayinla", "callback_data": "yes_%s" % key},
            {"text": "Atla",    "callback_data": "no_%s"  % key},
            {"text": "Yenile",  "callback_data": "new_%s" % key},
        ]]
    }

    requests.post(
        "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
        json={
            "chat_id":      TELEGRAM_CHAT_ID,
            "text":         preview,
            "reply_markup": keyboard,
        },
        timeout=15,
    )
    log.info("Onay icin Telegram'a gonderildi.")

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

                    if data.startswith("yes_"):
                        key = data[4:]
                        if key in _pending:
                            qd, pi, si, fn = _pending.pop(key)
                            _send_msg("Yayinlaniyor...")
                            threading.Thread(target=fn, daemon=True).start()

                    elif data.startswith("no_"):
                        key = data[3:]
                        _pending.pop(key, None)
                        _send_msg("Atlandi.")

                    elif data.startswith("new_"):
                        key = data[4:]
                        _pending.pop(key, None)
                        _send_msg("Yeni icerik uretiliyor...")
                        def _regen():
                            qd = generate_quote()
                            pi, pal = create_post_image(qd)
                            si = create_story_image(qd, pal)
                            from bot import _publish
                            send_for_approval(pi, si, qd, lambda: _publish(qd, pi, si))
                        threading.Thread(target=_regen, daemon=True).start()

                # Komutlar
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()

                if text == "/start":
                    _send_msg(
                        "FelsefeCo Bot aktif!\n\n"
                        "Komutlar:\n"
                        "/yeni - hemen yeni icerik uret\n"
                        "/durum - bot durumu"
                    )
                elif text == "/yeni":
                    _send_msg("Yeni icerik uretiliyor...")
                    def _gen():
                        qd = generate_quote()
                        pi, pal = create_post_image(qd)
                        si = create_story_image(qd, pal)
                        from bot import _publish
                        send_for_approval(pi, si, qd, lambda: _publish(qd, pi, si))
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
