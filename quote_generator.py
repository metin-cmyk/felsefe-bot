import os, re, random, anthropic
from datetime import datetime

# ---------------------------------------------------------------------------
# Atatürk — Sadece doğrulanmış, kaynaklarda belgelenmiş sözler
# Kaynak: Nutuk, TBMM tutanakları, Atatürk'ün Söylev ve Demeçleri
# ---------------------------------------------------------------------------

ATATURK_SOZLER = [
    {
        "quote": "Egemenlik kayıtsız şartsız milletindir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "TBMM açılış konuşması, 23 Nisan 1920",
        "hashtags": "#Ataturk #Egemenlik #Cumhuriyet #Felsefe #Bilgelik",
        "aciklama": "Milli egemenliğin temel ilkesini ifade eden bu söz, Türkiye Büyük Millet Meclisi'nin kuruluşunda dile getirilmiştir.",
    },
    {
        "quote": "Muhtaç olduğun kudret, damarlarındaki asil kanda mevcuttur.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Gençliğe Hitabe, Nutuk, 1927",
        "hashtags": "#Ataturk #Genclige #Nutuk #Felsefe #Bilgelik",
        "aciklama": "Nutuk'ta gençliğe yönelik kaleme alınan bu satırlar, milletin iç gücüne ve direncine duyulan inancı yansıtır.",
    },
    {
        "quote": "Ey Türk gençliği! Birinci vazifen, Türk istiklalini, Türk Cumhuriyeti'ni ilelebet muhafaza ve müdafaa etmektir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Gençliğe Hitabe, Nutuk, 1927",
        "hashtags": "#Ataturk #Genclige #Nutuk #Felsefe #Bilgelik",
        "aciklama": "Nutuk'un sonunda gençliğe hitaben yazılan bu bölüm, cumhuriyetin gelecek nesillere emanet edilişini belgeler.",
    },
    {
        "quote": "Hayatta en hakiki mürşit ilimdir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Ilim #Bilim #Felsefe #Bilgelik",
        "aciklama": "Bilimi tek rehber olarak kabul eden bu söz, Atatürk'ün aydınlanmacı düşünce anlayışını özetler.",
    },
    {
        "quote": "Biz cahilliğe karşı savaştık, silahla yapılan savaştan daha zor olan bu savaş, hâlâ devam etmektedir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, Cilt II",
        "hashtags": "#Ataturk #Egitim #Aydinlanma #Felsefe #Bilgelik",
        "aciklama": "Eğitime ve bilgiye verdiği önemi vurgulayan Atatürk, cehaletle mücadeleyi silahlı savaştan daha uzun ve zorlu bulduğunu dile getirmiştir.",
    },
    {
        "quote": "Türk milletinin karakteri yüksektir, Türk milleti çalışkandır, Türk milleti zekidir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #TurkMilleti #Cumhuriyet #Felsefe #Bilgelik",
        "aciklama": "Türk milletinin temel niteliklerini sıralayan bu söz, ulusal kimliğin inşasına yönelik Atatürk'ün görüşünü yansıtır.",
    },
    {
        "quote": "Yurtta sulh, cihanda sulh.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün dış politika ilkesi, 1931",
        "hashtags": "#Ataturk #Baris #Sulh #Felsefe #Bilgelik",
        "aciklama": "Türkiye Cumhuriyeti'nin dış politikasının temel ilkesi olan bu söz, barışçı bir ulusal ve uluslararası düzen anlayışını ifade eder.",
    },
    {
        "quote": "Türk, öğün, çalış, güven.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #TurkMilleti #Calisma #Felsefe #Bilgelik",
        "aciklama": "Kısa ve öz biçimde milli bir ilkeyi dile getiren bu söz, özgüveni, emeği ve kimliği ön plana çıkarır.",
    },
    {
        "quote": "Büyük davamız, medeniyetçe en ileri, en müreffeh ve en mesut millet olmak ve olmaya devam etmektir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, Cilt I",
        "hashtags": "#Ataturk #Medeniyet #Kalkinma #Felsefe #Bilgelik",
        "aciklama": "Modernleşme ve uygarlık idealini açıkça ortaya koyan bu söz, Atatürk'ün Türkiye için belirlediği uzun vadeli hedefi yansıtır.",
    },
    {
        "quote": "Ne mutlu Türküm diyene.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "10. Yıl Nutku, 29 Ekim 1933",
        "hashtags": "#Ataturk #Cumhuriyet #OnYil #Felsefe #Bilgelik",
        "aciklama": "Cumhuriyetin onuncu yılında söylenen bu söz, ulusal kimlikle barışmayı ve gururu simgeleyen en bilinen ifadelerden biridir.",
    },
    {
        "quote": "Sanatsız kalan bir milletin hayat damarlarından biri kopmuş demektir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Sanat #Kultur #Felsefe #Bilgelik",
        "aciklama": "Sanatın milli hayattaki vazgeçilmez yerine dikkat çeken bu söz, Atatürk'ün kültür ve estetik anlayışını özetler.",
    },
    {
        "quote": "Türk çocuğu ecdadını tanıdıkça daha büyük işler yapmak için kendinde kuvvet bulacaktır.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Tarih #Genclik #Felsefe #Bilgelik",
        "aciklama": "Tarihi bilincin gençliğe güç verdiğini vurgulayan bu söz, geçmiş ile gelecek arasındaki köprüyü kurar.",
    },
    {
        "quote": "Ordumuz, Türk birliğinin, Türk kudret ve kabiliyetinin, Türk vatanseverliğinin çelik bir ifadesidir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Ordu #Vatan #Felsefe #Bilgelik",
        "aciklama": "Ordunun milli kimlikle ilişkisini ifade eden bu söz, ulusal savunma anlayışını ve millî birliği ön plana çıkarır.",
    },
    {
        "quote": "Fikri hür, vicdanı hür, irfanı hür nesiller yetiştirmek istiyoruz.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, Cilt II",
        "hashtags": "#Ataturk #Ozgurluk #Egitim #Felsefe #Bilgelik",
        "aciklama": "Eğitimin özgürlükçü ve aydınlanmacı boyutunu vurgulayan bu söz, Atatürk'ün nesiller için beslediği en temel ideali yansıtır.",
    },
    {
        "quote": "Hâkimiyet, hiçbir mânada, hiçbir şekil ve renkte, ortaklık kabul etmez.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "TBMM, 1923",
        "hashtags": "#Ataturk #Hakimiyet #BagimsizlikFelsefe #Bilgelik",
        "aciklama": "Milli egemenliğin bölünemezliğini ifade eden bu söz, cumhuriyetin kurucu ilkelerinden birini açıkça ortaya koyar.",
    },
]

