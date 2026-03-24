import requests
import base64
import os

# --- YAPILANDIRMA ---
WP_URL = "https://felsefemiz.net/wp-json/wp/v2/posts"
WP_USER = "serezart"
WP_APP_PASS = "TBTJ w0hn 9Pz7 FyIa A6py xj6O"

def send_to_wordpress(title, content):
    """İçeriği WordPress sitesine yükler."""
    # Kimlik doğrulaması için Base64 hazırlığı
    credentials = f"{WP_USER}:{WP_APP_PASS}"
    token = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        'title': title,
        'content': content,
        'status': 'publish' # Direkt yayınla. Onay beklesin istersen 'draft' yap.
    }

    try:
        response = requests.post(WP_URL, json=payload, headers=headers)
        if response.status_code == 201:
            return True, "Siteye başarıyla yüklendi!"
        else:
            return False, f"Hata Kodu: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Bağlantı hatası: {str(e)}"

def send_to_telegram(bot, chat_id, text):
    """İçeriği Telegram'a gönderir."""
    try:
        bot.send_message(chat_id, text)
        return True
    except Exception as e:
        print(f"Telegram hatası: {e}")
        return False
