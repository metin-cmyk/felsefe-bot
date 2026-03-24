import os, re, random, anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

AKIMLAR = [
    "Stoacilik",
    "Budizm",
    "Taoizm",
    "Varoluşculuk",
    "Nihilizm",
    "Pragmatizm",
    "Epikurizm",
    "Skeptisizm",
    "Fenomenoloji",
    "Anarşizm",
    "Transandantalizm",
    "Sufizm",
    "Konfucyanism",
    "Genel bilgelik",
    "Modern psikoloji",
    "Feminist felsefe",
    "Doğu felsefesi",
]

FILOZOFLAR = {
    "Stoacilik":          ["Marcus Aurelius", "Epiktetos", "Seneca", "Zeno", "Kleantes", "Chrysippos"],
    "Budizm":             ["Buda", "Thich Nhat Hanh", "Dalai Lama", "Nagarjuna", "Shunryu Suzuki"],
    "Taoizm":             ["Laozi", "Zhuangzi", "Liezi"],
    "Varoluşculuk":       ["Albert Camus", "Friedrich Nietzsche", "Jean-Paul Sartre", "Simone de Beauvoir", "Søren Kierkegaard", "Martin Heidegger", "Karl Jaspers"],
    "Nihilizm":           ["Friedrich Nietzsche", "Emil Cioran", "Arthur Schopenhauer"],
    "Pragmatizm":         ["William James", "John Dewey", "Charles Sanders Peirce", "Richard Rorty"],
    "Epikurizm":          ["Epikuros", "Lucretius", "Philodemus"],
    "Skeptisizm":         ["Montaigne", "David Hume", "Pyrrho"],
    "Fenomenoloji":       ["Edmund Husserl", "Maurice Merleau-Ponty", "Simone de Beauvoir"],
    "Anarşizm":           ["Peter Kropotkin", "Emma Goldman", "Mikhail Bakunin"],
    "Transandantalizm":   ["Ralph Waldo Emerson", "Henry David Thoreau"],
    "Sufizm":             ["Rumi", "Hafız", "Ibn Arabi", "Yunus Emre", "Hacı Bektaş Veli"],
    "Konfucyanism":       ["Konfucyus", "Mozi", "Mengzi", "Xunzi"],
    "Genel bilgelik":     ["Sokrates", "Aristo", "Platon", "Herakleitos", "Demokritos", "Pythagoras", "Diogenes", "Parmenides"],
    "Modern psikoloji":   ["Carl Jung", "Viktor Frankl", "Erich Fromm", "Abraham Maslow", "Alfred Adler", "Karen Horney"],
    "Feminist felsefe":   ["Simone de Beauvoir", "bell hooks", "Hannah Arendt", "Mary Wollstonecraft", "Judith Butler"],
    "Doğu felsefesi":     ["Rabindranath Tagore", "Swami Vivekananda", "Jiddu Krishnamurti", "Alan Watts", "D.T. Suzuki"],
}

KONULAR = [
    # Varoluş & Anlam
    "hayatın anlamı", "varoluşun saçmalığı", "ölüm karşısında yaşamak",
    "anlamsızlıkla yüzleşmek", "ölümsüzlük arzusu", "zamanın akışı",
    "şimdiki an", "geçmişin ağırlığı", "geleceğin belirsizliği",

    # Benlik & Kimlik
    "benlik", "kimlik", "ego ve özbenlik", "özgün olmak",
    "maskelerin ardındaki gerçek yüz", "içimizdeki yabancı",
    "kendinle barışmak", "kendini tanımak", "dönüşüm ve yeniden doğuş",

    # Duygu & Deneyim
    "acı ve büyüme", "yalnızlık", "sessizlik", "özlem",
    "aşk ve bağlılık", "kıskançlık ve özgürlük", "kayıp ve yas",
    "hayal kırıklığı", "öfke ve dönüşüm", "utanç ve onur",
    "kırgınlık ve affetmek", "minnet ve şükran", "sevinç ve hafiflik",

    # İlişkiler & Toplum
    "dostluk", "sevgi", "yabancılaşma", "toplum ve birey",
    "aile ve bağlar", "güven ve ihanet", "empati ve merhamet",
    "yalnız kalabalıklar", "dijital çağda insan olmak",
    "sosyal medya ve kimlik", "modern insanın kaygıları",

    # Özgürlük & Güç
    "özgürlük", "direniş", "güç ve iktidar", "boyun eğmek ya da isyan",
    "vicdan", "adalet", "eşitsizlik", "cesaret", "sorumluluk",
    "baskı altında var olmak", "sistemin içinde kaybolmak",

    # Zihin & Bilgi
    "bilinç", "sezgi", "merak", "öğrenmek ve unutmak",
    "dil ve anlam", "gerçek ve yanılsama", "bilgi ve cehalet",
    "şüphe etmenin gücü", "akıl ve duygu", "rüyalar ve bilinçdışı",

    # Doğa & Evren
    "doğa ile uyum", "evrenin sessizliği", "chaos ve düzen",
    "döngüler ve yenilenme", "ölüm ve doğa", "bütünle bağlantı",

    # Başarı & Emek
    "emek ve anlam", "yaratıcılık", "başarı ve boşluk",
    "hırs ve tatmin", "mükemmeliyetçilik", "bırakmayı öğrenmek",
    "sabır", "alçakgönüllülük", "sadelik",

    # Ruh & Maneviyat
    "iç huzur", "aydınlanma", "sessiz bilgelik", "dua ve teslimiyet",
    "spiritüel uyanış", "nefes ve an", "boşlukta var olmak",
    "tanrı ve insan", "inanç ve şüphe",

    # Viral & İlgi Çeken
    "toxic ilişkilerden kurtulmak", "sınır koymayı öğrenmek",
    "hayır diyebilmek", "başkalarının onayına ihtiyaç duymamak",
    "kendi hikayenin kahramanı olmak", "geçmişi bırakmak ve ilerlemek",
    "karşılaştırma tuzağından çıkmak", "kendi hızında ilerlемek",
    "sessizliğin gücü", "yavaşlamanın erdemi",
    "teknoloji ve insanlık", "yapay zeka çağında anlam",
    "tüketim toplumunda mutluluk", "para ve mutluluk",
    "başarı mı mutluluk mu", "özgürlük mü güvenlik mi",
]

def generate_quote() -> dict:
    akim      = random.choice(AKIMLAR)
    filozof   = random.choice(FILOZOFLAR[akim])
    konu      = random.choice(KONULAR)

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
            "content": "%s felsefesinden %s'nin %s hakkinda derin bir söz üret." % (akim, filozof, konu)
        }]
    )

    return _parse(msg.content[0].text.strip(), filozof, akim)

def _clean_quotes(text):
    text = text.strip()
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

    quote    = _clean_quotes(get("SOZ"))
    author   = get("YAZAR") or default_autor
    hashtags = get("HASHTAG") or "#Felsefe #Bilgelik"

    twitter_raw = _clean_quotes(get("TWITTER")) or quote[:200]
    twitter = "%s\n\n— %s\n\n%s" % (twitter_raw, author, hashtags)

    return {
        "quote":    quote,
        "author":   author,
        "akim":     get("AKIM") or default_akim,
        "twitter":  twitter,
        "hashtags": hashtags,
        "aciklama": get("ACIKLAMA"),
    }
