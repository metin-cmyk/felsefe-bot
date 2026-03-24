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
    "Hedonizm",
    "Rasyonalizm",
    "Empirizm",
    "İdealizm",
    "Materyalizm",
    "Absürdizm",
    "Hümanizm",
    "Aydınlanma felsefesi",
    "Marksizm",
    "Feminist felsefe",
    "Doğu felsefesi",
    "Modern psikoloji",
    "Analitik felsefe",
    "Postmodernizm",
    "Genel bilgelik",
]

FILOZOFLAR = {
    "Stoacilik": [
        "Marcus Aurelius", "Epiktetos", "Seneca", "Zeno",
        "Kleantes", "Chrysippos", "Cato", "Musonius Rufus",
    ],
    "Budizm": [
        "Buda", "Thich Nhat Hanh", "Dalai Lama", "Nagarjuna",
        "Shunryu Suzuki", "Pema Chödrön", "Ajahn Chah", "Bodhidharma",
    ],
    "Taoizm": [
        "Laozi", "Zhuangzi", "Liezi", "Wang Bi",
    ],
    "Varoluşculuk": [
        "Albert Camus", "Friedrich Nietzsche", "Jean-Paul Sartre",
        "Simone de Beauvoir", "Søren Kierkegaard", "Martin Heidegger",
        "Karl Jaspers", "Gabriel Marcel", "Fyodor Dostoyevski",
        "Franz Kafka", "Leo Tolstoy",
    ],
    "Nihilizm": [
        "Friedrich Nietzsche", "Emil Cioran", "Arthur Schopenhauer",
        "Philipp Mainländer",
    ],
    "Pragmatizm": [
        "William James", "John Dewey", "Charles Sanders Peirce",
        "Richard Rorty", "Oliver Wendell Holmes",
    ],
    "Epikurizm": [
        "Epikuros", "Lucretius", "Philodemus", "Metrodoros",
    ],
    "Skeptisizm": [
        "Montaigne", "David Hume", "Pyrrho", "Sextus Empiricus",
        "René Descartes",
    ],
    "Fenomenoloji": [
        "Edmund Husserl", "Maurice Merleau-Ponty", "Simone de Beauvoir",
        "Hannah Arendt", "Emmanuel Levinas",
    ],
    "Anarşizm": [
        "Peter Kropotkin", "Emma Goldman", "Mikhail Bakunin",
        "Leo Tolstoy", "Murray Bookchin",
    ],
    "Transandantalizm": [
        "Ralph Waldo Emerson", "Henry David Thoreau", "Walt Whitman",
        "Margaret Fuller",
    ],
    "Sufizm": [
        "Rumi", "Hafız", "Ibn Arabi", "Yunus Emre",
        "Hacı Bektaş Veli", "Şems-i Tebrizi", "Rabia el-Adeviyye",
        "Al-Ghazali", "Omar Hayyam",
    ],
    "Konfucyanism": [
        "Konfucyus", "Mengzi", "Xunzi", "Zhu Xi", "Wang Yangming",
    ],
    "Hedonizm": [
        "Aristippos", "Epikuros", "Jeremy Bentham", "John Stuart Mill",
    ],
    "Rasyonalizm": [
        "René Descartes", "Baruch Spinoza", "Gottfried Wilhelm Leibniz",
        "Immanuel Kant", "Georg Wilhelm Friedrich Hegel",
    ],
    "Empirizm": [
        "John Locke", "David Hume", "Francis Bacon",
        "George Berkeley", "John Stuart Mill",
    ],
    "İdealizm": [
        "Platon", "Georg Wilhelm Friedrich Hegel", "Immanuel Kant",
        "Johann Gottlieb Fichte", "Friedrich Schelling",
    ],
    "Materyalizm": [
        "Karl Marx", "Friedrich Engels", "Ludwig Feuerbach",
        "Thomas Hobbes", "Demokritos",
    ],
    "Absürdizm": [
        "Albert Camus", "Samuel Beckett", "Franz Kafka",
        "Eugène Ionesco",
    ],
    "Hümanizm": [
        "Erasmus", "Thomas More", "Giovanni Pico della Mirandola",
        "Michel de Montaigne", "Voltaire",
    ],
    "Aydınlanma felsefesi": [
        "Voltaire", "Jean-Jacques Rousseau", "Denis Diderot",
        "Immanuel Kant", "John Locke", "Baron de Montesquieu",
    ],
    "Marksizm": [
        "Karl Marx", "Friedrich Engels", "Antonio Gramsci",
        "Rosa Luxemburg", "Georg Lukács",
    ],
    "Feminist felsefe": [
        "Simone de Beauvoir", "bell hooks", "Hannah Arendt",
        "Mary Wollstonecraft", "Judith Butler", "Angela Davis",
        "Audre Lorde", "Gloria Anzaldúa",
    ],
    "Doğu felsefesi": [
        "Rabindranath Tagore", "Swami Vivekananda", "Jiddu Krishnamurti",
        "Alan Watts", "D.T. Suzuki", "Sri Aurobindo", "Osho",
        "Ramana Maharshi", "Krishnamurti",
    ],
    "Modern psikoloji": [
        "Carl Jung", "Viktor Frankl", "Erich Fromm", "Abraham Maslow",
        "Alfred Adler", "Karen Horney", "Rollo May", "James Hillman",
        "Irvin Yalom", "Erich Neumann",
    ],
    "Analitik felsefe": [
        "Bertrand Russell", "Ludwig Wittgenstein", "Karl Popper",
        "Gilbert Ryle", "A.J. Ayer",
    ],
    "Postmodernizm": [
        "Michel Foucault", "Jacques Derrida", "Jean-François Lyotard",
        "Jean Baudrillard", "Gilles Deleuze", "Zygmunt Bauman",
    ],
    "Genel bilgelik": [
        "Sokrates", "Aristo", "Platon", "Herakleitos",
        "Demokritos", "Pythagoras", "Diogenes", "Parmenides",
        "Tales", "Anaksimandros", "Empedokles",
        "Blaise Pascal", "Francis Bacon", "Baruch Spinoza",
        "Friedrich Schiller", "Arthur Schopenhauer",
        "Ralph Waldo Emerson", "Albert Einstein",
        "Bertrand Russell", "George Orwell",
    ],
}

