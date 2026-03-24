import os, logging, requests, base64
from pathlib import Path

log = logging.getLogger(__name__)

WP_URL      = "https://felsefemiz.net"
WP_USER     = "serezart"
WP_APP_PASS = "TBTJ w0hn 9Pz7 FyIa A6py xj6O" # Şifreni buraya sabitledim

def post_to_wordpress(quote_data, image_path):
    """Senin orijinal publishers.py yapınla uyumlu WordPress gönderici."""
    try:
        # Önce görseli yükle (Media ID al)
        with open(image_path, "rb") as f:
            img_data = f.read()
        
        filename = Path(image_path).name
        media_r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            auth=(WP_USER, WP_APP_PASS),
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "image/jpeg",
            },
            data=img_data,
            timeout=60
        )
        media_id = media_r.json().get("id")

        # Sonra yazıyı paylaş
        payload = {
            "title": quote_data.get("quote", "Yeni Paylaşım")[:50],
            "content": f"{quote_data.get('quote')}\n\n— {quote_data.get('author')}\n\n#felsefe",
            "status": "publish",
            "featured_media": media_id
        }
        
        post_r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_APP_PASS),
            json=payload,
            timeout=60
        )
        if post_r.status_code == 201:
            return post_r.json().get("link")
    except Exception as e:
        log.error(f"WP Hatası: {e}")
    return None
