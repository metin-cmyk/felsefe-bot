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

Yanıtını TAM OLARAK şu formatta ver:

SOZ:
[Türkçe felsefi söz — 1-2 cümle, max 200 karakter]
---
YAZAR:
[Filozofun adı]
---
AKIM:
[Felsefi akım]
---
TWITTER:
[Aynı sözün Twitter versiyonu — max 240 karakter, hashtag ekle: #Felsefe #Bilgelik ve konuyla ilgili 1-2 hashtag]
---
ACIKLAMA:
[Sözün kısa Türkçe açıklaması — 1 cümle, Instagram caption için]"""

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

def _parse(text, default_autor, default_akim):
    def get(key):
        pattern = r"%s:\n(.*?)(?:\n---|\Z)" % key
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    return {
        "quote":      get("SOZ"),
        "author":     get("YAZAR") or default_autor,
        "akim":       get("AKIM") or default_akim,
        "twitter":    get("TWITTER"),
        "aciklama":   get("ACIKLAMA"),
    }
