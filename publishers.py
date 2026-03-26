# -*- coding: utf-8 -*-
import os, logging, requests, re, time
from pathlib import Path
from urllib.parse import quote as urlquote
from image_generator import create_square_cover

import anthropic
from google import genai

log = logging.getLogger(__name__)

WP_URL      = os.environ.get("WP_URL",      "https://felsefemiz.net")
WP_USER     = os.environ.get("WP_USER",     "serezart")
WP_APP_PASS = os.environ.get("WP_APP_PASS", "")

# ---------------------------------------------------------------------------
# AI İstemcilerini Başlat (Claude + Gemini Ortak Akıl)
# ---------------------------------------------------------------------------
try:
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
except Exception as e:
    claude_client = None
    log.warning("Claude istemcisi baslatilamadi: %s" % e)

try:
    gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    gemini_client = None
    log.warning("Gemini istemcisi baslatilamadi: %s" % e)


def _ai_generate(prompt, max_tokens=800):
    """Önce Claude'u dener, hata verirse (kredi vb.) Gemini'ye geçer."""
    # 1. Claude'u Dene
    if claude_client:
        try:
            msg = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            log.warning("Claude API hatasi (Gemini'ye geciliyor...): %s" % e)
            
    # 2. Gemini'yi Dene (Yeni GenAI SDK)
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            log.error("Gemini API hatasi: %s" % e)
            
    # 3. İkisi de çökerse
    return ""