def _get_ataturk_quote():
    """Doğrulanmış Atatürk sözlerinden rastgele birini döndürür. Claude hiç devreye girmez."""
    item = random.choice(ATATURK_SOZLER)
    quote = item["quote"]
    twitter_text = "%s\n\n— Mustafa Kemal Atatürk\n\n%s" % (quote, item["hashtags"])
    return {
        "quote":    quote,
        "author":   "Mustafa Kemal Atatürk",
        "akim":     item["akim"],
        "hashtags": item["hashtags"],
        "aciklama": item["aciklama"],
        "twitter":  twitter_text,
    }


client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# 50'den Fazla Felsefi Akım, İnanç ve Gelenek
AKIMLAR = [
    "Stoacılık", "Budizm", "Taoizm", "Varoluşçuluk", "Nihilizm", "Pragmatizm", "Epikürcülük", 
    "Skeptisizm", "Fenomenoloji", "Tasavvuf (Sufizm)", "İslam Felsefesi", "Türk Düşünce Tarihi",
    "Antik Yunan Felsefesi", "Aydınlanma Felsefesi", "Rasyonalizm", "Empirizm", "İdealizm", 
    "Materyalizm", "Absürdizm", "Hümanizm", "Psikanaliz ve Derinlik Psikolojisi", "Postmodernizm", 
    "Romantizm", "Kinik Felsefe", "Yeni Platonculuk", "Hermeneutik", "Zen Budizmi", "Hint Felsefesi (Vedanta)", 
    "Divan Edebiyatı (Felsefi Yönü)", "Yapısalcılık", "Frankfurt Okulu", "Skolastik Felsefe", 
    "Gnostisizm", "Panteizm", "Sofistler", "Elea Okulu", "Egzistansiyel Psikoterapi", "Klasik Alman Felsefesi", 
    "Mistisizm", "Sokrates Öncesi Felsefe", "Kozmoloji", "Kinizm", "Şintoizm (Felsefi Boyutu)", 
    "Kabalistik Felsefe", "Simya ve Okültizm", "Kıta Avrupası Felsefesi", "Analitik Felsefe", 
    "Faydacılık (Utilitarianism)", "Kişiselcilik (Personalizm)", "Post-yapısalcılık", "Karanlık Aydınlanma"
]

