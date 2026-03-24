import os, re, random, anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

AKIMLAR = [
    "Stoacilik",
    "Budizm",
    "Taoizm",
    "Varoluşculuk",
    "Genel bilgelik",
    "Modern psikoloji",
]

FILOZOFLAR = {
    "Stoacilik": ["Marcus Aurelius", "Epiktetos", "Seneca", "Zeno"],
    "Budizm": ["Buda", "Thich Nhat Hanh", "Dalai Lama"],
    "Taoizm": ["Laozi", "Zhuangzi"],
    "Varoluşculuk": ["Albert Camus", "Friedrich Nietzsche", "Jean-Paul Sartre", "Simone de Beauvoir"],
    "Genel bilgelik": ["Sokrates", "Aristo", "Platon", "Konfucyus"],
    "Modern psikoloji": ["Carl Jung", "Viktor Frankl", "Erich Fromm"],
}

KONULAR = [
    "hayatın anlamı", "özgürlük", "mutluluk", "acı ve büyüme",
    "sabır ve direniş", "an'da yaşamak", "iç huzur", "cesaret",
    "değişim ve dönüşüm", "benlik", "sevgi", "ölüm ve ölümsüzlük",
    "bilgelik", "doğa ile uyum", "ego ve özbenlik",
]

def generate_quote() -> dict:
    akim    = random.choice(AKIMLAR)
    filozoflar = FILOZOFLAR[akim]
    filozof = random.choice(filozoflar)
    konu    = random.choice(KONULAR)

    system = """Sen derin bir felsefe bilgisine sahip Türkçe içerik üreticisisin.
Felsefi sözler üretiyorsun — kısa, güçlü, düşündürücü.

ÖNEMLI KURALLAR:
- SOZ alanında kesinlikle tirnak isareti (\" veya \u201c veya ') KULLANMA. Sözü düz yaz.
- TWITTER alaninda da sözü tirnaksiz yaz.
- Hashtag'leri her zaman # ile baslat, Türkçe karakter kullanma (ö->o, ü->u, s->s, ç->c, i->i, g->g).

Yanitini TAM OLARAK su formatta ver:

SOZ:
[Türkçe felsefi söz — 1-2 cümle, max 200 karakter, TIRNAK KULLANMA]
---
YAZAR:
[Filozofun adi]
---
AKIM:
[Felsefi akim]
---
TWITTER:
[Ayni sözün Twitter versiyonu — max 200 karakter, TIRNAK KULLANMA]
---
HASHTAG:
[5 adet hashtag — #Felsefe ve #Bilgelik zorunlu, konuyla ilgili 3 tane daha ekle]
---
ACIKLAMA:
[Sözün kisa Türkçe aciklamasi — 1 cümle, Instagram caption için]"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=system,
        messages=[{
            "role": "user",
            "content": "%s felsefesinden %s'nin %s hakkinda derin bir soz uret." % (akim, filozof, konu)
        }]
    )

    return _parse(msg.content[0].text.strip(), filozof, akim)

def _clean_quotes(text):
    """Basta ve sonda tirnak isaretlerini temizle."""
    text = text.strip()
    # Çeşitli tırnak karakterlerini temizle
    for q in ['\u201c', '\u201d', '\u2018', '\u2019', '"', "'"]:
        if text.startswith(q):
            text = text[1:]
        if text.endswith(q):
            text = text[:-1]
    return text.strip()

def _parse(text, default_autor, default_akim):
    def get(key):
        pattern = r"%s:\n(.*?)(?:\n---|\Z)" % key
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    quote = _clean_quotes(get("SOZ"))

    # Twitter metnini de tırnaksız yap, sonuna hashtag ekle
    twitter_raw = _clean_quotes(get("TWITTER"))
    hashtags    = get("HASHTAG") or "#Felsefe #Bilgelik"

    # Twitter metni yoksa quote'tan oluştur
    if not twitter_raw:
        twitter_raw = quote[:180]

    twitter = "%s\n\n— %s\n\n%s" % (twitter_raw, get("YAZAR") or default_autor, hashtags)

    return {
        "quote":    quote,
        "author":   get("YAZAR") or default_autor,
        "akim":     get("AKIM") or default_akim,
        "twitter":  twitter,
        "hashtags": hashtags,
        "aciklama": get("ACIKLAMA"),
    }