KONULAR = [
    # Varoluş & Anlam
    "hayatın anlamı", "varoluşun saçmalığı", "ölüm karşısında yaşamak",
    "anlamsızlıkla yüzleşmek", "ölümsüzlük arzusu", "zamanın akışı",
    "şimdiki an", "geçmişin ağırlığı", "geleceğin belirsizliği",
    "neden varız", "varoluşun yükü", "hayatı anlamlandırmak",

    # Benlik & Kimlik
    "benlik", "kimlik", "ego ve özbenlik", "özgün olmak",
    "maskelerin ardındaki gerçek yüz", "içimizdeki yabancı",
    "kendinle barışmak", "kendini tanımak", "dönüşüm ve yeniden doğuş",
    "gölge benlik", "içsel çatışma", "kim olmak istiyoruz",

    # Duygu & Deneyim
    "acı ve büyüme", "yalnızlık", "sessizlik", "özlem",
    "aşk ve bağlılık", "kayıp ve yas", "hayal kırıklığı",
    "öfke ve dönüşüm", "utanç ve onur", "kırgınlık ve affetmek",
    "minnet ve şükran", "sevinç ve hafiflik", "keder ve güzellik",
    "nostalji", "huzur", "iç savaş",

    # İlişkiler & Bağ
    "dostluk", "sevgi", "yabancılaşma", "toplum ve birey",
    "aile ve bağlar", "güven ve ihanet", "empati ve merhamet",
    "yalnız kalabalıklar", "bağlanma korkusu", "terk edilme",
    "sınır koymayı öğrenmek", "toxic ilişkilerden kurtulmak",
    "gerçek sevgi nedir", "koşulsuz sevgi",

    # Özgürlük & Güç
    "özgürlük", "direniş", "güç ve iktidar", "boyun eğmek ya da isyan",
    "vicdan", "adalet", "cesaret", "sorumluluk",
    "baskı altında var olmak", "kendi kaderini tayin",
    "özgürlük mü güvenlik mi", "isyan etmek",

    # Zihin & Bilgi
    "bilinç", "sezgi", "merak", "öğrenmek ve unutmak",
    "dil ve anlam", "gerçek ve yanılsama", "bilgi ve cehalet",
    "şüphe etmenin gücü", "akıl ve duygu", "rüyalar ve bilinçdışı",
    "algı ve gerçeklik", "düşüncenin gücü",

    # Doğa & Evren
    "doğa ile uyum", "evrenin sessizliği", "kaos ve düzen",
    "döngüler ve yenilenme", "ölüm ve doğa", "bütünle bağlantı",
    "sonsuzluk", "küçüklük ve büyüklük", "evrendeki yerimiz",

    # Başarı & Emek
    "emek ve anlam", "yaratıcılık", "başarı ve boşluk",
    "hırs ve tatmin", "mükemmeliyetçilik", "bırakmayı öğrenmek",
    "sabır", "alçakgönüllülük", "sadelik", "azla yetinmek",
    "para ve mutluluk", "başarı mı mutluluk mu",

    # Ruh & Maneviyat
    "iç huzur", "aydınlanma", "sessiz bilgelik", "dua ve teslimiyet",
    "spiritüel uyanış", "boşlukta var olmak", "tanrı ve insan",
    "inanç ve şüphe", "ruhun gıdası", "mistik deneyim",

    # Modern Hayat & Güncel
    "dijital çağda insan olmak", "sosyal medya ve kimlik",
    "modern insanın kaygıları", "teknoloji ve insanlık",
    "yapay zeka çağında anlam", "tüketim toplumunda mutluluk",
    "hız çağında yavaşlamak", "dikkat dağınıklığı",
    "başkalarının onayına ihtiyaç duymamak",
    "karşılaştırma tuzağından çıkmak", "kendi hızında ilerlemek",
    "sessizliğin gücü", "yavaşlamanın erdemi",
    "telefon bağımlılığı ve gerçek hayat",
    "bilgi çağında bilgelik", "çevrimiçi olmak çevrimdışı kalmak",

    # Psikolojik & Kişisel Gelişim
    "hayır diyebilmek", "kendi hikayenin kahramanı olmak",
    "geçmişi bırakmak ve ilerlemek", "iç eleştirmeni susturmak",
    "öz şefkat", "kırılganlığın gücü", "utançla yüzleşmek",
    "travma ve iyileşme", "korkuyla dans etmek",
    "güvensizlik ve özgüven", "içsel çocuk",

    # Toplum & Siyaset
    "eşitsizlik ve adalet", "özgürlük ve sorumluluk",
    "bireycilik ve dayanışma", "iktidar ve direniş",
    "normalin sorgulanması", "sisteme uymak ya da uymamak",
    "savaş ve barış", "insanlığın geleceği",

    # Ölüm & Kalıcılık
    "ölüm korkusu", "iyi yaşamak iyi ölmek",
    "geride bıraktıklarımız", "ölümlülüğü kucaklamak",
    "kalıcılık ve geçicilik", "unutulmak",
]

def generate_quote() -> dict:
    akim    = random.choice(AKIMLAR)
    filozof = random.choice(FILOZOFLAR[akim])
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