# 500'den Fazla Düşünür (Dev Havuz)
FILOZOFLAR = {
    "Stoacılık": ["Marcus Aurelius", "Epiktetos", "Seneca", "Zeno", "Kleantes", "Chrysippos", "Musonius Rufus", "Panaitios", "Poseidonios", "Hierokles", "Antipatros", "Diogenes of Babylon", "Aristo of Chios"],
    "Budizm": ["Buda", "Thich Nhat Hanh", "Dalai Lama", "Nagarjuna", "Shunryu Suzuki", "Bodhidharma", "Dogen", "Milarepa", "Vasubandhu", "Asanga", "Chandrakirti", "Padmasambhava", "Shantideva", "Atisha", "Naropa", "Marpa", "Tsongkhapa", "Nichiren", "Kukai", "Shinran", "Huineng"],
    "Taoizm": ["Laozi (Lao Tzu)", "Zhuangzi", "Sun Tzu", "Liezi", "Wang Bi", "Guo Xiang", "Ge Hong", "Zhang Daoling", "Wenzi"],
    "Varoluşçuluk": ["Søren Kierkegaard", "Jean-Paul Sartre", "Simone de Beauvoir", "Karl Jaspers", "Gabriel Marcel", "Miguel de Unamuno", "Lev Şestov", "Nikolay Berdyayev", "Rollo May", "Paul Tillich", "Fyodor Dostoyevski", "Martin Buber", "Jose Ortega y Gasset", "Colin Wilson", "Abdelwahab Meddeb"],
    "Nihilizm": ["Friedrich Nietzsche", "Emil Cioran", "Ivan Turgenev", "Max Stirner", "Gorgias", "Arthur Schopenhauer", "Philipp Mainländer", "Oswald Spengler", "Giacomo Leopardi", "Eduard von Hartmann"],
    "Absürdizm": ["Albert Camus", "Samuel Beckett", "Franz Kafka", "Eugene Ionesco", "Daniil Kharms", "Thomas Bernhard", "Fernando Pessoa"],
    "Antik Yunan Felsefesi": ["Sokrates", "Platon", "Aristoteles", "Diyojen", "Herakleitos", "Pisagor", "Thales", "Parmenides", "Demokritos", "Anaksimandros", "Anaksimenes", "Empedokles", "Anaksagoras", "Zenon (Elealı)", "Protagoras", "Ksenofanes", "Gorgias", "Antisthenes"],
    "Epikürcülük": ["Epikür", "Lucretius", "Metrodorus", "Hermarchus", "Philodemus", "Polyaenus", "Colotes", "Leontion"],
    "Tasavvuf (Sufizm)": ["Mevlana Celaleddin Rumi", "Yunus Emre", "Hacı Bektaş Veli", "Şems-i Tebrizi", "Muhyiddin İbn'ül-Arabi", "Niyazi Mısri", "Ahmet Yesevi", "Hacı Bayram Veli", "Şeyh Galip", "Hallac-ı Mansur", "Feridüddin Attar", "Rabia el-Adeviyye", "Beyazıd-ı Bistami", "Erzurumlu İbrahim Hakkı", "Akşemseddin", "Eşrefoğlu Rumi", "Aziz Mahmud Hüdayi", "Somuncu Baba", "Şah-ı Nakşibend", "Abdülkadir Geylani", "Sadreddin Konevi", "İmam Rabbani", "Molla Cami", "Hafız Şirazi", "Sadi Şirazi", "Fuzuli", "Pir Sultan Abdal", "Seyyid Nesimi", "Şabani Veli", "Merkez Efendi", "Ebul Hasan Harakani", "Şibli", "Cüneyd-i Bağdadi"],
    "İslam Felsefesi": ["Farabi", "İbn Sina", "Gazali", "İbn Rüşd", "İbn Haldun", "El-Kindi", "Sühreverdi", "İbn Bacce", "İbn Tufeyl", "Ömer Hayyam", "Molla Sadra", "Fahreddin Razi", "İbn Hazm", "Nasîrüddin Tûsî", "İhvan-ı Safa", "Biruni", "Sühreverdi el-Maktul", "İbnü'n-Nefis"],
    "Türk Düşünce Tarihi": ["Mustafa Kemal Atatürk", "Ziya Gökalp", "Nurettin Topçu", "Cemil Meriç", "Yusuf Has Hacib", "İoanna Kuçuradi", "Hilmi Ziya Ülken", "Ahmet Hamdi Tanpınar", "Oğuz Atay", "Kemal Tahir", "Yusuf Akçura", "İsmail Hakkı Baltacıoğlu", "Sabahattin Ali", "Teoman Duralı", "Macit Gökberk", "Niyazi Berkes", "Bedia Akarsu", "Yalçın Koç", "Namık Kemal", "Ali Suavi", "Prens Sabahaddin", "Erol Güngör", "Şerif Mardin", "Kemal Karpat", "İdris Küçükömer", "Sezai Karakoç", "İsmet Özel", "Attila İlhan", "Dursun Erkip"],
    "Aydınlanma Felsefesi": ["Immanuel Kant", "Jean-Jacques Rousseau", "Voltaire", "John Locke", "David Hume", "Montesquieu", "Denis Diderot", "Thomas Paine", "Adam Smith", "Cesare Beccaria", "Gotthold Ephraim Lessing", "Baron d'Holbach", "Marquis de Condorcet", "Mary Wollstonecraft"],
    "Rasyonalizm": ["Rene Descartes", "Baruch Spinoza", "Gottfried Wilhelm Leibniz", "Nicolas Malebranche", "Christian Wolff", "Blaise Pascal", "Antoine Arnauld"],
    "Empirizm": ["John Locke", "George Berkeley", "David Hume", "Francis Bacon", "Thomas Hobbes", "John Stuart Mill"],
    "İdealizm": ["Hegel", "Kant", "Fichte", "Schelling", "Arthur Schopenhauer", "Benedetto Croce", "Giovanni Gentile", "F.H. Bradley", "J.M.E. McTaggart", "T.H. Green"],
    "Materyalizm": ["Karl Marx", "Friedrich Engels", "Thomas Hobbes", "Ludwig Feuerbach", "Epicurus", "Lucretius", "Baron d'Holbach", "Julien Offray de La Mettrie", "Helvetius"],
    "Psikanaliz ve Derinlik Psikolojisi": ["Sigmund Freud", "Carl Gustav Jung", "Alfred Adler", "Erich Fromm", "Viktor Frankl", "Rollo May", "Jacques Lacan", "Karen Horney", "Wilhelm Reich", "Melanie Klein", "Donald Winnicott", "Anna Freud", "Otto Rank", "Sandor Ferenczi", "Irvin D. Yalom", "R.D. Laing"],
    "Postmodernizm": ["Michel Foucault", "Jacques Derrida", "Jean Baudrillard", "Gilles Deleuze", "Slavoj Zizek", "Jean-François Lyotard", "Richard Rorty", "Judith Butler", "Giorgio Agamben", "Alain Badiou", "Felix Guattari", "Paul Virilio", "Julia Kristeva", "Zygmunt Bauman"],
    "Fenomenoloji": ["Edmund Husserl", "Martin Heidegger", "Maurice Merleau-Ponty", "Emmanuel Levinas", "Paul Ricoeur", "Hannah Arendt", "Max Scheler", "Edith Stein", "Alfred Schutz"],
    "Romantizm": ["Arthur Schopenhauer", "Johann Wolfgang von Goethe", "Ralph Waldo Emerson", "Henry David Thoreau", "Friedrich Schiller", "William Blake", "Novalis", "Lord Byron", "John Keats", "Percy Bysshe Shelley", "Giacomo Leopardi", "Victor Hugo", "Søren Kierkegaard", "Walt Whitman"],
    "Hint Felsefesi (Vedanta)": ["Adi Şankara", "Ramanuja", "Swami Vivekananda", "Sri Aurobindo", "Jiddu Krishnamurti", "Osho", "Ramana Maharshi", "Patanjali", "Mahavira", "Madhvacharya", "Chaitanya Mahaprabhu", "Nisargadatta Maharaj"],
    "Kinik Felsefe": ["Diyojen (Sinoplu)", "Antisthenes", "Krates", "Hipparkhia", "Bion", "Menippos", "Demetrios"],
    "Zen Budizmi": ["D.T. Suzuki", "Alan Watts", "Linji", "Hakuin", "Bankei", "Ikkyu", "Seung Sahn", "Eisai", "Huangbo", "Zhaozhou", "Mazu Daoyi"],
    "Divan Edebiyatı (Felsefi Yönü)": ["Fuzuli", "Baki", "Nabi", "Nedim", "Şeyhülislam Yahya", "Nefi", "Karacaoğlan", "Pir Sultan Abdal", "Nesimi", "Kadı Burhaneddin", "Ruşeni", "Naili", "Neşati", "Naili-i Kadim", "Enderunlu Fazıl", "Zati", "Taşlıcalı Yahya"],
    "Frankfurt Okulu": ["Theodor W. Adorno", "Max Horkheimer", "Walter Benjamin", "Herbert Marcuse", "Jürgen Habermas", "Erich Fromm", "Siegfried Kracauer", "Leo Löwenthal", "Axel Honneth"],
    "Skolastik Felsefe": ["Thomas Aquinas", "Anselmus", "Duns Scotus", "Bonaventura", "Ockhamlı William", "Pierre Abelard", "Albertus Magnus", "Boethius", "Erigena"],
    "Mistisizm": ["Eckhart Tolle", "Meister Eckhart", "Hildegard von Bingen", "Teresa of Avila", "John of the Cross", "Jakob Böhme", "Gurdjieff", "Emanuel Swedenborg", "William Law", "Julian of Norwich", "Marguerite Porete", "Simeon the New Theologian"]
}

