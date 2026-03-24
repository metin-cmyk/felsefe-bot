import os, re, random, anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# 40+ Felsefi Akım, İnanç ve Gelenek
AKIMLAR = [
    "Stoacılık", "Budizm", "Taoizm", "Varoluşçuluk", "Nihilizm",
    "Pragmatizm", "Epikürcülük", "Skeptisizm", "Fenomenoloji",
    "Tasavvuf (Sufizm)", "İslam Felsefesi", "Türk Düşünce Tarihi",
    "Antik Yunan Felsefesi", "Aydınlanma Felsefesi", "Rasyonalizm",
    "Empirizm", "İdealizm", "Materyalizm", "Absürdizm", "Hümanizm",
    "Psikanaliz ve Derinlik Psikolojisi", "Postmodernizm", "Romantizm",
    "Kinik Felsefe", "Yeni Platonculuk", "Hermeneutik", "Zen Budizmi",
    "Hint Felsefesi (Vedanta)", "Divan Edebiyatı (Felsefi Yönü)", "Yapısalcılık",
    "Frankfurt Okulu", "Skolastik Felsefe", "Gnostisizm", "Panteizm",
    "Kinizm", "Sofistler", "Elea Okulu", "Egzistansiyel Psikoterapi",
    "Klasik Alman Felsefesi", "Mistisizm", "Sokrates Öncesi Felsefe"
]