# ---------------------------------------------------------------------------
# Yardımcı: WordPress Görsel Yükleme
# ---------------------------------------------------------------------------
def _upload_image(image_path, alt_text="", title="", caption="", description=""):
    if not image_path or not Path(image_path).exists(): return None
    try:
        with open(image_path, "rb") as f:
            img_data = f.read()
        filename = Path(image_path).name
        r = requests.post(
            "%s/wp-json/wp/v2/media" % WP_URL,
            auth=(WP_USER, WP_APP_PASS),
            headers={"Content-Disposition": "attachment; filename=%s" % filename, "Content-Type": "image/jpeg"},
            data=img_data, timeout=90
        )
        if r.status_code not in (200, 201): return None
        media_id = r.json()["id"]
        meta = {}
        if alt_text: meta["alt_text"] = alt_text
        if title: meta["title"] = title
        if caption: meta["caption"] = caption
        if description: meta["description"] = description
        if meta:
            requests.post("%s/wp-json/wp/v2/media/%s" % (WP_URL, media_id), auth=(WP_USER, WP_APP_PASS), json=meta, timeout=15)
        time.sleep(0.5)
        return media_id
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Filozof, Kategori ve Etiket İşlemleri
# ---------------------------------------------------------------------------
def _fetch_wikipedia(name):
    for lang in ("tr", "en"):
        try:
            r = requests.get("https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (lang, urlquote(name)), timeout=10)
            if r.status_code == 200:
                data = r.json()
                extract = data.get("extract", "")
                desc = data.get("description", "")
                if len(extract) > 80:
                    full = ("%s\n%s" % (desc, extract)) if desc else extract
                    return full[:3000], lang
        except Exception:
            pass
    return "", "tr"

def _extract_dates(text):
    if not text: return "Bilinmiyor"
    m = re.search(r"(\d{3,4})\s*[-\u2013]\s*(\d{3,4})", text[:500])
    if m: return "%s \u2013 %s" % (m.group(1), m.group(2))
    return "Bilinmiyor"

def _build_bio(name, wiki_raw, wiki_lang):
    prompt = (
        "%s hakkında Wikipedia özetini referans alarak Türkçe, akıcı, özgün 3 paragraf "
        "biyografi yaz. Kopyalama, kendi cümlelerinle anlat. Felsefi görüşlerini vurgula.\n\n"
        "Wikipedia referansı:\n%s\n\nSadece biyografi yaz."
    ) % (name, wiki_raw[:1500] or "Bilgi bulunamadı.")
    bio = _ai_generate(prompt, max_tokens=1000)
    return bio or wiki_raw[:600]

def _ensure_filozof(name, wiki_raw, wiki_lang):
    try:
        r = requests.get("%s/wp-json/wp/v2/filozof" % WP_URL, auth=(WP_USER, WP_APP_PASS), params={"search": name, "per_page": 10}, timeout=15)
        if r.status_code == 200:
            for term in r.json():
                if term["name"].lower() == name.lower():
                    return term["id"]
    except Exception:
        pass
    
    bio = _build_bio(name, wiki_raw, wiki_lang)
    cover_path = create_square_cover(name)
    cover_id = _upload_image(cover_path, alt_text=name, title=name) if cover_path else ""
    payload = {"name": name, "description": bio, "acf": {"kisa_biyografi": bio, "yasam_tarihleri": _extract_dates(wiki_raw), "filozof_kapak_resmi": cover_id}}
    
    try:
        r = requests.post("%s/wp-json/wp/v2/filozof" % WP_URL, auth=(WP_USER, WP_APP_PASS), json=payload, timeout=30)
        if r.status_code in (200, 201): return r.json()["id"]
    except Exception:
        pass
    return None

def _ensure_category(akim):
    try:
        r = requests.get("%s/wp-json/wp/v2/categories" % WP_URL, auth=(WP_USER, WP_APP_PASS), params={"search": akim}, timeout=15)
        if r.status_code == 200:
            for t in r.json():
                if t["name"].lower() == akim.lower(): return t["id"]
    except Exception:
        pass
    wiki_raw, _ = _fetch_wikipedia(akim)
    desc = _ai_generate("'%s' felsefi akımı hakkında 2 paragraf Türkçe açıklama yaz.\nWiki:\n%s" % (akim, wiki_raw[:1000]), max_tokens=600) or ""
    try:
        r2 = requests.post("%s/wp-json/wp/v2/categories" % WP_URL, auth=(WP_USER, WP_APP_PASS), json={"name": akim, "description": desc}, timeout=15)
        if r2.status_code in (200, 201): return r2.json()["id"]
    except Exception:
        pass
    return None

def _get_or_create_tag(name):
    try:
        r = requests.get("%s/wp-json/wp/v2/tags" % WP_URL, auth=(WP_USER, WP_APP_PASS), params={"search": name}, timeout=10)
        if r.status_code == 200:
            for t in r.json():
                if t["name"].lower() == name.lower(): return t["id"]
        r2 = requests.post("%s/wp-json/wp/v2/tags" % WP_URL, auth=(WP_USER, WP_APP_PASS), json={"name": name}, timeout=10)
        if r2.status_code in (200, 201): return r2.json()["id"]
    except Exception:
        pass
    return None

def _prepare_tags(quote_data):
    raw, akim, yazar = quote_data.get("hashtags", ""), quote_data.get("akim", ""), quote_data.get("author", "")
    tags = list(re.findall(r"#(\w+)", raw))
    for extra in [akim, yazar, "Felsefe", "Bilgelik", "DusunenInsan"]:
        if extra and extra not in tags: tags.append(extra)
    return [_get_or_create_tag(tag) for tag in tags[:8] if _get_or_create_tag(tag)]

# ---------------------------------------------------------------------------
# İçerik Oluşturma Formatları
# ---------------------------------------------------------------------------
def _build_title(quote_data):
    soz = quote_data.get("quote", "").strip()
    if len(soz) > 80:
        t = soz[:80]
        ls = t.rfind(" ")
        return (t[:ls] if ls > 50 else t).rstrip(",.;:") + "..."
    return soz.rstrip(",.;:")

def _build_content(quote_data):
    soz = quote_data.get("quote", "")
    yazar = quote_data.get("author", "Anonim")
    akim = quote_data.get("akim", "Felsefe")
    hashtags = quote_data.get("hashtags", "")
    
    html_content = (
        f'<blockquote class="wp-block-quote"><p><em>"{soz}"</em></p>'
        f'<cite>— {yazar} | {akim}</cite></blockquote>\n\n'
        f'<p class="felsefemiz-tags">{hashtags}</p>'
    )
    return html_content

def _build_aciklama(quote_data):
    soz, yazar, akim = quote_data.get("quote", ""), quote_data.get("author", "Anonim"), quote_data.get("akim", "Felsefe")
    prompt = (
        f"Sen derinlikli yazılar yazan bir felsefe editörüsün. Şu felsefi sözü son derece detaylı bir şekilde analiz et.\n\n"
        f"Söz: '{soz}'\nYazar: {yazar}\nAkım: {akim}\n\n"
        f"GÖREVİN: Bu sözün altında yatan felsefi derinliği, yazarın genel düşünce sistemi içindeki yerini ve günümüz dünyasındaki varoluşsal karşılığını incele. "
        f"Okuyucuyu düşünmeye sevk eden, edebi bir dille yazılmış, EN AZ 3-4 UZUN PARAGRAFTAN oluşan çok kapsamlı bir makale oluştur. "
        f"Kısa cevaplar verme; adeta bir felsefe dergisine başyazı hazırlıyormuşsun gibi derinlikli yaz."
    )
    editor = _ai_generate(prompt, max_tokens=1200)
    return editor or quote_data.get("aciklama", f"{akim} felsefesinin bu sözü, modern insanın varoluşsal sorularına ışık tutmaktadır.")

# ---------------------------------------------------------------------------
# WordPress Yükleme ve Silme
# ---------------------------------------------------------------------------
def post_to_wordpress(quote_data, post_img):
    if not WP_APP_PASS: return None, None, None
    yazar, akim, soz = quote_data.get("author", "Anonim"), quote_data.get("akim", "Felsefe"), quote_data.get("quote", "")

    wiki_raw, wiki_lang = _fetch_wikipedia(yazar)
    filozof_id = _ensure_filozof(yazar, wiki_raw, wiki_lang)
    cat_id = _ensure_category(akim)
    tag_ids = _prepare_tags(quote_data)

    media_id = _upload_image(post_img, alt_text="%s — %s" % (soz[:80], yazar), title="%s sözü" % yazar)
    
    post_data = {
        "title": _build_title(quote_data),
        "content": _build_content(quote_data),
        "excerpt": soz[:160],
        "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "filozof": [filozof_id] if filozof_id else [],
        "acf": {
            "felsefi_soz": soz,
            "yazar": yazar,
            "felsefi_akim": akim,
            "aciklama": _build_aciklama(quote_data),
            "twitter_text": quote_data.get("twitter", ""),
        },
    }
    if media_id: post_data["featured_media"] = media_id

    try:
        r = requests.post("%s/wp-json/wp/v2/posts" % WP_URL, auth=(WP_USER, WP_APP_PASS), json=post_data, timeout=45)
        if r.status_code in (200, 201):
            resp = r.json()
            return resp.get("link", ""), resp.get("id"), media_id
    except Exception:
        pass
    return None, None, media_id

def delete_from_wordpress(post_id, media_id=None):
    deleted = []
    if post_id:
        try:
            r = requests.delete(
                "%s/wp-json/wp/v2/posts/%s" % (WP_URL, post_id),
                auth=(WP_USER, WP_APP_PASS),
                params={"force": True},
                timeout=15,
            )
            if r.status_code in (200, 201):
                log.info("WP post silindi: %s" % post_id)
                deleted.append("post:%s" % post_id)
        except Exception as e:
            log.error("Post silme hatasi: %s" % e)
            
    if media_id and media_id != 'None':
        try:
            r = requests.delete(
                "%s/wp-json/wp/v2/media/%s" % (WP_URL, media_id),
                auth=(WP_USER, WP_APP_PASS),
                params={"force": True},
                timeout=15,
            )
            if r.status_code in (200, 201):
                log.info("WP media silindi: %s" % media_id)
                deleted.append("media:%s" % media_id)
        except Exception as e:
            log.error("Media silme hatasi: %s" % e)
            
    return deleted