# 300+ Derin Felsefi / Psikolojik / Sosyolojik Konu Başlığı
KONULAR = [
    # ⏳ ZAMAN, GEÇİCİLİK, HAFIZA VE UZAM
    "Zamanın acımasız geçiciliği ve anı yakalamak", "Geçmişin bir illüzyon, geleceğin ise bir kaygı olması",
    "Hatıraların insan ruhuna yüklediği ağır prangalar", "Unutmanın iyileştirici gücü ve nostaljinin zehri",
    "İnsanın zamanla yarışması ve kaçınılmaz mağlubiyeti", "Sonsuzluk arzusunun ölümlü bedendeki trajedisi",
    "Yaşlanmanın bilgeliği vs. gençliğin kibri", "Anın (şimdi'nin) içindeki sonsuz derinlik",
    "Beklemenin ve sabrın ruhu nasıl yonttuğu", "Tarihin tekerrürü ve insanın ders almama ısrarı",
    "Mekanın ruh üzerindeki etkisi ve kök salma ihtiyacı", "Zamanın acı çekerken görece yavaşlaması",
    "Çocukluk saflığına duyulan bitmez özlem ve o bahçeden kovuluş", "Kendi cenazemizi hayal etmenin verdiği yaşama sevinci",
    "Hiç yaşanmamış anılara (Anemoia) duyulan tuhaf melankoli", "Geç kalan keşkelerin kalpte açtığı sessiz yaralar",
    "Yarın illüzyonuna inanıp bugünü cinayete kurban etmek", "Bir zamanlar her şeyimiz olan insanların yabancılaşması",
    "Fotoğrafların zamanı dondurma çabasındaki hüznü", "Saatin tik-taklarının aslında ömre atılan çizikler olması",
    
    # 🌌 VAROLUŞ, ANLAM, HİÇLİK, ABSÜRTLÜK VE ONTOLOJİ
    "İnsanın evrendeki kozmik hiçliği ve önemsizliği", "Hayatın kendiliğinden bir anlamı olmaması (Absürtlük)",
    "Kendi anlamını yaratmanın verdiği ağır sorumluluk", "Kader, kaza ve özgür irade paradoksu",
    "İntihar düşüncesi ve yaşama tutunma inadı", "Ruhun ölümsüzlüğü ve bedenin bir kafes oluşu",
    "Hiçlik korkusu ve varolma sancısı (Angst)", "Gündelik hayatın sıradanlığında ve rutinde boğulmak",
    "Neden varız sorusunun cevapsızlığındaki büyük huzur", "Tesadüflerin birleşip yenilmez bir kaderi oluşturması",
    "Sınır durumlar (Ölüm, acı, suçluluk) karşısında insanın çıplak kalması", "Ontolojik güvensizlik ve evsizlik hissi",
    "Kaderi sevmek (Amor Fati) ve başımıza gelen her şeyi kucaklamak", "Yaşamın trajik boyutu ve bunu kabullenmenin zarafeti",
    "Sisyphos'un kayayı tepeye çıkarırkenki gizli mutluluğu", "Var olmanın dayanılmaz hafifliği ve kararsızlık",
    "Kendi kendine doğmuş olma yanılgısı ve kökeni inkar", "Sürekli bir 'olma' halinde olup asla 'tamamlanamamak'",
    "Evrenin sağır sessizliği karşısında insanın çığlığı", "Ölümün varlığı sayesinde hayatın kıymetlenmesi paradoksu",
    
    # 🎭 İÇ DÜNYA, PSİKOLOJİ, EGO, KİMLİK VE GÖLGE BENLİK
    "Ego, kibir ve insanın kendi kendini kandırma sanatı", "Yalnızlığın yaratıcı gücü vs. yıkıcı ve çürütücü tarafı",
    "Kalabalıklar içindeki sağır edici izolasyon", "Rüyalar, bilinçaltı ve içsel canavarlarla yüzleşmek",
    "Korkuların esiri olmak ve cesaretin anatomisi", "Maskelerimiz (Persona) ve gerçek benliğimizi ömür boyu saklamamız",
    "Kendi içindeki karanlık (Gölge) ile barışmak ve onu ehlileştirmek", "Melankoli ve hüznün estetiği, acıdan zevk alma (Mazoşizm)",
    "Acı çekmenin ruhsal olgunlaştırıcılığı ve potada erimek", "Kendini gerçekleştirme yolundaki görünmez zihinsel engeller",
    "Kusurluluk ve mükemmeliyetçiliğin hastalıklı, yorucu doğası", "Mutluluk arayışının paradoksal olarak mutsuzluk ve anksiyete getirmesi",
    "Delilik ve dahilik arasındaki kıl payı ince çizgi", "Aşağılık kompleksi ve bunu örtbas etmek için kurulan üstünlük çabası",
    "Kendini affetmenin başkasını affetmekten bin kat zor olması", "Özsaygının inşası ve bir başkasının tek sözüyle yıkılabilmesi",
    "Kendi zihninin içinde hapis kalmak ve aşırı düşünme (Overthinking)", "Susarak çığlık atmak ve anlaşılmayı beklemek",
    "Bize ait olmayan hayalleri kendi hayalimiz sanarak yaşamak", "İçimizdeki çocuğun yaralarını bir ömür boyu taşımak",
    "Kendi yalanlarına inanacak kadar gerçeğe tahammülsüzlük",
    
    # ❤️ AŞK, İLİŞKİLER, DUYGULAR, BAĞLILIK VE İNSAN DOĞASI
    "Aşkın mülkiyet arzusuyla zehirlenmesi ve kafese konması", "Gerçek sevginin beklentisiz ve özgür bırakan, uçsuz bucaksız doğası",
    "İhanetin kalpte bıraktığı onulmaz izler ve affetmenin imkansızlığı", "Tutkuların aklı kör etmesi ve iradenin şehvete köle olması",
    "Gerçek dostluğun modern çağda elmas kadar nadir bulunması", "Sessizliğin ve bakışların binlerce kelimeden güçlü iletişimi",
    "İnsanlara duyulan güvenin cam kadar kırılganlığı", "Toksik bağlılıklar, vazgeçememe ve bağımlılıktan kanayarak özgürleşme",
    "Kıskançlık, haset ve başkasının hayatına duyulan bitmez tükenmez açlık", "Fedakarlık adı altındaki gizli bencillik ve borçlandırma psikolojisi",
    "Cinsellik, haz, bedenin felsefesi ve tensel uyuşma", "Ayrılığın yas süreci, parçalanma ve küllerinden yeniden doğuş",
    "İki ruhun birbirinde erimesi ve 'ben'in 'biz'de kaybolması", "Platonik aşkın ulaşılamaz mükemmelliği ve gerçeğin hayal kırıklığı",
    "Şefkatin dönüştürücü gücü ve merhametin dünyayı kurtarma ihtimali", "İnsanlara sınır koyamamanın getirdiği ruhsal tükeniş",
    "Aşık olduğumuz kişinin aslında kendi zihnimizdeki bir yansıma olması", "Biten bir aşkın ardından o kişinin bir yabancıya dönüşme hızı",
    "Aynı evin içinde iki yabancıya dönüşmenin sessiz trajedisi", "Sadece yalnızlıktan kaçmak için kurulan sahte ve içi boş ilişkiler",
    
    # ⚖️ AHLAK, ERDEM, VİCDAN, KÖTÜLÜK VE POLİTİKA
    "Vicdanın gece yarıları susmak bilmeyen, hesap soran sesi", "Toplumsal ahlakın vitrinliği ve arkasındaki devasa ikiyüzlülük",
    "Gerçek adalet arzusu ve dünyadaki tiksindirici hakkaniyetsizlik", "Tevazu (alçakgönüllülük) ihtişamı ve kibrin komik yıkıcılığı",
    "İyilik yapmanın altında yatan 'ben iyi biriyim' bencilce güdüsü", "Suçluluk duygusu, günah, pişmanlık ve ruhun kefaret arayışı",
    "Sadakat ve verilen sözün ruhsal ağırlığını taşımanın onuru", "Kötülüğün sıradanlığı, bürokrasisi ve içimizdeki potansiyel zalim",
    "Erdemli yaşamanın dik yokuşu ve cazip günahların yaldızlı yolları", "Dürüstlüğün ağır bedeli ve yalanın sağladığı konforlu yatak",
    "Devletin, otoritenin birey üzerindeki tahakkümü ve özgürlüğün gaspı", "Hukuk kuralları ile evrensel ahlakın birbirine zıt düşmesi",
    "Merhametin modern dünyada bir aptallık ve zaaf olarak algılanması", "İntikam duygusunun ruhu içeriden yiyip bitiren bir asit olması",
    "Savaşın anlamsız vahşeti ve barışın sürdürülemez ütopyası", "Kahraman yaratma ihtiyacı ve liderlere duyulan kölece itaat",
    "Suça sessiz kalmanın suçu işlemek kadar büyük bir ahlaki çöküş olması",
    
    # 🏙️ TOPLUM, MODERN ÇAĞ, BİLİM, KAPİTALİZM VE YABANCILAŞMA
    "Modern dünyanın baş döndürücü hızı ve insanın kendine yabancılaşması", "Teknoloji, ekranlar ve sanal gerçekliğin hakikati katletmesi",
    "Tüketim çılgınlığı, alışveriş bağımlılığı ve sahte ihtiyaçların kölesi olmak", "Toplumun farklı düşünen bireyi ezmesi, dışlaması ve sürü psikolojisi",
    "İktidar, güç zehirlenmesi, makam hırsı ve itaat kültürü", "Cehaletin getirdiği aptalca huzur vs. bilginin verdiği o derin, sancılı acı",
    "Hakikat arayışı, hakikatin bükülmesi ve medyanın kitleleri uyutması", "Çalışmak, emek sömürüsü, plaza hayatı ve modern kravatlı kölelik",
    "Sosyal medyadaki gösteriş toplumu ve 'başkaları ne der' zindanı", "Başarısızlığı kucaklamak ve sistemin dayattığı zehirli 'başarı' fetişi",
    "Siber çağda milyonlarca bağlantı arasında yaşanan o devasa yalnızlık", "Gürültü çağında sessizliği, dinginliği ve durup dinlenmeyi kaybetmek",
    "Kapitalizmin ruhu metalaştırması ve her şeye bir fiyat biçmesi", "Bürokrasinin, kağıtların insanı ruhsuz bir makineye dönüştürmesi",
    "Bilimin sınırları, aklın çaresizliği ve açıklayamadığı maneviyat", "Büyükşehir yalnızlığı, betonlaşan kalpler ve asansördeki sessizlik",
    "Algoritmaların bizi bizden daha iyi tanıyıp özgür irademizi hacklemesi", "Her şeyin fotoğrafını çekmekten anı yaşamayı unutma hastalığı",
    "Üretkenlik (productivity) baskısı altında ezilip yaşamayı kaçırmak", "Moda ve trendlerin kölesi olup kendi özgün zevkini yitirmek",
    
    # 🕊️ TASAVVUF, DOĞU MİSTİSİZMİ, DİN, AYDINLANMA VE DİNGİNLİK
    "Hiçlik makamı (Fena), egonun ölümü ve benliğin ortadan kalkması", "Başkalarının kusurlarını gece gibi örtmek ve derin, ilahi hoşgörü",
    "Evrensel birlik (Vahdet-i Vücud), yaradılanı Yaradan'dan ötürü sevmek", "Aklın bir noktada iflası ve hakikati ancak kalbin gözüyle görmek",
    "Nefis terbiyesi (Cihad-ı Ekber) ve insanın kendi arzularıyla olan en büyük savaşı", "Tabiatla bütünleşmek, ağacın dilini anlamak ve doğanın sessiz bilgeliği",
    "Sade yaşamak, dünyevi yüklerden arınmak ve dervişane minimalizmin huzuru", "Teslimiyet, tevekkül, endişeyi bırakmak ve kendini evrenin akışına bırakmak",
    "Nefesin farkındalığı, geçmiş ve geleceği silip sadece 'tam burada' olmak (Zen)", "Dünyevi arzuların, malın mülkün bir serap, bir gölge oyunu olması",
    "Ayna metaforu: Başkasında kınadığın veya övdüğün şeyin kendi yansıman olması", "Manevi uyanış, gaflet uykusundan uyanmak ve üçüncü gözün açılması",
    "İlahi aşk (Aşk-ı Hakiki) uğruna dünyevi mecazi aşklardan geçip gitmek", "Sessizlik orucu, kelimelerin israfı ve içsel gevezeliği tamamen susturmak",
    "Acının ve kederin ruhu yıkayan bir lütuf, bir uyanış alarmı olması", "Dünyanın koskoca bir rüya, ölümün ise asıl gerçeğe uyanış (Şeb-i Arus) olması",
    "Camide, kilisede veya tapınakta değil, hakikati kendi kalbinin içinde aramak", "Her düşüşün aslında yukarıya, kendi içine doğru bir yükseliş olması",
    "Dünyada misafir (yolcu) olduğunu bilmek ve hiçbir şeyi sahiplenmemek",
    
    # 🎭 SANAT, ESTETİK, DİL, SÖZ VE YARATICILIK
    "Sanatın ve estetiğin insan ruhunu iyileştiren, arındıran eşsiz gücü", "Kusurun, çatlağın ve yaşanmışlığın içindeki o derin güzellik (Wabi-sabi)",
    "Yaratım sancısı, ilham perisinin kaprisleri ve hiçlikten bir şey var etmek", "Müziğin ve şiirin kelimelerin kifayetsiz kaldığı sınırın ötesine geçmesi",
    "Trajedinin estetiği: En acı veren olaylardan en ölümsüz şaheserlerin doğması", "Hayatı sıradan bir varoluş değil, bir sanat eseri gibi ince ince yaşamak",
    "Dilin yetersizliği, kelimelerin kalıbına sığmayan o devasa, anlatılamayan hisler", "Sözcüklerin hakikati ne kadar çarpıttığı ve anlamın dilde kaybolması",
    "Yazmanın, boyamanın veya yontmanın ölüme ve unutulmaya meydan okuması", "Sıradan olanın, bir toz zerresinin içindeki olağanüstü evreni görmek (Epifani)",
    "Deliliğin sanata dönüşmesi ve aklın zincirlerinden kurtulan yaratıcılık", "Okunan bir kitabın veya izlenen bir tablonun insanın ruhunu geri dönülmez şekilde değiştirmesi"
]