# 300'den Fazla Düşünür, Şair, Mistik ve Filozof
FILOZOFLAR = {
    "Stoacılık": ["Marcus Aurelius", "Epiktetos", "Seneca", "Zeno", "Kleantes", "Chrysippos", "Musonius Rufus", "Panaitios", "Poseidonios", "Hierokles"],
    "Budizm": ["Buda", "Thich Nhat Hanh", "Dalai Lama", "Nagarjuna", "Shunryu Suzuki", "Bodhidharma", "Dogen", "Milarepa", "Vasubandhu", "Asanga", "Chandrakirti", "Padmasambhava"],
    "Taoizm": ["Laozi (Lao Tzu)", "Zhuangzi", "Sun Tzu", "Liezi", "Wang Bi", "Guo Xiang"],
    "Varoluşçuluk": ["Søren Kierkegaard", "Jean-Paul Sartre", "Simone de Beauvoir", "Karl Jaspers", "Gabriel Marcel", "Miguel de Unamuno", "Lev Şestov", "Nikolay Berdyayev", "Rollo May", "Paul Tillich"],
    "Nihilizm": ["Friedrich Nietzsche", "Emil Cioran", "Ivan Turgenev", "Max Stirner", "Gorgias", "Arthur Schopenhauer"],
    "Absürdizm": ["Albert Camus", "Samuel Beckett", "Franz Kafka", "Eugene Ionesco", "Daniil Kharms"],
    "Antik Yunan Felsefesi": ["Sokrates", "Platon", "Aristoteles", "Diyojen", "Herakleitos", "Pisagor", "Thales", "Parmenides", "Demokritos", "Anaksimandros", "Anaksimenes", "Empedokles", "Anaksagoras", "Epiküros"],
    "Epikürcülük": ["Epikür", "Lucretius", "Metrodorus", "Hermarchus", "Philodemus"],
    "Tasavvuf (Sufizm)": ["Mevlana Celaleddin Rumi", "Yunus Emre", "Hacı Bektaş Veli", "Şems-i Tebrizi", "Muhyiddin İbn'ül-Arabi", "Niyazi Mısri", "Ahmet Yesevi", "Hacı Bayram Veli", "Şeyh Galip", "Hallac-ı Mansur", "Feridüddin Attar", "Rabia el-Adeviyye", "Beyazıd-ı Bistami", "Erzurumlu İbrahim Hakkı", "Akşemseddin", "Eşrefoğlu Rumi", "Aziz Mahmud Hüdayi", "Somuncu Baba", "Şah-ı Nakşibend", "Abdülkadir Geylani"],
    "İslam Felsefesi": ["Farabi", "İbn Sina", "Gazali", "İbn Rüşd", "İbn Haldun", "El-Kindi", "Sühreverdi", "İbn Bacce", "İbn Tufeyl", "Ömer Hayyam", "Molla Sadra", "Fahreddin Razi", "İbn Hazm", "Nasîrüddin Tûsî"],
    "Türk Düşünce Tarihi": ["Ziya Gökalp", "Nurettin Topçu", "Cemil Meriç", "Yusuf Has Hacib", "İoanna Kuçuradi", "Hilmi Ziya Ülken", "Ahmet Hamdi Tanpınar", "Oğuz Atay", "Kemal Tahir", "Yusuf Akçura", "İsmail Hakkı Baltacıoğlu", "Sabahattin Ali", "Teoman Duralı", "Macit Gökberk", "Niyazi Berkes", "Bedia Akarsu", "Yalçın Koç"],
    "Aydınlanma Felsefesi": ["Immanuel Kant", "Jean-Jacques Rousseau", "Voltaire", "John Locke", "David Hume", "Montesquieu", "Denis Diderot", "Thomas Paine", "Adam Smith", "Cesare Beccaria"],
    "Rasyonalizm": ["Rene Descartes", "Baruch Spinoza", "Gottfried Wilhelm Leibniz", "Nicolas Malebranche", "Christian Wolff"],
    "Empirizm": ["John Locke", "George Berkeley", "David Hume", "Francis Bacon", "Thomas Hobbes"],
    "İdealizm": ["Hegel", "Kant", "Fichte", "Schelling", "Arthur Schopenhauer", "Benedetto Croce", "Giovanni Gentile"],
    "Materyalizm": ["Karl Marx", "Friedrich Engels", "Thomas Hobbes", "Ludwig Feuerbach", "Epicurus", "Lucretius", "Baron d'Holbach"],
    "Psikanaliz ve Derinlik Psikolojisi": ["Sigmund Freud", "Carl Gustav Jung", "Alfred Adler", "Erich Fromm", "Viktor Frankl", "Rollo May", "Jacques Lacan", "Karen Horney", "Wilhelm Reich", "Melanie Klein", "Donald Winnicott"],
    "Postmodernizm": ["Michel Foucault", "Jacques Derrida", "Jean Baudrillard", "Gilles Deleuze", "Slavoj Zizek", "Jean-François Lyotard", "Richard Rorty", "Judith Butler", "Giorgio Agamben", "Alain Badiou", "Felix Guattari"],
    "Fenomenoloji": ["Edmund Husserl", "Martin Heidegger", "Maurice Merleau-Ponty", "Emmanuel Levinas", "Paul Ricoeur", "Hannah Arendt"],
    "Romantizm": ["Arthur Schopenhauer", "Johann Wolfgang von Goethe", "Ralph Waldo Emerson", "Henry David Thoreau", "Friedrich Schiller", "William Blake", "Novalis", "Lord Byron", "John Keats"],
    "Hint Felsefesi (Vedanta)": ["Adi Şankara", "Ramanuja", "Swami Vivekananda", "Sri Aurobindo", "Jiddu Krishnamurti", "Osho", "Ramana Maharshi", "Patanjali", "Mahavira"],
    "Kinik Felsefe": ["Diyojen (Sinoplu)", "Antisthenes", "Krates", "Hipparkhia", "Bion"],
    "Zen Budizmi": ["D.T. Suzuki", "Alan Watts", "Linji", "Hakuin", "Bankei", "Ikkyu", "Seung Sahn"],
    "Divan Edebiyatı (Felsefi Yönü)": ["Fuzuli", "Baki", "Nabi", "Nedim", "Şeyhülislam Yahya", "Nefi", "Karacaoğlan", "Pir Sultan Abdal", "Nesimi", "Kadı Burhaneddin", "Ruşeni"],
    "Frankfurt Okulu": ["Theodor W. Adorno", "Max Horkheimer", "Walter Benjamin", "Herbert Marcuse", "Jürgen Habermas", "Erich Fromm"],
    "Skolastik Felsefe": ["Thomas Aquinas", "Anselmus", "Duns Scotus", "Bonaventura", "Ockhamlı William"],
    "Mistisizm": ["Eckhart Tolle", "Meister Eckhart", "Hildegard von Bingen", "Teresa of Avila", "John of the Cross", "Jakob Böhme", "Gurdjieff"]
}

# Yüzlerce Felsefi, Psikolojik ve Mistik Konu Başlığı (Genişletilmiş Dev Havuz)
KONULAR = [
    # ⏳ ZAMAN, GEÇİCİLİK VE HAFIZA
    "Zamanın acımasız geçiciliği ve anı yakalamak", "Geçmişin bir illüzyon, geleceğin ise bir kaygı olması", 
    "Hatıraların insan ruhuna yüklediği ağır prangalar", "Unutmanın iyileştirici gücü ve nostaljinin zehri", 
    "İnsanın zamanla yarışması ve kaçınılmaz mağlubiyeti", "Sonsuzluk arzusunun ölümlü bedendeki trajedisi",
    "Yaşlanmanın bilgeliği vs. gençliğin kibri", "Anın (şimdi'nin) içindeki sonsuz derinlik",
    "Beklemenin ve sabrın ruhu nasıl yonttuğu", "Tarihin tekerrürü ve insanın ders almama ısrarı",

    # 🌌 VAROLUŞ, ANLAM VE ABSÜRTLÜK
    "İnsanın evrendeki kozmik hiçliği ve önemsizliği", "Hayatın kendiliğinden bir anlamı olmaması (Absürtlük)", 
    "Kendi anlamını yaratmanın verdiği ağır sorumluluk", "Kader, kaza ve özgür irade paradoksu", 
    "İntihar düşüncesi ve yaşama tutunma inadı", "Ruhun ölümsüzlüğü ve bedenin bir kafes oluşu",
    "Hiçlik korkusu ve varolma sancısı", "Gündelik hayatın sıradanlığında boğulmak",
    "Neden varız sorusunun cevapsızlığındaki huzur", "Tesadüflerin birleşip kaderi oluşturması",

    # 🎭 İÇ DÜNYA, PSİKOLOJİ VE EGO
    "Ego, kibir ve insanın kendi kendini kandırma sanatı", "Yalnızlığın yaratıcı gücü vs. yıkıcılığı", 
    "Kalabalıklar içindeki sessiz izolasyon", "Rüyalar, bilinçaltı ve içsel canavarlarla yüzleşmek", 
    "Korkuların esiri olmak ve cesaretin anatomisi", "Maskelerimiz (Persona) ve gerçek benliğimizi saklamamız",
    "Kendi içindeki karanlık (Gölge) ile barışmak", "Melankoli ve hüznün estetiği", 
    "Acı çekmenin ruhsal olgunlaştırıcılığı", "Kendini gerçekleştirme yolundaki engeller",
    "Kusurluluk ve mükemmeliyetçiliğin hastalıklı doğası", "Mutluluk arayışının paradoksal olarak mutsuzluk getirmesi",

    # ❤️ AŞK, İLİŞKİLER VE İNSAN DOĞASI
    "Aşkın mülkiyet arzusuyla zehirlenmesi", "Gerçek sevginin beklentisiz ve özgür bırakan doğası", 
    "İhanetin bıraktığı izler ve affetmenin imkansızlığı", "Tutkuların aklı kör etmesi ve irade zayıflığı", 
    "Gerçek dostluğun modern çağda nadirliği", "Sessizliğin ve bakışların iletişimdeki gücü", 
    "İnsanlara duyulan güvenin kırılganlığı", "Toksik bağlılıklar ve bağımlılıktan özgürleşme",
    "Kıskançlık, haset ve başkasının hayatına duyulan açlık", "Fedakarlık adı altındaki gizli bencillik",
    "Cinsellik, haz ve bedenin felsefesi", "Ayrılığın yas süreci ve yeniden doğuş",

    # ⚖️ AHLAK, ERDEM VE VİCDAN
    "Vicdanın susmak bilmeyen sesi", "Toplumsal ahlakın ikiyüzlülüğü", 
    "Gerçek adalet ve dünyadaki hakkaniyetsizlik", "Tevazu (alçakgönüllülük) ve kibrin yıkıcılığı", 
    "İyilik yapmanın altında yatan bencilce güdüler", "Suçluluk duygusu, günah ve kefaret arayışı", 
    "Sadakat ve verilen sözün ruhsal ağırlığı", "Kötülüğün sıradanlığı ve içimizdeki potansiyel zalim",
    "Erdemli yaşamanın zorluğu ve cazip günahlar", "Dürüstlüğün bedeli ve yalanın konforu",

    # 🏙️ TOPLUM, MODERN ÇAĞ VE YABANCILAŞMA
    "Modern dünyanın hızı ve insanın kendine yabancılaşması", "Teknoloji, ekranlar ve sanal gerçeklik illüzyonu", 
    "Tüketim çılgınlığı ve sahte ihtiyaçların kölesi olmak", "Toplumun bireyi ezmesi ve sürü psikolojisi", 
    "İktidar, güç zehirlenmesi ve itaat kültürü", "Cehaletin huzuru vs. bilginin verdiği derin acı", 
    "Hakikat arayışı ve medyanın algı yanılmaları", "Çalışmak, emek ve modern kölelik", 
    "Gösteriş toplumu ve başkaları için yaşamak", "Başarısızlığı kucaklamak ve sistemin başarı dayatması",
    "Siber çağda gerçek temasın ve samimiyetin ölümü", "Gürültü çağında sessizliği ve dinginliği kaybetmek",

    # 🕊️ TASAVVUF, DOĞU MİSTİSİZMİ VE DİNGİNLİK
    "Hiçlik makamı ve egonun yok oluşu (Fena fillah)", "Kusurları örtmek ve derin hoşgörü", 
    "Evrensel birlik (Vahdet-i Vücud) ve ayrımların bitişi", "Aklın yetersizliği ve hakikati kalbin gözüyle görmek", 
    "Nefis terbiyesi ve insanın kendi içindeki savaşı", "Tabiatla bütünleşmek ve doğanın sessiz bilgeliği", 
    "Sade yaşamak ve minimalizmin huzuru", "Teslimiyet, tevekkül ve akışa bırakmak",
    "Nefesin farkındalığı ve sadece 'burada' olmak (Zen)", "Dünyevi arzuların bir serap olması",
    "Ayna metaforu ve başkasında kendi yansımanı görmek", "Manevi uyanış ve üçüncü gözün açılması",

    # 🎭 SANAT, ESTETİK VE YARATICILIK
    "Sanatın ve estetiğin insan ruhunu iyileştiren gücü", "Kusurun içindeki güzellik (Wabi-sabi)", 
    "Yaratım sancısı ve ilhamın doğası", "Müziğin ve şiirin kelimelerin ötesine geçmesi",
    "Trajedinin estetiği ve acıdan doğan şaheserler", "Hayatı bir sanat eseri gibi yaşamak"
]
def generate_quote():
    akim = random.choice(AKIMLAR)
    
    # %80 ihtimalle listeden bilindik birini seç, %20 ihtimalle Claude'dan "Kıyıda köşede kalmış" birini bulmasını iste.
    if akim in FILOZOFLAR and FILOZOFLAR[akim] and random.random() < 0.8:
        filozof = random.choice(FILOZOFLAR[akim])
    else:
        filozof = "bu felsefi akımdan, tarihi kaynaklarda adı az geçen, gölgede kalmış ama çok derin bir düşünür"
        
    konu = random.choice(KONULAR)

    system = """Sen dünyaca ünlü, ansiklopedik bilgiye sahip bir felsefe profesörü ve bilgesin.
Sana verilen akım, filozof ve konu bağlamında; derinlikli, ufuk açıcı, daha önce internette klişeleşmemiş ÖZGÜN bir felsefi söz üret.

Eğer senden "az bilinen, gölgede kalmış bir düşünür" istenmişse, gerçekten tarihte yaşamış ama popüler olmayan bir ismi bul (örneğin: Ibn Tufeyl, Marguerite Porete, Zhuangzi'nin bir müridi, Philipp Mainländer, Suhreverdi vb.) ve sözü onun ağzından, onun gerçek ontolojik/epistemolojik felsefesine uygun yaz.

Söz kısa, vurucu ve Instagram/Twitter'da paylaşılmaya uygun olmalı. Kesinlikle klişe kişisel gelişim sözleri yazma; edebi, felsefi, sarsıcı ve ağırbaşlı olsun.

YANITINI AŞAĞIDAKİ FORMATTA VER. BAŞKA HİÇBİR ŞEY YAZMA:

SOZ:
[Ürettiğin felsefi söz, tırnak işareti kullanma]
---
YAZAR:
[Gerçek Filozofun/Düşünürün Adı]
---
AKIM:
[Felsefi Akım / Gelenek]
---
HASHTAG:
[#Felsefe #Bilgelik ve konuyla ilgili 3 hashtag daha]
---
ACIKLAMA:
[Sözün kısa, derinlikli Türkçe açıklaması — Instagram caption için 2-3 cümlelik bir zihin açıcı yorum]"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=700,
        system=system,
        messages=[{
            "role": "user",
            "content": f"Bağlam: {akim} felsefesi.\nDüşünür: {filozof}.\nKonu: '{konu}'\nBu bağlamda eşsiz ve sarsıcı bir felsefi alıntı ve analiz üret."
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
        pattern = rf"{key}:\n(.*?)(?:\n---|\Z)"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    quote    = _clean_quotes(get("SOZ"))
    author   = get("YAZAR")
    
    # Eğer yapay zeka YAZAR kısmını boş döndürürse veya bizim "az bilinen" talimatımızı basarsa, default'a dön
    if not author or "az bilinen" in author.lower():
        author = default_autor if "az bilinen" not in default_autor.lower() else "Anonim Bilge"

    akim     = get("AKIM") or default_akim
    hashtags = get("HASHTAG")
    aciklama = get("ACIKLAMA")

    if not hashtags:
        hashtags = "#Felsefe #Bilgelik #Düşünce #Hayat"

    twitter = f"{quote}\n\n— {author}"

    return {
        "quote": quote,
        "author": author,
        "akim": akim,
        "hashtags": hashtags,
        "aciklama": aciklama,
        "twitter": twitter
    }