def generate_quote():
    bugun = datetime.now()
    ay = bugun.month
    gun = bugun.day
    ozel_gun_mesaji = None
    
    if ay == 11 and gun == 10:
        ozel_gun_mesaji = "BUGÜN 10 KASIM, ATATÜRK'Ü ANMA GÜNÜ. Söz doğrudan onun fikirlerinin ölümsüzlüğü, hüznün kararlılığa dönüşmesi ve Cumhuriyet'in sonsuz bekası üzerine son derece etkileyici, asil ve sarsıcı bir mesaj içermeli."
    elif ay == 10 and gun == 29:
        ozel_gun_mesaji = "BUGÜN 29 EKİM CUMHURİYET BAYRAMI. Söz doğrudan Cumhuriyet'in fazileti, milletin bağımsızlık karakteri, aydınlanma, çağdaşlaşma ve egemenlik üzerine çok coşkulu, devrimci bir mesaj içermeli."
    elif ay == 8 and gun == 30:
        ozel_gun_mesaji = "BUGÜN 30 AĞUSTOS ZAFER BAYRAMI. Söz doğrudan Türk milletinin ve ordusunun bağımsızlık azmi, esarete karşı isyanı, emperyalizme vurulan tokat ve hürriyetin kutsallığı üzerine destansı bir mesaj içermeli."
    elif ay == 5 and gun == 19:
        ozel_gun_mesaji = "BUGÜN 19 MAYIS. Söz doğrudan kurtuluş ateşinin yakılması, gençliğe duyulan güven, umut, akılcılık ve Türkiye'nin aydınlık geleceği üzerine motive edici bir mesaj içermeli."
    elif ay == 4 and gun == 23:
        ozel_gun_mesaji = "BUGÜN 23 NİSAN. Söz doğrudan kayıtsız şartsız milli egemenlik, çocuklara ve geleceğe bırakılan aydınlık miras, meclisin ve demokrasinin gücü üzerine olmalı."

    if ozel_gun_mesaji:
        # Özel günlerde de Atatürk için sadece doğrulanmış sözler listesinden al
        return _get_ataturk_quote()
    elif random.random() < 0.20:
        # Atatürk için Claude kullanılmaz — doğrulanmış sözler listesinden al
        return _get_ataturk_quote()
    else:
        akim = random.choice(AKIMLAR)
        if akim in FILOZOFLAR and FILOZOFLAR[akim] and random.random() < 0.8:
            filozof = random.choice(FILOZOFLAR[akim])
        else:
            filozof = "bu felsefi akımdan, tarihi kaynaklarda adı az geçen, gölgede kalmış ama çok derin bir düşünür"
        konu = random.choice(KONULAR)

    # SENİN KATIKSIZ ORİJİNAL PROMPT KURALLARIN
    system = """Sen derin bir felsefe bilgisine sahip Türkçe içerik üreticisisin.
Felsefi sözler üretiyorsun — kısa, güçlü, düşündürücü.

Eğer düşünür Mustafa Kemal Atatürk ise:
- KESİNLİKLE kendi yazmadığı, söylemediği, kaynaklarda geçmeyen hiçbir söz üretme.
- Sadece Nutuk, TBMM tutanakları veya resmi tarihi kaynaklarda belgelenmiş, doğrulanmış sözlerini kullan.
- Uydurmak veya yorumlamak YASAKTIR. Doğrulanmış söz yoksa YAZAR alanına başka bir Türk düşünür yaz.
Değilse; verilen akıma ve düşünüre sadık kalarak çok vurucu, sarsıcı, özgün bir edebi alıntı üret. Klişelerden uzak dur.

ÖNEMLİ KURALLAR:
- SOZ alanında kesinlikle tirnak isareti (" veya \u201c veya ') KULLANMA. Sözü düz yaz.
- TWITTER alaninda da sözü tirnaksiz yaz.
- Hashtag'leri her zaman # ile baslat, Türkçe karakter kullanma (ö->o, ü->u, ş->s, ç->c, ı->i, ğ->g).

Yanitini TAM OLARAK su formatta ver:

SOZ:
[Türkçe felsefi söz — 1-2 cümle, max 200 karakter, TIRNAK KULLANMA]
---
YAZAR:
[Filozofun adi]
---
AKIM:
[Felsefi Akım / Gelenek]
---
HASHTAG:
[5 adet hashtag — #Felsefe ve #Bilgelik zorunlu, konuyla ilgili 3 tane daha ekle (Türkçe karakter kullanma)]
---
ACIKLAMA:
[Sözün kısa, derinlikli Türkçe açıklaması — 1-2 cümle, Instagram caption için]
---
TWITTER:
[Aynı felsefi söz (tırnaksız), iki satır boşluk, uzun tire (—) ve yazar adı]"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=700,
        system=system,
        messages=[{"role": "user", "content": f"Bağlam: {akim}.\nDüşünür: {filozof}.\nKonu: '{konu}'\nEşsiz bir alıntı ve analiz üret."}]
    )

    return _parse(msg.content[0].text.strip(), filozof, akim)

def _clean_quotes(text):
    text = text.strip()
    for q in ['\u201c', '\u201d', '\u2018', '\u2019', '"', "'"]:
        if text.startswith(q): text = text[1:]
        if text.endswith(q): text = text[:-1]
    return text.strip()

def _parse(text, default_autor, default_akim):
    def get(key):
        m = re.search(rf"{key}:\n(.*?)(?:\n---|\Z)", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    quote = _clean_quotes(get("SOZ"))
    author = get("YAZAR")
    if not author or "az bilinen" in author.lower():
        author = default_autor if "az bilinen" not in default_autor.lower() else "Anonim Bilge"

    hashtags = get("HASHTAG") or "#Felsefe #Bilgelik"
    twitter = get("TWITTER") or f"{quote}\n\n— {author}"

    return {
        "quote": quote,
        "author": author,
        "akim": get("AKIM") or default_akim,
        "hashtags": hashtags,
        "aciklama": get("ACIKLAMA"),
        "twitter": twitter
    }
