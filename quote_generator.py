import os, re, random, anthropic, logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Atatürk — Sadece doğrulanmış, kaynaklarda belgelenmiş sözler
# Kaynak: Nutuk, TBMM tutanakları, Atatürk'ün Söylev ve Demeçleri
# ---------------------------------------------------------------------------

ATATURK_SOZLER = [

    # NUTUK (1927) — Gençliğe Hitabe
    {
        "quote": "Ey Türk gençliği! Birinci vazifen, Türk istiklâlini, Türk Cumhuriyetini ilelebet muhafaza ve müdafaa etmektir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Nutuk, Gençliğe Hitabe, 20 Ekim 1927",
        "hashtags": "#Ataturk #Nutuk #GencligeHitabe #Felsefe #Bilgelik",
        "aciklama": "Nutuk'un sonunda Türk gençliğine yönelik yazılan bu vasiyetin ilk ve en güçlü cümlesidir.",
    },
    {
        "quote": "Muhtaç olduğun kudret, damarlarındaki asil kanda mevcuttur.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Nutuk, Gençliğe Hitabe, 20 Ekim 1927",
        "hashtags": "#Ataturk #Nutuk #GencligeHitabe #Felsefe #Bilgelik",
        "aciklama": "Türk milletinin güç kaynağının kendi özünde bulunduğunu ifade eden bu söz, Gençliğe Hitabe'nin en bilinen satırlarındandır.",
    },
    {
        "quote": "Bugün ulaştığımız sonuç, asırlardan beri çekilen millî felâketlerin doğurduğu uyanıklığın ve bu aziz vatanın her köşesini sulayan kanların bedelidir. Bu sonucu, Türk gençliğine emanet ediyorum.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Nutuk, Kapanış bölümü, 20 Ekim 1927",
        "hashtags": "#Ataturk #Nutuk #Cumhuriyet #Felsefe #Bilgelik",
        "aciklama": "Kurtuluş Savaşı'nın bedelini ve cumhuriyetin emanetini anlatan bu cümleler, Nutuk'un kapanışından alınmıştır.",
    },
    {
        "quote": "Benim Türk milletine, Türk cemiyetine, Türklüğün istikbaline ait ödevlerim bitmemiştir, siz onları tamamlayacaksınız.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Nutuk, 1927",
        "hashtags": "#Ataturk #Nutuk #Genclik #Felsefe #Bilgelik",
        "aciklama": "Atatürk'ün tamamlanmamış görevlerini gençliğe bıraktığını ifade ettiği bu söz, Nutuk'tan alınmıştır.",
    },
    {
        "quote": "Cumhuriyeti biz kurduk, onu yükseltecek ve yaşatacak sizsiniz.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Nutuk, 1927",
        "hashtags": "#Ataturk #Cumhuriyet #Genclik #Felsefe #Bilgelik",
        "aciklama": "Cumhuriyetin yönetimini ve geleceğini genç nesillere devreden bu söz Nutuk'tan alınmıştır.",
    },

    # TBMM KONUŞMALARI
    {
        "quote": "Egemenlik kayıtsız şartsız milletindir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "TBMM açılış konuşması, 23 Nisan 1920",
        "hashtags": "#Ataturk #Egemenlik #TBMM #Felsefe #Bilgelik",
        "aciklama": "Türkiye Büyük Millet Meclisi'nin kuruluşunda dile getirilen bu söz, milli egemenliğin temel ilkesini özetler.",
    },
    {
        "quote": "Hâkimiyet, hiçbir mânada, hiçbir şekil ve renkte ortaklık kabul etmez.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "TBMM, 1923",
        "hashtags": "#Ataturk #Hakimiyet #Bagimsizlik #Felsefe #Bilgelik",
        "aciklama": "Millî egemenliğin bölünemezliğini kesin bir dille ortaya koyan bu söz TBMM kürsüsünden söylenmiştir.",
    },
    {
        "quote": "Uluslar, egemenliklerini geçici bile olsa bırakacağı meclislere dahi gereğinden fazla inanmamalı ve güvenmemelidir. Çünkü meclisler bile despotluk yapabilir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "TBMM konuşmaları",
        "hashtags": "#Ataturk #Demokrasi #Ozgurluk #Felsefe #Bilgelik",
        "aciklama": "Kurumsal gücün dahi sınırsız bırakılamayacağını vurgulayan bu söz, Atatürk'ün ileri görüşlü siyasi anlayışını yansıtır.",
    },
    {
        "quote": "İstiklal, istikbal, hürriyet, her şey adaletle kaimdir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "TBMM konuşmaları",
        "hashtags": "#Ataturk #Adalet #Hurriyet #Felsefe #Bilgelik",
        "aciklama": "Bağımsızlık ve özgürlüğün temelinin adalet olduğunu vurgulayan bu kısa ve güçlü söz, TBMM kayıtlarından alınmıştır.",
    },
    {
        "quote": "Savunma çizgisi yoktur, savunma alanı vardır. O alan bütün yurttur. Yurdun her karış toprağı vatandaşın kanıyla ıslanmadıkça düşmana bırakılamaz.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Nutuk, Kurtuluş Savaşı dönemi",
        "hashtags": "#Ataturk #Vatan #KurtulusSavasi #Felsefe #Bilgelik",
        "aciklama": "Kurtuluş Savaşı'nda vatan savunmasının sınırını ortadan kaldıran bu emir, Nutuk'ta kayıtlıdır.",
    },

    # SÖYLEV VE DEMEÇLER — BİLİM VE EĞİTİM
    {
        "quote": "Hayatta en hakiki mürşit ilimdir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Ilim #Bilim #Felsefe #Bilgelik",
        "aciklama": "Bilimi tek rehber kabul eden bu söz, Atatürk'ün aydınlanmacı düşünce anlayışının özlü ifadesidir.",
    },
    {
        "quote": "Dünyada her şey için, medeniyet için, hayat için, başarı için, en hakiki mürşit bilimdir, fendir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Bilim #Medeniyet #Felsefe #Bilgelik",
        "aciklama": "Bilim ve tekniğin medeniyetin tüm alanlarında rehber olduğunu vurgulayan bu söz, Atatürk'ün en temel ilkelerinden birini dile getirir.",
    },
    {
        "quote": "Eğitimdir ki, bir milleti ya özgür, bağımsız, şanlı, yüksek bir topluluk halinde yaşatır; ya da esaret ve sefalete terk eder.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Egitim #Ozgurluk #Felsefe #Bilgelik",
        "aciklama": "Eğitimin bir millet için hayati önemine dikkat çeken bu söz, Atatürk'ün Söylev ve Demeçleri'nde yer almaktadır.",
    },
    {
        "quote": "Millî Eğitim programımızın, Milli Eğitim siyasetimizin temel taşı, cahilliğin yok edilmesidir. Cahillik yok edilmedikçe, yerimizdeyiz.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Egitim #Aydinlanma #Felsefe #Bilgelik",
        "aciklama": "Eğitim politikasının temel hedefini ortaya koyan bu söz, cehaletle mücadeleyi millî ilerlemenin ön koşulu olarak tanımlar.",
    },
    {
        "quote": "Muallimler! Yeni nesli, Cumhuriyetin fedakâr öğretmenleri ve eğiticileri, sizler yetiştireceksiniz. Ve yeni nesil sizin eseriniz olacaktır.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, 1924",
        "hashtags": "#Ataturk #Ogretmen #Egitim #Felsefe #Bilgelik",
        "aciklama": "Öğretmenlerin cumhuriyetin inşasındaki belirleyici rolünü vurgulayan bu söz, 1924 yılında öğretmenlere yönelik konuşmadan alınmıştır.",
    },
    {
        "quote": "Fikri hür, vicdanı hür, irfanı hür nesiller yetiştirmek istiyoruz.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, Cilt II",
        "hashtags": "#Ataturk #Ozgurluk #Egitim #Felsefe #Bilgelik",
        "aciklama": "Eğitimin özgürlükçü ve aydınlanmacı boyutunu tanımlayan bu söz, Atatürk'ün nesiller için beslediği en temel ideali yansıtır.",
    },
    {
        "quote": "Büyük davamız, medeniyetçe en ileri, en müreffeh ve en mesut millet olmak ve olmaya devam etmektir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, Cilt I",
        "hashtags": "#Ataturk #Medeniyet #Kalkinma #Felsefe #Bilgelik",
        "aciklama": "Modernleşme ve uygarlık idealini açıkça ortaya koyan bu söz, Türkiye için belirlenen uzun vadeli hedefi ifade eder.",
    },

    # SÖYLEV VE DEMEÇLER — KADIN VE TOPLUM
    {
        "quote": "İnsan topluluğu kadın ve erkek denilen iki cins insandan mürekkeptir. Kabil midir ki, bu kütlenin bir parçasını ilerletelim, ötekini ihmal edelim de kütlenin bütünlüğü ilerleyebilsin?",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Kadin #Esitlik #Felsefe #Bilgelik",
        "aciklama": "Toplumsal ilerlemenin kadın ve erkek eşitliğine dayandığını anlatan bu metafor, Atatürk'ün en güçlü kadın hakları söylemlerinden biridir.",
    },
    {
        "quote": "Kadınlarımız, erkeklerden daha çok aydın, daha çok bilgili, daha çok faziletli olmaya mecburdurlar. Eğer gerçekten milletin anası olmak istiyorlarsa böyle olmalıdırlar.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Kadin #Egitim #Felsefe #Bilgelik",
        "aciklama": "Kadının aydınlanma ve bilgi konusundaki sorumluluğunu vurgulayan bu söz, Atatürk'ün Söylev ve Demeçleri'nde yer almaktadır.",
    },
    {
        "quote": "Dünyada hiçbir milletin kadını, ben Anadolu kadınından fazla çalıştım diyemez.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Kadin #AnadoluKadini #Felsefe #Bilgelik",
        "aciklama": "Kurtuluş Savaşı'nda Anadolu kadınının fedakârlığını ve çalışkanlığını öne çıkaran bu söz, Söylev ve Demeçler'den alınmıştır.",
    },
    {
        "quote": "Kadınlarımız ilim ve fen sahibi olacaklar ve erkeklerin geçtikleri bütün öğretim basamaklarından geçeceklerdir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Kadin #Ilim #Felsefe #Bilgelik",
        "aciklama": "Kadınların eğitimde erkeklerle tam eşitliğini savunan bu söz, Atatürk'ün toplumsal dönüşüm vizyonunun açık bir ifadesidir.",
    },

    # SÖYLEV VE DEMEÇLER — BAĞIMSIZLIK VE MİLLET
    {
        "quote": "Özgürlük ve bağımsızlık benim karakterimdir. Ben milletimin en büyük ve ecdadımın en değerli mirası olan bağımsızlık aşkıyla dolu bir adamım.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Ozgurluk #Bagimsizlik #Felsefe #Bilgelik",
        "aciklama": "Bağımsızlığı kendi karakterinin ayrılmaz parçası olarak tanımlayan bu söz, Atatürk'ün kişisel inancının özlü ifadesidir.",
    },
    {
        "quote": "Ne kadar zengin ve müreffeh olursa olsun, istiklâlden mahrum bir millet, medenî insanlık karşısında uşak olmak mevkiinden yüksek bir muameleye lâyık sayılamaz.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Istiklal #Bagimsizlik #Felsefe #Bilgelik",
        "aciklama": "Maddi zenginliğin bağımsızlığın yerini tutamayacağını ortaya koyan bu söz, Söylev ve Demeçler'de yer almaktadır.",
    },
    {
        "quote": "Biz Türkler, bütün tarihimiz boyunca hürriyet ve istiklâle timsal olmuş bir milletiz.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #TurkMilleti #Hurriyet #Felsefe #Bilgelik",
        "aciklama": "Türk milletinin tarihsel özgürlük geleneğini vurgulayan bu söz, millî kimliğin temel değerlerini özetler.",
    },
    {
        "quote": "Bir millet varlığını ve istiklalini kurtarabilmek için düşünülebilen her türlü teşebbüs ve fedakârlığı yaptıktan sonra başarıya ulaşır.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Nutuk, 1927",
        "hashtags": "#Ataturk #Nutuk #Istiklal #Felsefe #Bilgelik",
        "aciklama": "Milletin bağımsızlık mücadelesinde azmin ve fedakârlığın kaçınılmaz olduğunu anlatan bu söz Nutuk'tan alınmıştır.",
    },
    {
        "quote": "Millete efendilik yoktur. Hizmet vardır. Bu millete hizmet eden onun efendisi olur.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Millet #Hizmet #Felsefe #Bilgelik",
        "aciklama": "Liderin millete hizmetkâr olduğunu vurgulayan bu söz, Atatürk'ün demokratik liderlik anlayışını açıkça ortaya koyar.",
    },

    # SÖYLEV VE DEMEÇLER — SANAT VE KÜLTÜR
    {
        "quote": "Sanatsız kalan bir milletin hayat damarlarından biri kopmuş demektir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Sanat #Kultur #Felsefe #Bilgelik",
        "aciklama": "Sanatın milli yaşamdaki vazgeçilmez yerine dikkat çeken bu söz, Atatürk'ün kültür ve estetik anlayışını özetler.",
    },
    {
        "quote": "Bir millet sanattan ve sanatçıdan mahrumsa, tam bir hayata sahip olamaz. Böyle bir millet bir ayağı topal, bir kolu çolak, sakat ve alil bir kimse gibidir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Sanat #Kultur #Felsefe #Bilgelik",
        "aciklama": "Sanatsız bir milletin eksik kaldığını güçlü bir metaforla anlatan bu söz, Atatürk'ün sanat vizyonunu yansıtır.",
    },
    {
        "quote": "Hayatta müzik lazım değildir. Çünkü hayat müziktir. Müziksiz hayat zaten mevcut olamaz. Müzik hayatın neşesi, ruhu, sevinci ve her şeyidir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, 14 Ekim 1925, İzmir",
        "hashtags": "#Ataturk #Muzik #Sanat #Felsefe #Bilgelik",
        "aciklama": "Müziği hayatın kendisiyle özdeşleştiren bu derin söz, 1925'te İzmir'de söylenmiştir.",
    },

    # SÖYLEV VE DEMEÇLER — BARIŞ VE DIŞ POLİTİKA
    {
        "quote": "Yurtta sulh, cihanda sulh.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Türk dış politikasının temel ilkesi, 1931",
        "hashtags": "#Ataturk #Baris #Sulh #Felsefe #Bilgelik",
        "aciklama": "Türkiye Cumhuriyeti'nin dış politikasının temeli olan bu söz, barışçıl bir ulusal ve uluslararası düzen anlayışını ifade eder.",
    },
    {
        "quote": "Türkiye'nin gerçek sahibi ve efendisi, gerçek üretici olan köylüdür. O hâlde, herkesten daha çok refah, saadet ve servete müstahak ve lâyık olan köylüdür.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Koylu #Uretim #Felsefe #Bilgelik",
        "aciklama": "Üretici halkın toplumsal değerini öne çıkaran bu söz, Atatürk'ün demokratik ve halkçı tutumunu yansıtır.",
    },

    # SÖYLEV VE DEMEÇLER — MİLLİ HEYECAN VE GENÇLIK
    {
        "quote": "Gençler cesaretimizi takviye ve idame eden sizlersiniz. Siz, almakta olduğunuz terbiye ve irfan ile insanlık ve medeniyetin, vatan sevgisinin, fikir hürriyetinin en kıymetli timsali olacaksınız.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Genclik #Cesaret #Felsefe #Bilgelik",
        "aciklama": "Türk gençliğini medeniyetin ve özgürlüğün simgesi olarak tanımlayan bu söz, Söylev ve Demeçler'de yer almaktadır.",
    },
    {
        "quote": "Yükselen yeni nesil, istikbal sizsiniz.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Genclik #Istikbal #Felsefe #Bilgelik",
        "aciklama": "Geleceğin gençlerin elinde olduğunu vurgulayan bu kısa ve güçlü söz, Söylev ve Demeçler'den alınmıştır.",
    },
    {
        "quote": "Küçük hanımlar, küçük beyler! Sizler hepiniz geleceğin bir gülü, yıldızı ve ikbal ışığısınız. Memleketi asıl ışığa boğacak olan sizsiniz.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Cocuklar #Gelecek #Felsefe #Bilgelik",
        "aciklama": "Çocuklara yönelik bu sevecen hitap, onların ülkenin geleceğindeki belirleyici rolünü vurgular.",
    },
    {
        "quote": "Türk çocuğu ecdadını tanıdıkça daha büyük işler yapmak için kendinde kuvvet bulacaktır.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Tarih #Genclik #Felsefe #Bilgelik",
        "aciklama": "Tarihi bilincin gençliğe güç verdiğini vurgulayan bu söz, geçmişle gelecek arasındaki köprüyü kurar.",
    },

    # SÖYLEV VE DEMEÇLER — DEVLET VE SİYASET
    {
        "quote": "Benim gayem Türkiye'de, yeni Türkiye Cumhuriyeti'nde millet hâkimiyetini takviye etmek ve ebedîleştirmektir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, 1930",
        "hashtags": "#Ataturk #MilietHakimiyeti #Cumhuriyet #Felsefe #Bilgelik",
        "aciklama": "Devlet adamlığının amacını milli egemenliği kalıcı kılmak olarak tanımlayan bu söz, 1930 yılından bir basın toplantısından alınmıştır.",
    },
    {
        "quote": "Kendilerine bir milletin tarihi bırakılan adamlar, milletin kuvvet ve kudretini yalnız ve ancak yine milletin gerçek menfaatleri yolunda kullanmakla görevlidirler.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, 1924",
        "hashtags": "#Ataturk #Devlet #Millet #Felsefe #Bilgelik",
        "aciklama": "Devlet yetkisinin milletin çıkarına kullanılması gerektiğini vurgulayan bu söz, 1924 yılından alınmıştır.",
    },
    {
        "quote": "Millete efendilik yoktur. Hizmet vardır. Bu millete hizmet eden onun efendisi olur.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Hizmet #Liderlik #Felsefe #Bilgelik",
        "aciklama": "Demokratik liderliğin özünü tanımlayan bu söz, yönetimin millete hizmet etmekten ibaret olduğunu vurgular.",
    },

    # 10. YIL NUTKU VE ÖNEMLİ KONUŞMALAR
    {
        "quote": "Ne mutlu Türküm diyene.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "10. Yıl Nutku, 29 Ekim 1933",
        "hashtags": "#Ataturk #Cumhuriyet #OnYil #Felsefe #Bilgelik",
        "aciklama": "Cumhuriyetin onuncu yılında söylenen bu söz, ulusal kimlikle barışmayı ve millî gururu simgeleyen en bilinen ifadelerden biridir.",
    },
    {
        "quote": "Türk milleti, güçlükleri yenmesini bilen bir millettir. Her güçlüğün içinde bir fırsat yatar.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #TurkMilleti #Azim #Felsefe #Bilgelik",
        "aciklama": "Türk milletinin zorluklarla mücadele kapasitesini öne çıkaran bu söz, Söylev ve Demeçler'de yer almaktadır.",
    },
    {
        "quote": "Türk, öğün, çalış, güven.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #TurkMilleti #Calisma #Felsefe #Bilgelik",
        "aciklama": "Kısa ve öz biçimde milli bir ilkeyi dile getiren bu söz, özgüveni, emeği ve kimliği ön plana çıkarır.",
    },
    {
        "quote": "Türk milletinin karakteri yüksektir, Türk milleti çalışkandır, Türk milleti zekidir.",
        "akim": "Türk Düşünce Tarihi / Cumhuriyet",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #TurkMilleti #Karakter #Felsefe #Bilgelik",
        "aciklama": "Türk milletinin temel niteliklerini sıralayan bu söz, ulusal kimliğin inşasına yönelik Atatürk'ün görüşünü yansıtır.",
    },

    # BURSA ÖĞRETMENLERİNE KONUŞMA (1922)
    {
        "quote": "Bir milleti felâketten kurtarmakta, bir milleti aydınlatmakta devlet adamlarının sahip olduğu büyük önem inkâr edilemez.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Bursa Öğretmenlerine Konuşma, 1922",
        "hashtags": "#Ataturk #Devlet #Aydinlanma #Felsefe #Bilgelik",
        "aciklama": "1922'de Bursa'daki öğretmenlere yaptığı konuşmadan alınan bu söz, devlet adamlığının toplumsal aydınlanmadaki rolünü vurgular.",
    },
    {
        "quote": "Öğretmenler! Yeni neslin yetiştirilmesinde göstereceğiniz gayret ve fedakârlık, cumhuriyetin yarınını inşa edecektir.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Ogretmen #Egitim #Felsefe #Bilgelik",
        "aciklama": "Öğretmenlerin toplumdaki dönüştürücü gücüne dikkat çeken bu söz, eğitim alanındaki devrimci vizyonu yansıtır.",
    },

    # LAİKLİK VE MODERNLEŞME
    {
        "quote": "Laiklik asla dinsizlik olmadığı gibi, sahte dindarlık ve büyücülükle savaşma kapısı açtığı için, gerçek dindarlığın gelişmesi olanağını sağlamıştır.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, 1930",
        "hashtags": "#Ataturk #Laiklik #Modernlesme #Felsefe #Bilgelik",
        "aciklama": "Laikliği dinsizlikle karıştırılmasına açıkça karşı çıkan bu söz, 1930 yılında dile getirilmiştir.",
    },
    {
        "quote": "Bizim akıl, mantık, zekâ ile hareket etmek en belirgin özelliğimizdir. Bütün hayatımızı dolduran olaylar bu gerçeğin delillidirler.",
        "akim": "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak": "Atatürk'ün Söylev ve Demeçleri, 1925",
        "hashtags": "#Ataturk #Akil #Mantik #Felsefe #Bilgelik",
        "aciklama": "Aklın ve mantığın rehberliğini ön plana çıkaran bu söz, Atatürk'ün rasyonalist dünya görüşünü özetler.",
    },

    # ═══════════════════════════════════════════════
    # YENİ BÖLÜMLER — Nutuk, Gençliğe Hitabe, Demeçler
    # ═══════════════════════════════════════════════
    {
        "quote":    "1919 yılı Mayısının 19'uncu günü Samsun'a çıktım.",
        "akim":     "Türk Düşünce Tarihi / Siyasi Tarih",
        "kaynak":   "Nutuk, Giriş Bölümü, 1927",
        "hashtags": "#Ataturk #Nutuk #19Mayis #Tarih #Felsefe #Bilgelik",
        "aciklama": "Nutuk'un o sarsıcı açılış cümlesidir. Bu beş kelime, sıradan bir günlük kaydı gibi görünse de aslında yüzyıllık bir imparatorluğun enkâzından yeni bir ulusun doğuşunu simgeleyen tarihin en yüklü cümleleri arasındadır. Atatürk bu yalın anlatımla, büyük tarihsel kırılmaların çoğunlukla küçük bir adımla başladığını gösterir: bir iskelede karaya çıkmak, bir karara saplanmak, geri dönmemeye yemin etmek.",
    },
    {
        "quote":    "Efendiler, bu durum karşısında bir tek karar vardı. O da millî egemenliğe dayanan, kayıtsız şartsız bağımsız yeni bir Türk devleti kurmak!",
        "akim":     "Türk Düşünce Tarihi / Bağımsızlık",
        "kaynak":   "Nutuk, 1927",
        "hashtags": "#Ataturk #MilliEgemenlik #DevletKurmak #Felsefe #Bilgelik",
        "aciklama": "Bu söz, Milli Mücadele'nin salt bir 'vatan savunması'ndan çok daha büyük bir vizyona sahip olduğunu ortaya koyar: Atatürk'ün amacı, başından beri, eski düzeni onarmak değil; egemenliği gerçek sahibine — ulusa — geri veren tümüyle yeni bir devlet yaratmaktı. Elde silah savaşılırken kafada devlet kurulmaktaydı. Bu, tarihte nadir görülen bir zihinsel netliğin ve stratejik derinliğin itirafıdır.",
    },
    {
        "quote":    "Böyle bir millet esir yaşamaktansa mahvolsun daha iyidir! Öyleyse, ya istiklâl ya ölüm!",
        "akim":     "Türk Düşünce Tarihi / Ontolojik Özgüven",
        "kaynak":   "Nutuk, 1927",
        "hashtags": "#Ataturk #YaIstiklalYaOlum #Haysiyet #Felsefe #Bilgelik",
        "aciklama": "Bu sözde Atatürk, varoluşun biyolojik süreklilikten ibaret olmadığını; onurlu bir yaşamın, onursuz bir hayatta kalmadan her zaman üstün olduğunu ilan eder. Yabancı himayesini (mandacılığı) savunanlara verilen bu yanıt, aynı zamanda felsefi bir insan tanımıdır: İnsan, sadece nefes alan bir varlık değil, haysiyetiyle var olan bir özne olmalıdır. Özgürlüğün olmadığı yerde gerçek anlamda bir yaşamın da olmadığını söyler.",
    },
    {
        "quote":    "Milli siyaset dediğim zaman kastettiğim mana şudur: Milli sınırlarımız içinde, her şeyden önce kendi kuvvetimize dayanıp varlığımızı koruyarak, millet ve memleketin gerçek saadet ve refahına çalışmak.",
        "akim":     "Türk Düşünce Tarihi / Realizm",
        "kaynak":   "Nutuk, 1927",
        "hashtags": "#Ataturk #MilliSiyaset #Realizm #DisPolitika #Felsefe #Bilgelik",
        "aciklama": "Osmanlı'nın çöküşüne zemin hazırlayan üç büyük ideolojik hata —Türkçülük, Osmanlıcılık ve İslamcılık— hep sınırlarını aşan hayaller kurmuştu. Atatürk bu sözlerle hem bu mirasa hem de büyük güç politikasının büyüleyici aldatmacalarına karşı bir 'gerçekçilik manifestosu' yayımlar: Ayağının bastığı toprakta güçlen, kendi insanına bak, sonra dünyaya konuş.",
    },
    {
        "quote":    "Egemenlik ve saltanat hiç kimseye ilim icabıdır diye, görüşmeyle, tartışmayla verilmez. Egemenlik, saltanat kuvvetle, kudretle ve zorla alınır.",
        "akim":     "Türk Düşünce Tarihi / Siyaset Felsefesi",
        "kaynak":   "Nutuk, Saltanatın Kaldırılması Görüşmeleri, 1927",
        "hashtags": "#Ataturk #SaltanatinKaldirilmasi #Egemenlik #Guc #Felsefe #Bilgelik",
        "aciklama": "Mecliste saltanatın kaldırılmasını tartışan komisyonun gereksiz ikircikliğine karşı Atatürk'ün o ünlü müdahalesidir. Bu söz, modern siyaset felsefesinin temel gerçeklerinden birini işaret eder: İktidar, nezaket sonucu devredilmez; ya fiilen alınır ya da bırakılır. Meşruiyet onaylanmaz, inşa edilir. Tarihin sayfaları bu kaba gerçeği defalarca yazmıştır.",
    },
    {
        "quote":    "Milli emeller, milli irade yalnız bir şahsın düşünmesinden değil, bütün millet fertlerinin arzularının, emellerinin birleşmesinden ibarettir.",
        "akim":     "Türk Düşünce Tarihi / Demokratik Meşruiyet",
        "kaynak":   "Nutuk, 1927",
        "hashtags": "#Ataturk #MilliIrade #Demokrasi #Felsefe #Bilgelik",
        "aciklama": "Bu söz, 'kurtarıcı lider' mitine karşı çıkan paradoksal bir itiraftır — zira söyleyen kişi bizzat o mitin içindedir. Atatürk, millî iradenin kendisinden bile büyük olduğunu kabul eder: Devlet, bir dehanın projesine değil; ortak akla, paylaşılan emellere dayanmalıdır. Demokrasinin özündeki bu ilke, otoriter liderlik çağlarında hâlâ tartışılmaya değer bir hatırlatmadır.",
    },
    {
        "quote":    "Tatbik eden, icra eden, karar verenden daima daha kuvvetlidir.",
        "akim":     "Türk Düşünce Tarihi / Pragmatizm",
        "kaynak":   "Nutuk, 1927",
        "hashtags": "#Ataturk #Eylem #Icraat #Pragmatizm #Felsefe #Bilgelik",
        "aciklama": "Siyasette ve hayatta yalnızca fikrin üretilmesi yetmez; fikrin hayata geçirilmesi, karar mekanizmasından çok daha belirleyicidir. Atatürk bu tespitle bürokrasinin ürettiği eylemsizliğe, hayallerin arkasına sığınan tembelliğe ve 'karar verdim ama uygulayamadım' bahanesine karşı çıkar. Tarih, planları değil; uygulamaları kaydeder.",
    },
    {
        "quote":    "Biz, ilhamlarımızı gökten ve gaipten değil, doğrudan doğruya hayattan almış bulunuyoruz.",
        "akim":     "Türk Düşünce Tarihi / Pozitivizm",
        "kaynak":   "TBMM Konuşması, 1937",
        "hashtags": "#Ataturk #Laiklik #Pozitivizm #Devlet #Felsefe #Bilgelik",
        "aciklama": "Cumhuriyet'in teolojik bir rehbere değil, gözlemlenebilir gerçekliğe dayandığını ilan eden bu söz; aynı zamanda Aydınlanma'nın özlü bir tanımıdır. 'Gökyüzünden ilham almak', hem teokrasiyi hem de dogmatik ideolojiyi imler. Atatürk bunların karşısına somut bir alternatif koyar: Hayatın kendisi — acıları, deneyimleri ve dersleriyle — tek güvenilir kılavuzdur.",
    },
    {
        "quote":    "Milli egemenlik öyle bir nurdur ki, onun karşısında zincirler erir, taç ve tahtlar batar, mahvolur.",
        "akim":     "Türk Düşünce Tarihi / Demokrasi",
        "kaynak":   "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #MilliEgemenlik #Demokrasi #Felsefe #Bilgelik",
        "aciklama": "Siyasi dilin en güçlü metaforlarından biri: egemenlik, soyut bir hukuki kavram değil; karanlığı dağıtan, zinciri eriten, mutlak iktidarları yok eden bir 'nur'dur. Bu söz, hem şiirsel bir imgedir hem de tarihin önüne konulmuş bir kanıt: Monarşiler düşmüş, imparatorluklar çökmüş, ama halkın egemenlik talebi hiç susmamıştır.",
    },
    {
        "quote":    "Bilesiniz ki Türkiye Cumhuriyeti şeyhler, dervişler, müritler, meczuplar memleketi olamaz. En doğru, en hakiki tarikat, medeniyet tarikatıdır.",
        "akim":     "Türk Düşünce Tarihi / Aydınlanma",
        "kaynak":   "Kastamonu Nutku, 1925",
        "hashtags": "#Ataturk #Medeniyet #Tarikatlar #Aydinlanma #Felsefe #Bilgelik",
        "aciklama": "Bu söz hem bir yasak bildirisi hem de bir vizyon manifestosudur. Atatürk burada 'tarikat' kelimesini kasıtlı olarak kullanır: Eleştirdiği yapıların kendi içinde bir 'yol' (tarikat) kurduğunu kabul eder; ama onların karşısına evrensel uygarlığı 'tek gerçek yol' olarak koyar. Bireyleri cemaatin denetimine değil, aklın rehberliğine çağıran köklü bir paradigma değişikliğidir.",
    },
    {
        "quote":    "Sanatkar, toplumda uzun çaba ve çalışmalardan sonra alnında ışığı ilk hisseden insandır.",
        "akim":     "Türk Düşünce Tarihi / Estetik",
        "kaynak":   "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Sanatkar #Isik #Estetik #Felsefe #Bilgelik",
        "aciklama": "Atatürk'ün sanatçıya verdiği bu tanım, sıradan bir övgünün çok ötesindedir. Sanatçı, toplumun henüz adını koyamadığı duyguları, fikirleri ve dönüşümleri sezgisel olarak ilk kavrayandır. Bir bakıma, toplumun bilincinin öncüsüdür. Bu söz aynı zamanda sanatın siyasi bir işlevine de işaret eder: Aydınlanmanın ne kadar ilerlediğini ölçmek için sanata bakılmalıdır.",
    },
    {
        "quote":    "Kültür, okumak, anlamak, görebilmek, görebildiğinden mana çıkarmak, intibah almak, düşünmek, zekayı terbiye etmektir.",
        "akim":     "Türk Düşünce Tarihi / Kültür",
        "kaynak":   "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #Kultur #Zeka #Anlamak #Felsefe #Bilgelik",
        "aciklama": "Kültürü bir miras deposu veya 'folklorik koleksiyon' olarak gören pasif anlayışa karşı, Atatürk burada kültürü dinamik bir zihinsel süreç olarak tanımlar. Görmek yetmez, manasını çıkarmak gerekir; anlamak yetmez, uyanmak (intibah) gerekir. Bu dizi, aslında eleştirel düşüncenin ve bilimsel zihniyetin aşamalarını tarif eder. Modern bir eğitim felsefesinin özlü beyanıdır.",
    },
    {
        "quote":    "Ben, diktatör değilim. Ben kalpleri kırarak değil, kazanarak hükmetmek isterim.",
        "akim":     "Türk Düşünce Tarihi / Siyaset Psikolojisi",
        "kaynak":   "Yabancı Gazetecilere Verdiği Mülakat, 1930'lar",
        "hashtags": "#Ataturk #Liderlik #DiktatorKarsiti #GonulYapmak #Felsefe #Bilgelik",
        "aciklama": "Batı basınının diktatörlük suçlamalarına verilen bu cevap, hem diplomatik bir savunma hem de liderlik felsefesinin özlü bir tanımıdır. Atatürk iktidar ile meşruiyet arasındaki ince çizgiye işaret eder: Zorla da itaat ettirilebilirsin, ama gönülden kazanılmış bir ülke bambaşka bir güçtür. İktidarın gücünü rızadan alan bir siyaset anlayışı, çağları aşan bir yönetim bilgeliğidir.",
    },
    {
        "quote":    "İki Mustafa Kemal vardır: Biri ben, et ve kemik, geçici Mustafa Kemal... İkinci Mustafa Kemal, onu 'ben' kelimesiyle ifade edemem; o, ben değil, bizdir!",
        "akim":     "Türk Düşünce Tarihi / Ontoloji",
        "kaynak":   "Atatürk'ün Söylev ve Demeçleri, 1933",
        "hashtags": "#Ataturk #IkiMustafaKemal #Biz #Felsefe #Bilgelik",
        "aciklama": "Bu eşsiz öz-çözümleme, felsefi düzeyde bir 'benlik' tartışmasıdır. Atatürk, kendi beden varlığını (geçici, ölümlü) ile temsil ettiği fikri (kalıcı, kolektif) birbirinden ayırt eder. Bireysel ego değil, toplumsal bir uyanış hareketidir asıl 'Mustafa Kemal'. Bu ayrım, onu kişi kültünden çıkarıp bir düşünce geleneğinin sembolüne dönüştüren felsefi dürüstlüğün ifadesidir.",
    },
    {
        "quote":    "Basın hürriyetinden doğan mahzurların giderilme vasıtası, yine basın hürriyetidir.",
        "akim":     "Türk Düşünce Tarihi / Hukuk",
        "kaynak":   "Atatürk'ün Söylev ve Demeçleri",
        "hashtags": "#Ataturk #BasinHurriyeti #Medya #Ozgurluk #Felsefe #Bilgelik",
        "aciklama": "Özgür basının doğurduğu sorunların çözümünün sansür değil, yine özgürlük olduğunu savunan bu söz; bugün dijital platformların ve dezenformasyonun tartışıldığı bir çağda bile şaşırtıcı ölçüde günceldir. Konuşmayı durdurmak yerine daha iyi konuşmayı teşvik etmek — bu, demokratik bir toplumun öz-iyileşme mekanizmasının en doğru tarifidir.",
    },
    {
        "quote":    "Bizi mahvetmek isteyen emperyalizme karşı ve bizi yutmak isteyen kapitalizme karşı heyecanı milliye ile mücadele etmeyi uygun gören bir mesleği takip edenlerdeniz.",
        "akim":     "Türk Düşünce Tarihi / Siyaset Felsefesi",
        "kaynak":   "1. TBMM Kürsüsü, 1920",
        "hashtags": "#Ataturk #EmperyalizmKarsiti #MilliHeyecan #Felsefe #Bilgelik",
        "aciklama": "1920'de TBMM kürsüsünden söylenen bu sözler, Cumhuriyet'in anti-emperyalist kuruluş ruhunu belgelemesi açısından kritiktir. Atatürk hem siyasi sömürgeciliği (emperyalizm) hem de ekonomik boyundurluğu (kapitalizm) tek cümlede tanımlamış; bunlara karşı duracak gücü dış destekte değil, millî heycanda aramıştır. Bağımsızlık, tüm boyutlarıyla —askeri, ekonomik, kültürel— savunulması gereken bir bütündür.",
    },
    {
        "quote":    "Ekonomi demek, her şey demektir. Yaşamak için, mutlu olmak için, insan varlığı için ne lazımsa onların hepsi demektir.",
        "akim":     "Türk Düşünce Tarihi / İktisat",
        "kaynak":   "İzmir, 1923",
        "hashtags": "#Ataturk #Ekonomi #YasamakIcin #Felsefe #Bilgelik",
        "aciklama": "Bu tanım, ekonomiyi soyut bir para ve ticaret bilimi olmaktan çıkarıp; insanın gündelik hayatını, mutluluğunu ve varoluşunu doğrudan belirleyen temel gerçeklik olarak çerçeveler. Atatürk'ün bu yaklaşımı, ekonomik bağımsızlığı siyasi bağımsızlıkla aynı düzeyde tuttuğunu gösterir: Boş kâseyle özgür ülke olmaz.",
    },
    {
        "quote":    "Türkiye Cumhuriyeti'ni kuran Türkiye halkına Türk Milleti denir.",
        "akim":     "Türk Düşünce Tarihi / Sosyoloji",
        "kaynak":   "Medeni Bilgiler Kitabı (Atatürk'ün El Yazısı ile)",
        "hashtags": "#Ataturk #TurkMilleti #Cumhuriyet #Felsefe #Bilgelik",
        "aciklama": "Bu tanım, ırk veya kan temelli milliyetçiliğin karşısına 'yurttaşlık milliyetçiliğini' koyan devrimci bir hukuki ilkedir. Millet, etnik bir kategori değil; ortak bir devlet kuruculuğu eylemi etrafında bir araya gelen siyasi bir topluluktur. Bu yaklaşım; Diyarbakır'dan Trabzon'a, Trakya'dan Ege'ye kadar herkesin eşit onurla aynı vatanın sahibi olduğunu anayasal temele oturtur.",
    },
    {
        "quote":    "Ey Türk gençliği! Birinci vazifen; Türk istiklalini, Türk cumhuriyetini, ilelebet muhafaza ve müdafaa etmektir.",
        "akim":     "Türk Düşünce Tarihi / Varoluş Amacı",
        "kaynak":   "Nutuk, Gençliğe Hitabe, 20 Ekim 1927",
        "hashtags": "#Ataturk #GencligeHitabe #Vazife #Felsefe #Bilgelik",
        "aciklama": "Gençliğe Hitabe'nin açılış cümlesi olmasına karşın, kısa ömrü olan bir 'selam'dan çok daha fazlasıdır. Atatürk burada muhatabını ordu değil, gençlik olarak seçer; zira gençlik, her kuşakta yeniden doğan, yeniden yemin eden bir güçtür. 'İlelebet' sözcüğü zamansallığı aşar: Bu görev, bugün de, yüz yıl sonra da aynı ağırlıkla taşınmaya devam edecektir.",
    },
    {
        "quote":    "İstikbalde dahi seni bu hazineden mahrum etmek isteyecek dahilî ve haricî bedhahların olacaktır.",
        "akim":     "Türk Düşünce Tarihi / Siyasi Öngörü",
        "kaynak":   "Nutuk, Gençliğe Hitabe, 1927",
        "hashtags": "#Ataturk #Bedhahlar #SiyasiTehdit #Felsefe #Bilgelik",
        "aciklama": "1927 yılında yazılan bu cümle, tarihsel bir kehanetten çok daha derindir. Atatürk, tehditlerin yalnızca sınır dışından gelmeyeceğini —içeriden de çıkabileceğini— peşinen kabul eder. 'Dahilî bedhah' kavramı; her çağda kendini yenileyen, kimi zaman hırs kimi zaman ihanet kılığına bürünen bir tehlikeye dikkat çeker. Uyanık olmak, sadece dışa değil içe de bakmayı gerektirir.",
    },
    {
        "quote":    "Bütün bu şeraitten daha elim ve daha vahim olmak üzere, memleketin dahilinde iktidara sahip olanlar, gaflet ve dalalet ve hatta hıyanet içinde bulunabilirler.",
        "akim":     "Türk Düşünce Tarihi / Siyaset Felsefesi",
        "kaynak":   "Nutuk, Gençliğe Hitabe, 1927",
        "hashtags": "#Ataturk #Iktidar #Gaflet #Hiyanet #Felsefe #Bilgelik",
        "aciklama": "Gençliğe Hitabe'nin en keskin ve en cesur satırıdır. Atatürk burada dost düşman ayrımını ortadan kaldırır: İşgal ordusu, en kötü ihtimali bile değildir. Asıl felaketi, içerideki bilgisizlik, sapkınlık ve ihanet doğurur. Bu uyarı, güncelliğini hiç yitirmez; zira tarihin her döneminde toplumları asıl yıkan şey, dışarıdan gelen saldırıdan çok içeriden gelen çürümedir.",
    },
    {
        "quote":    "Ey Türk istikbalinin evladı! İşte, bu ahval ve şerait içinde dahi vazifen, Türk istiklal ve cumhuriyetini kurtarmaktır.",
        "akim":     "Türk Düşünce Tarihi / Kurtuluş Sorumluluğu",
        "kaynak":   "Nutuk, Gençliğe Hitabe, 1927",
        "hashtags": "#Ataturk #Vazife #IstikbalinEvladi #Felsefe #Bilgelik",
        "aciklama": "Hitabe boyunca sayılan tüm korkunç senaryoların (işgal, yönetici ihaneti, ekonomik çöküş) ardından gelen bu cümle, bir çöküş töreni değil; tersine, tam bir dirilişçağrısıdır. 'Dahi' kelimesi belirleyicidir: 'Bunlara rağmen, buna karşın.' Umutsuzluk yasaklanmıştır. Her kaos ortamının içine, göreve çağrı gizlenmiştir.",
    },
    {
        "quote":    "Muhtaç olduğun kudret, damarlarındaki asil kanda mevcuttur.",
        "akim":     "Türk Düşünce Tarihi / Ontolojik Özgüven",
        "kaynak":   "Nutuk, Gençliğe Hitabe, 1927",
        "hashtags": "#Ataturk #AsilKan #Kudret #GencligeHitabe #Felsefe #Bilgelik",
        "aciklama": "Gençliğe Hitabe'nin efsanevi kapanış cümlesidir. Atatürk burada büyük bir devrimci teselli sunar: Kurtuluş için bir kurtarıcı beklemeye gerek yoktur. Güç dışarıda değil, içeridedir — tarihin derinliklerinden akan, toprağa sinen, kanda yaşayan birikimli bir direnişte. Bu söz, nesiller boyu tekrarlanan bir cesaret aşısıdır; yılgınlığa karşı en eski ve en etkili panzehirlerden biridir.",
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
    "Stoacılık",
    "Epikürcülük",
    "Kinik Felsefe",
    "Skeptisizm",
    "Antik Yunan Felsefesi",
    "Sokrates Öncesi Felsefe",
    "Elea Okulu",
    "Sofistler",
    "Yeni Platonculuk",
    "Peripatetikler",
    "Budizm",
    "Zen Budizmi",
    "Taoizm",
    "Hint Felsefesi (Vedanta)",
    "Konfüçyüsçülük",
    "Rasyonalizm",
    "Empirizm",
    "Aydınlanma Felsefesi",
    "Klasik Alman Felsefesi",
    "İdealizm",
    "Romantizm",
    "Materyalizm",
    "Pragmatizm",
    "Analitik Felsefe",
    "Varoluşçuluk",
    "Absürdizm",
    "Nihilizm",
    "Fenomenoloji",
    "Hermeneutik",
    "Postmodernizm",
    "Post-yapısalcılık",
    "Frankfurt Okulu",
    "Eleştirel Teori",
    "Feminist Felsefe",
    "Bilim Felsefesi",
    "Zihin Felsefesi",
    "Faydacılık (Utilitarianism)",
    "Kişiselcilik (Personalizm)",
    "Psikanaliz ve Derinlik Psikolojisi",
    "Egzistansiyel Psikoterapi",
    "Hümanizm",
    "Kozmoloji",
    "Kinizm",
    "Skolastik Felsefe",
    "Kıta Avrupası Felsefesi",
    "Yapısalcılık",
    "Teknoloji Felsefesi",
    "Siyaset Felsefesi",
    "Estetik",
    "Etik",
    "Hukuk Felsefesi",
    "Türk Düşünce Tarihi",
]

# 500'den Fazla Düşünür (Dev Havuz)
FILOZOFLAR = {
    "Antik Yunan ve Ön-Sokratikler": ["Thales", "Anaksimandros", "Anaksimenes", "Pitagoras", "Herakleitos", "Parmenides", "Zenon (Elealı)", "Ksenofanes", "Empedokles", "Anaksagoras", "Demokritos", "Leukippos", "Philolaus", "Archytas", "Archelaus"],
    "Sokratik Dönem ve Platonizm": ["Sokrates", "Platon", "Speusippus", "Xenocrates", "Carneades", "Philo of Larissa", "Plutarch", "Numenius", "Atticus"],
    "Aristotelesçilik ve Peripatetikler": ["Aristoteles", "Theophrastus", "Strato", "Alexander of Aphrodisias", "Aristoxenus", "Eudemus of Rhodes", "Demetrius of Phalerum"],
    "Stoacılık (Tüm Dönemler)": ["Zeno of Citium", "Cleanthes", "Chrysippos", "Diogenes of Babylon", "Antipater of Tarsus", "Panaetius", "Posidonius", "Musonius Rufus", "Seneca", "Epiktetos", "Marcus Aurelius", "Hierocles"],
    "Epikürcülük": ["Epikür", "Metrodorus", "Hermarchus", "Leontion", "Colotes", "Philodemus", "Lucretius", "Zeno of Sidon", "Diogenes of Oenoanda"],
    "Kinik Felsefe": ["Antisthenes", "Diyojen (Sinoplu)", "Crates of Thebes", "Hipparchia", "Metrocles", "Menippus", "Bion of Borysthenes", "Teles"],
    "Skeptisizm": ["Pyrrho", "Timon of Phlius", "Aenesidemus", "Sextus Empiricus", "Arcesilaus"],
    "Yeni Platonculuk": ["Plotinus", "Porphyry", "Iamblichus", "Hypatia", "Proclus", "Damascius", "Simplicius", "Ammonius Saccas"],
    "Skolastik Felsefe": ["Boethius", "Anselm", "Peter Abelard", "Albertus Magnus", "Thomas Aquinas", "Bonaventure", "Roger Bacon", "Duns Scotus", "William of Ockham", "Jean Buridan", "Robert Grosseteste", "Francisco Suárez"],
    "Rönesans ve Hümanizm": ["Petrarca", "Erasmus", "Thomas More", "Machiavelli", "Marsilio Ficino", "Pico della Mirandola", "Giordano Bruno", "Tommaso Campanella", "Montaigne", "Francis Bacon"],
    "Rasyonalizm": ["Descartes", "Spinoza", "Leibniz", "Malebranche", "Antoine Arnauld", "Christian Wolff", "Blaise Pascal", "Noam Chomsky"],
    "Empirizm": ["John Locke", "George Berkeley", "David Hume", "Thomas Hobbes", "John Stuart Mill", "Jeremy Bentham", "Condillac", "Pierre Gassendi", "James Mill", "Hans Reichenbach"],
    "Aydınlanma Felsefesi": ["Voltaire", "Rousseau", "Montesquieu", "Diderot", "D'Alembert", "Holbach", "Condorcet", "Adam Smith", "Kant", "Lessing", "Herder", "Jacobi"],
    "Klasik Alman Felsefesi": ["Fichte", "Schelling", "Hegel", "Schleiermacher", "Novalis", "Arthur Schopenhauer", "Eduard von Hartmann", "Johann Wolfgang von Goethe", "Friedrich Schiller"],
    "Materyalizm": ["Karl Marx", "Friedrich Engels", "Feuerbach", "Lenin", "Gramsci", "Lukács", "Althusser", "Badiou", "Zizek", "Meillassoux"],
    "Analitik Felsefe": ["Frege", "Russell", "Wittgenstein", "Moore", "Carnap", "Quine", "Kripke", "Davidson", "Hilary Putnam", "David Lewis", "Sellars", "Ryle", "Austin", "Strawson", "Dummett", "Anscombe", "Parfit", "Nagel", "Searle", "Tarski", "Gettier"],
    "Bilim Felsefesi": ["Popper", "Kuhn", "Feyerabend", "Lakatos", "Bachelard", "Ian Hacking", "van Fraassen", "Duhem", "Poincaré", "Mach", "Hempel", "Nelson Goodman", "Penrose", "Gödel", "Hilbert", "Cantor"],
    "Zihin Felsefesi": ["Daniel Dennett", "David Chalmers", "Jerry Fodor", "Ned Block", "Thomas Nagel", "John Searle", "Frank Jackson", "Kim", "George Lakoff", "Andy Clark", "Antonio Damasio", "Douglas Hofstadter"],
    "Fenomenoloji": ["Husserl", "Heidegger", "Merleau-Ponty", "Sartre", "Levinas", "Paul Ricoeur", "Hans-Georg Gadamer", "Wilhelm Dilthey", "Edith Stein", "Max Scheler", "Roman Ingarden", "Jean-Luc Marion", "Derrida"],
    "Hermeneutik": [],
    "Varoluşçuluk": ["Søren Kierkegaard", "Jean-Paul Sartre", "Albert Camus", "Simone de Beauvoir", "Karl Jaspers", "Gabriel Marcel", "Emil Cioran", "Friedrich Nietzsche", "Viktor Frankl", "Irvin Yalom", "Paul Tillich", "Martin Buber"],
    "Nihilizm": ["Philipp Mainländer", "Giacomo Leopardi"],
    "Absürdizm": ["Samuel Beckett", "Franz Kafka", "Eugene Ionesco", "Thomas Bernhard", "Fernando Pessoa"],
    "Pragmatizm": ["Charles Sanders Peirce", "William James", "John Dewey", "George Herbert Mead", "Richard Rorty", "Ferdinand Canning Scott Schiller", "Robert Brandom"],
    "Frankfurt Okulu": ["Theodor Adorno", "Max Horkheimer", "Walter Benjamin", "Herbert Marcuse", "Jürgen Habermas", "Erich Fromm", "Axel Honneth", "Nancy Fraser"],
    "Postmodernizm": ["Michel Foucault", "Jacques Derrida", "Jean Baudrillard", "Gilles Deleuze", "Félix Guattari", "Jean-François Lyotard", "Judith Butler", "Giorgio Agamben", "Alain Badiou", "Julia Kristeva", "Paul Virilio", "Zygmunt Bauman", "Fredric Jameson", "Edward Said", "Gayatri Spivak"],
    "Siyaset Felsefesi": ["Hobbes", "Locke", "Bentham", "John Rawls", "Robert Nozick", "Ronald Dworkin", "Isaiah Berlin", "Hannah Arendt", "Michael Sandel", "Martha Nussbaum", "Amartya Sen", "Frantz Fanon", "Friedrich Hayek", "Peter Kropotkin"],
    "Psikanaliz ve Derinlik Psikolojisi": ["Sigmund Freud", "Carl Gustav Jung", "Alfred Adler", "Jacques Lacan", "Karen Horney", "Wilhelm Reich", "Melanie Klein", "Donald Winnicott", "Otto Rank", "Sandor Ferenczi", "Erik Erikson", "Heinz Kohut", "Harry Stack Sullivan", "James Hillman", "Wilfred Bion"],
    "Egzistansiyel Psikoterapi": ["Rollo May", "Ludwig Binswanger", "Medard Boss"],
    "Romantizm": ["Friedrich Schlegel", "William Blake", "Samuel Taylor Coleridge", "Friedrich Hölderlin"],
    "Budizm": ["Nagarjuna", "Vasubandhu", "Asanga", "Dignaga", "Dharmakirti", "Shantideva", "Bodhidharma", "Huineng", "Dogen", "Hakuin", "Bankei", "Shinran", "Daisetz Teitaro Suzuki", "Alan Watts"],
    "Zen Budizmi": ["Linji", "Shunryu Suzuki"],
    "Taoizm": ["Laozi", "Zhuangzi", "Liezi", "Wang Bi", "Guo Xiang", "Ge Hong"],
    "Hint Felsefesi (Vedanta)": ["Shankara", "Ramanuja", "Madhva", "Patanjali", "Kapila", "Swami Vivekananda", "Sri Aurobindo", "Jiddu Krishnamurti", "Ramana Maharshi", "Nisargadatta Maharaj", "Osho"],
    "Konfüçyüsçülük": ["Konfüçyüs", "Mencius", "Xunzi", "Zhu Xi", "Wang Yangming", "Han Fei", "Mozi"],
    "Türk Düşünce Tarihi": ["Mustafa Kemal Atatürk", "Ziya Gökalp", "İoanna Kuçuradi", "Hilmi Ziya Ülken", "Macit Gökberk", "Niyazi Berkes", "Bedia Akarsu", "Nermi Uygur", "Arda Denkel", "Teoman Duralı", "Afşar Timuçin", "Cemil Meriç", "Ahmet Arslan", "Doğan Özlem", "Saffet Murat Tura"],
    "Teknoloji Felsefesi": ["Martin Heidegger", "Jacques Ellul", "Lewis Mumford", "Bernard Stiegler", "Don Ihde", "Andrew Feenberg", "Donna Haraway", "Bruno Latour", "Nick Bostrom", "Ray Kurzweil", "Luciano Floridi"],
    "Feminist Felsefe": ["Mary Wollstonecraft", "Luce Irigaray", "bell hooks", "Angela Davis", "Carol Gilligan"],
    "Estetik": ["Arthur Danto", "Umberto Eco", "R. G. Collingwood", "Clive Bell", "Susan Sontag", "Roland Barthes", "John Berger", "Leo Tolstoy", "Oscar Wilde"],
    "Etik": ["Immanuel Kant", "Philippa Foot", "Peter Singer", "Derek Parfit", "Bernard Williams", "Alasdair MacIntyre", "G. E. Moore", "W. D. Ross", "Christine Korsgaard", "T. M. Scanlon"],
    "Hümanizm": ["Camus"],
    "Kozmoloji": [],
}
KONULAR = [
    "Zamanın acımasız geçiciliği ve anı yakalamak",
    "Geçmişin bir illüzyon, geleceğin ise bir kaygı olması",
    "Hatıraların insan ruhuna yüklediği ağır prangalar",
    "Unutmanın iyileştirici gücü ve nostaljinin zehri",
    "İnsanın zamanla yarışması ve kaçınılmaz mağlubiyeti",
    "Sonsuzluk arzusunun ölümlü bedendeki trajedisi",
    "Yaşlanmanın bilgeliği ve gençliğin kibri",
    "Anın içindeki sonsuz derinlik",
    "Beklemenin ve sabrın ruhu nasıl yonttuğu",
    "Tarihin tekerrürü ve insanın ders almama ısrarı",
    "Mekanın ruh üzerindeki etkisi ve kök salma ihtiyacı",
    "Çocukluk saflığına duyulan bitmez özlem",
    "Kendi cenazemizi hayal etmenin verdiği yaşama sevinci",
    "Hiç yaşanmamış anılara duyulan tuhaf melankoli",
    "Geç kalan keşkelerin kalpte açtığı sessiz yaralar",
    "Yarın illüzyonuna inanıp bugünü cinayete kurban etmek",
    "Fotoğrafların zamanı dondurma çabasındaki hüznü",
    "Eşyaların bizden daha uzun yaşaması karşısındaki ontolojik hüzün",
    "Paralel evrenler ihtimalinin yarattığı yaşanamamış hayatlar sancısı",
    "Entropi: Evrenin kaçınılmaz düzensizliğe gidişindeki şiirsellik",
    "Blok Evren: Zamanın bir nehir değil, sabit bir kütle olması",
    "Olay ufku: Geri dönüşü olmayan kararların yarattığı zihinsel tekillik",
    "Biyolojik saat ile toplumsal saat çatışması",
    "Zamanın metalaşması: Vaktin nakit olduğu kapitalist hapishane",
    "Prezentizm: Geçmişi ve geleceği bugünün değerleriyle yargılama hatası",
    "İnsanın evrendeki kozmik hiçliği ve önemsizliği",
    "Hayatın kendiliğinden bir anlamı olmaması (Absürtlük)",
    "Kendi anlamını yaratmanın verdiği ağır sorumluluk",
    "Kader, kaza ve özgür irade paradoksu",
    "Ruhun ölümsüzlüğü ve bedenin bir kafes oluşu",
    "Hiçlik korkusu ve varolma sancısı (Angst)",
    "Gündelik hayatın sıradanlığında ve rutinde boğulmak",
    "Neden varız sorusunun cevapsızlığındaki büyük huzur",
    "Tesadüflerin birleşip yenilmez bir kaderi oluşturması",
    "Sınır durumlar karşısında insanın çıplak kalması",
    "Ontolojik güvensizlik ve evsizlik hissi",
    "Kaderi sevmek (Amor Fati) ve başımıza gelen her şeyi kucaklamak",
    "Yaşamın trajik boyutu ve bunu kabullenmenin zarafeti",
    "Sisyphos'un kayayı tepeye çıkarırkenki gizli mutluluğu",
    "Var olmanın dayanılmaz hafifliği ve kararsızlık",
    "Sürekli bir 'olma' halinde olup asla 'tamamlanamamak'",
    "Evrenin sağır sessizliği karşısında insanın çığlığı",
    "Ölümün varlığı sayesinde hayatın kıymetlenmesi paradoksu",
    "Antinatalizm: Doğmanın bir zarar olduğu ve üremenin etik sorunu",
    "Kozmik Karamsarlık: Doğanın insana olan mutlak kayıtsızlığı",
    "Simülasyon Teorisi: Gerçekliğin bir yazılım olma ihtimali",
    "Ölümlülük bilinci ile ölümsüzlük fantezisi",
    "Varoluşsal Sıkıntı: Anlam eksikliğinin yarattığı ruhsal boşluk",
    "Ego, kibir ve insanın kendi kendini kandırma sanatı",
    "Yalnızlığın yaratıcı gücü ile yıkıcı tarafı",
    "Kalabalıklar içindeki sağır edici izolasyon",
    "Rüyalar, bilinçaltı ve içsel canavarlarla yüzleşmek",
    "Korkuların esiri olmak ve cesaretin anatomisi",
    "Maskelerimiz (Persona) ve gerçek benliğimizi saklamamız",
    "Kendi içindeki karanlık (Gölge) ile barışmak",
    "Melankoli ve hüznün estetiği",
    "Acı çekmenin ruhsal olgunlaştırıcılığı",
    "Kendini gerçekleştirme yolundaki görünmez engeller",
    "Kusurluluk ve mükemmeliyetçiliğin hastalıklı doğası",
    "Mutluluk arayışının getirdiği anksiyete",
    "Delilik ile dahilik arasındaki kıl payı ince çizgi",
    "Kendini affetmenin zorluğu",
    "Kendi zihninin içinde hapis kalmak (Overthinking)",
    "Susarak çığlık atmak",
    "Bize ait olmayan hayalleri kendi hayalimiz sanmak",
    "İçimizdeki çocuğun yaralarını ömür boyu taşımak",
    "Gerçeğe tahammülsüzlük ve yalanlara sığınma",
    "Kimlik inşası: Başkalarının aynasında kendimizi görme",
    "İçsel Sabotaj: Başarıya giden yolda kendi ayağına çelme takmak",
    "Sahte Kendilik: Toplumsal onay için ruhunu satmak",
    "Narsisizm: Kendi yansımasına aşık olmanın getirdiği yalnızlık",
    "Duygusal Zeka: Hislerin mantığa rehberlik etmesi",
    "Aşkın mülkiyet arzusuyla zehirlenmesi",
    "Gerçek sevginin beklentisiz doğası",
    "İhanetin kalpte bıraktığı onulmaz izler",
    "Tutkuların aklı kör etmesi",
    "Gerçek dostluğun modern çağda elmas kadar nadir olması",
    "Sessizliğin kelimelerden güçlü iletişimi",
    "İnsanlara duyulan güvenin cam kadar kırılganlığı",
    "Toksik bağlılıklar ve bağımlılıktan kanayarak özgürleşme",
    "Kıskançlık ve başkasının hayatına duyulan açlık",
    "Fedakarlık adı altındaki gizli bencillik",
    "Cinsellik, haz, bedenin felsefesi ve tensel uyuşma",
    "Ayrılığın yas süreci ve küllerinden doğuş",
    "İki ruhun birbirinde erimesi",
    "Platonik aşkın ulaşılamaz mükemmelliği",
    "Şefkatin dönüştürücü gücü",
    "İnsanlara sınır koyamamanın getirdiği ruhsal tükeniş",
    "Aşık olduğumuz kişinin kendi zihnimizdeki yansıması olması",
    "Arzu nesnesine ulaşınca duyulan boşluk",
    "Bağlanma korkusunun kökenindeki terk edilme dehşeti",
    "Romantik aşkın bir kurgu olduğu ve evrimin bizi kandırması",
    "Vicdanın gece yarıları hesap soran sesi",
    "Toplumsal ahlakın ikiyüzlülüğü",
    "Gerçek adalet arzusu ve dünyadaki hakkaniyetsizlik",
    "Tevazu ihtişamı ve kibrin yıkıcılığı",
    "İyilik yapmanın altında yatan bencilce güdüler",
    "Suçluluk duygusu ve ruhun kefaret arayışı",
    "Sadakat ve verilen sözün onuru",
    "Kötülüğün sıradanlığı ve içimizdeki zalim",
    "Erdemli yaşamanın dik yokuşu",
    "Dürüstlüğün ağır bedeli",
    "Devletin birey üzerindeki tahakkümü",
    "Hukuk ile evrensel ahlakın çatışması",
    "Merhametin zaaf olarak algılanması",
    "İntikamın ruhu yiyip bitiren bir asit olması",
    "Savaşın anlamsız vahşeti",
    "Suça sessiz kalmanın ahlaki çöküşü",
    "Faydacılık: Çoğunluğun iyiliği için bir kişinin feda edilmesi",
    "Deontoloji: Sonuç ne olursa olsun kurala uymanın ağırlığı",
    "Modern dünyanın hızı ve insanın kendine yabancılaşması",
    "Teknoloji ve sanal gerçekliğin hakikati öldürmesi",
    "Tüketim çılgınlığı ve sahte ihtiyaçların kölesi olmak",
    "Sürü psikolojisi ve toplumun bireyi ezmesi",
    "İktidar ve güç zehirlenmesi",
    "Cehaletin huzuru ile bilginin sancısı",
    "Hakikat sonrası (Post-truth) çağda yalanın yönetimi",
    "Modern kravatlı kölelik ve emek sömürüsü",
    "Sosyal medyadaki gösteriş toplumu",
    "Başarısızlığı kucaklamak ve başarı fetişi",
    "Siber çağda milyonlarca bağlantı arasındaki yalnızlık",
    "Gürültü çağında sessizliği kaybetmek",
    "Kapitalizmin ruhu metalaştırması",
    "Bürokrasinin insanı makineye dönüştürmesi",
    "Bilimin sınırları ve aklın çaresizliği",
    "Büyükşehir yalnızlığı ve betonlaşan kalpler",
    "Algoritmaların özgür irademizi hacklemesi",
    "Tekno-Feodalizm: Veri devlerinin yeni lordlar haline gelmesi",
    "Biyopolitika: Devletin bedenimiz ve sağlığımız üzerindeki kontrolü",
    "Gözetim Toplumu: Her hareketin kaydedildiği dijital panoptikon",
    "Kültür Endüstrisi: Sanatın tüketim malına indirgenmesi",
    "Hiçlik makamı, egonun ölümü",
    "Her zerrede bütünü görmek (Vahdet-i Vücud)",
    "Aklın iflası ve kalbin gözü",
    "Nefis terbiyesi ve içsel savaş",
    "Tabiatla bütünleşmek",
    "Dervişane minimalizm",
    "Teslimiyet ve akışa güvenmek",
    "Zen ve şimdinin gücü",
    "Dünyanın bir gölge oyunu olması",
    "Manevi uyanış ve gafletten kurtuluş",
    "İçsel cennet ve cehennem",
    "Yalnızlık içinde bütünle beraber olmak",
    "Ölmeden önce ölmek",
    "Acının bir lütuf olması",
    "Sanatın ruhu arındıran gücü",
    "Wabi-sabi: Kusurdaki güzellik",
    "Yaratım sancısı ve hiçlikten var etmek",
    "Müziğin kelimelerin ötesine geçmesi",
    "Trajediden ölümsüz şaheserlerin doğması",
    "Hayatı bir sanat eseri gibi yaşamak",
    "Dilin yetersizliği ve anlatılamayan hisler",
    "Anlamın dilde kaybolması",
    "Yazmanın ölüme meydan okuması",
    "Toz zerresindeki evreni görmek (Epifani)",
    "Deliliğin sanata dönüşmesi",
    "Kitapların ruhu geri dönülmez şekilde değiştirmesi",
    "Mimarinin insan ruhuna fısıldadığı otorite",
    "Sessizliğin kompozisyonu",
    "Soyut sanatın anlam ile anlamsızlığı arasındaki dans",
    "Sanatın politik bir silah olarak gücü",
    "Yapay zekanın ürettiği sanatın ruhsuzluğu",
    "Gerçeğin bilinemezliği (Şüphecilik)",
    "Mantıksal safsatalar ve düşünce tuzakları",
    "Dilin bir hapishane olması",
    "Paradoksların güzelliği",
    "Bilginin yük mü yoksa kanat mı olduğu",
    "Zekanın bir lanet olması",
    "Sezgilerin mantığa galip gelmesi",
    "Hakikatin parçalı doğası",
    "Bilimsel Paradigmalar: Gerçeğin her yüzyılda değişmesi",
    "Kuantum Belirsizliği: Gözlemcinin gerçeği değiştirmesi",
    "Gödel'in Eksiklik Teoremi: Mantığın kendi içindeki delikleri",
    "Yapay Zeka Etiği: Bir makineye vicdan yüklenebilir mi?",
    "Bilimsel determinizm ile rastlantısallık",
    "Hafızanın güvenilmezliği ve geçmişin yeniden inşası",
    "Bilişsel Önyargılar: Neden hep yanlış kararlar veriyoruz?",
    "Gerçekliğin sosyal bir kurgu olması",
    "İnsanın makineleşmesi ve makinelerin insanlaşması",
    "Ölümsüzlük arayışı: Bilinci dijital ortama aktarmak",
    "Transhümanizm: Biyolojik sınırları aşmak",
    "Dijital miras: Sosyal medya hayaletleri",
    "Deepfake ve gerçeklik algısının kaybı",
    "Teknolojik tekillik: İnsanın kendi yarattığı zekanın gerisinde kalması",
    "Metaverse: Yeni bir evren mi yoksa yeni bir kaçış mı?",
    "Algoritmik Aşk: Veri temelli eşleşmelerin ruhsuzluğu",
    "Dijital Detoks: Ekranlardan kurtulup gerçekliğe uyanmak",
    "Yapay Zekanın hakları olabilir mi?",
    "Bilginin demokratikleşmesi ile dezenformasyonun yayılması",
]


def _load_recent_authors(n=15):
    """Son n paylaşımdan yazar setini döndür."""
    try:
        pf = Path("posted.json")
        if not pf.exists():
            return set()
        posted = json.loads(pf.read_text(encoding="utf-8"))
        return set(p.get("author", "") for p in posted[-n:])
    except Exception:
        return set()

def _load_recent_quotes(n=30):
    """Son n paylaşımdan söz setini döndür (ilk 60 karakter)."""
    try:
        pf = Path("posted.json")
        if not pf.exists():
            return set()
        posted = json.loads(pf.read_text(encoding="utf-8"))
        return set(p.get("quote", "")[:60] for p in posted[-n:])
    except Exception:
        return set()

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
        recent_authors = _load_recent_authors(15)
        recent_quotes  = _load_recent_quotes(30)
        # Son 15 paylaşımda olmayan bir yazar seç
        for _ in range(20):
            akim = random.choice(AKIMLAR)
            if akim in FILOZOFLAR and FILOZOFLAR[akim] and random.random() < 0.8:
                filozof = random.choice(FILOZOFLAR[akim])
            else:
                filozof = random.choice(FILOZOFLAR.get("Antik Yunan Felsefesi", ["Sokrates"]))
            if filozof not in recent_authors:
                break
        konu = random.choice(KONULAR)
        log.info("Secilen filozof: %s" % filozof)

    MAX_DENEME = 8
    for deneme in range(MAX_DENEME):
        real_quotes, lang = _fetch_real_quotes_from_wikipedia(filozof)

        if real_quotes:
            filtered = [q for q in real_quotes if q[:60] not in recent_quotes]
            if not filtered:
                filtered = real_quotes

            raw    = _select_best_quote(filozof, akim, konu, filtered)
            result = _parse(raw, filozof, akim)
            if result and result.get("quote"):
                if result["quote"][:60] in recent_quotes:
                    log.warning("Bu soz zaten paylasılmis, atlaniyor.")
                else:
                    return result
            log.warning("Parse bos/tekrar, baska filozof deneniyor.")

        log.warning("Soz bulunamadi: %s (%d/%d)" % (filozof, deneme+1, MAX_DENEME))
        for _ in range(10):
            akim = random.choice(AKIMLAR)
            if akim in FILOZOFLAR and FILOZOFLAR[akim]:
                filozof = random.choice(FILOZOFLAR[akim])
            else:
                filozof = random.choice(FILOZOFLAR.get("Antik Yunan Felsefesi", ["Sokrates"]))
            if filozof not in recent_authors:
                break
        konu = random.choice(KONULAR)

    log.error("8 denemede de gercek soz bulunamadi.")
    return None

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

    # Boş söz — parse başarısız, None dön
    if not quote or len(quote.strip()) < 10:
        log.warning("Parse sonucu bos soz geldi, atlaniyor.")
        return None

    # Yabancı dil kontrolü — Türkçe değilse None dön
    if not _is_turkish(quote):
        log.warning("Parse sonucu yabanci dil sozü geldi, atlaniyor: %s" % quote[:50])
        return None

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

# ---------------------------------------------------------------------------
# Wikiquote wikitext API — gercek sozler (dosyanin sonuna eklendi)
# ---------------------------------------------------------------------------

import re as _re
import logging as _logging
_wq_log = _logging.getLogger(__name__)



def _name_variants(name):
    """Filozof adinin farkli Wikiquote varyantlarini uretir."""
    variants = [name]
    parts = name.strip().split()
    if len(parts) >= 2:
        variants.append(parts[-1])
        variants.append(parts[0])
        variants.append("%s %s" % (parts[-1], parts[0]))
    import re as _re2
    m = _re2.search(r"\(([^)]+)\)", name)
    if m:
        variants.append(name[:name.index("(")].strip())
        variants.append(m.group(1).strip())
    seen = set()
    result = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _fetch_wikiquote(philosopher):
    """Wikiquote TR ve EN wikitext API — en güvenilir kaynak."""
    import requests as _req

    def _parse_wikitext(wikitext):
        quotes = []
        for line in wikitext.split("\n"):
            s = line.strip()
            if not s.startswith("*") or s.startswith("**"):
                continue
            clean = s.lstrip("* ").strip()
            clean = _re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", clean)
            clean = _re.sub(r"\{\{[^}]*\}\}", "", clean)
            clean = _re.sub(r"<ref[^>]*>.*?</ref>", "", clean, flags=_re.DOTALL)
            clean = _re.sub(r"<br\s*/?>", " ", clean)
            clean = _re.sub(r"<[^>]+>", "", clean)
            clean = _re.sub(r"('''|'')", "", clean)
            clean = clean.strip().strip('"').strip("\'").strip()
            if 25 < len(clean) < 400:
                quotes.append(clean)
        return quotes

    name_variants = _name_variants(philosopher)
    for lang in ("tr", "en"):
        for name in name_variants:
            try:
                r = _req.get(
                    "https://%s.wikiquote.org/w/api.php" % lang,
                    params={"action": "parse", "page": name, "prop": "wikitext", "format": "json"},
                    timeout=12,
                )
                if r.status_code != 200:
                    continue
                data = r.json()
                if "error" in data:
                    continue
                wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
                if not wikitext:
                    continue
                quotes = _parse_wikitext(wikitext)
                if quotes:
                    log.info("Wikiquote %s [%s]: %d soz" % (lang.upper(), name, len(quotes)))
                    return quotes[:25]
            except Exception as e:
                log.warning("Wikiquote %s [%s] hatasi: %s" % (lang, name, e))
    return []


def _fetch_azquotes(philosopher):
    """AZQuotes.com — HTML parse, genis koleksiyon."""
    import requests as _req
    from urllib.parse import quote as _uq
    try:
        # AZQuotes URL formatı: /author/first-last
        slug = philosopher.lower()
        slug = _re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        url = "https://www.azquotes.com/author/%s" % slug
        headers = {"User-Agent": "Mozilla/5.0 (compatible; felsefemiz-bot/1.0)"}
        r = _req.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return []
        # <a class="title" ...> taglerini çıkar
        quotes = _re.findall(r'<a[^>]+class="title"[^>]*>([^<]{20,350})</a>', r.text)
        # HTML entity decode
        import html as _html
        quotes = [_html.unescape(q.strip()) for q in quotes if len(q.strip()) > 20]
        if quotes:
            log.info("AZQuotes [%s]: %d soz" % (philosopher, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("AZQuotes hatasi [%s]: %s" % (philosopher, e))
    return []


def _fetch_goodreads(philosopher):
    """Goodreads quotes search — HTML parse."""
    import requests as _req
    from urllib.parse import quote as _uq
    try:
        url = "https://www.goodreads.com/quotes/search?q=%s" % _uq(philosopher)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; felsefemiz-bot/1.0)"}
        r = _req.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return []
        # <div class="quoteText"> içindeki metni çıkar
        raw_blocks = _re.findall(r'<div\s+class="quoteText">(.*?)</div>', r.text, _re.DOTALL)
        quotes = []
        for block in raw_blocks:
            # HTML temizle
            text = _re.sub(r"<[^>]+>", "", block)
            import html as _html
            text = _html.unescape(text).strip()
            # Sadece tırnak içindeki kısmı al (― ile bitmeden önce)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                quote_text = lines[0].strip('""\u201c\u201d\u2018\u2019').strip()
                if 25 < len(quote_text) < 400:
                    quotes.append(quote_text)
        if quotes:
            log.info("Goodreads [%s]: %d soz" % (philosopher, len(quotes)))
        return quotes[:20]
    except Exception as e:
        log.warning("Goodreads hatasi [%s]: %s" % (philosopher, e))
    return []


def _fetch_felsefe_gen_tr(philosopher):
    """felsefe.gen.tr — Türkçe felsefe sitesi."""
    import requests as _req
    from urllib.parse import quote as _uq
    try:
        url = "https://felsefe.gen.tr/?s=%s" % _uq(philosopher)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; felsefemiz-bot/1.0)"}
        r = _req.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        # <blockquote> veya <p> içindeki felsefi sözleri çek
        quotes = _re.findall(r'<blockquote[^>]*>(.*?)</blockquote>', r.text, _re.DOTALL)
        result = []
        import html as _html
        for q in quotes:
            text = _re.sub(r"<[^>]+>", "", q)
            text = _html.unescape(text).strip()
            if 25 < len(text) < 400:
                result.append(text)
        if result:
            log.info("felsefe.gen.tr [%s]: %d soz" % (philosopher, len(result)))
        return result[:15]
    except Exception as e:
        log.warning("felsefe.gen.tr hatasi [%s]: %s" % (philosopher, e))
    return []


def _fetch_real_quotes_from_wikipedia(philosopher):
    """
    Çok kaynaklı söz toplama sistemi.
    Sıra: Wikiquote TR/EN → AZQuotes → Goodreads → felsefe.gen.tr
    İlk sonuç veren kaynaktan döner.
    """
    # 1. Wikiquote (en güvenilir)
    quotes = _fetch_wikiquote(philosopher)
    if quotes:
        return quotes, "wikiquote"

    # 2. AZQuotes
    quotes = _fetch_azquotes(philosopher)
    if quotes:
        return quotes, "azquotes"

    # 3. Goodreads
    quotes = _fetch_goodreads(philosopher)
    if quotes:
        return quotes, "goodreads"

    # 4. felsefe.gen.tr
    quotes = _fetch_felsefe_gen_tr(philosopher)
    if quotes:
        return quotes, "felsefe.gen.tr"

    log.warning("Hicbir kaynakta soz bulunamadi: %s" % philosopher)
    return [], "none"

def _select_best_quote(philosopher, akim, konu, quotes_list):
    """
    Cok kaynaktan gelen GERCEK sozler arasinda Claude en uygununu SECER.
    Ingilizce ise Turkce'ye cevirir, anlamini degistirmez.
    """
    quotes_text = "\n".join(["  %d. %s" % (i+1, q) for i, q in enumerate(quotes_list)])

    system = """Sen bir felsefe editörüsün. Sana filozofun GERÇEK, doğrulanmış sözleri verilecek.
Görev: Bu listeden konuya EN UYGUN ve EN GÜÇLÜ sözü seç, MUTLAKA Türkçeye çevir, formatla.

KESİN KURALLAR:
1. Listede OLMAYAN hiçbir söz yazma veya uydurma. Sadece verilen listeden seç.
2. Söz hangi dilde olursa olsun (Almanca, İngilizce, Fransızca, Latince vb.) MUTLAKA akıcı Türkçeye çevir.
3. Anlamı DEĞİŞTİRME, sadece çevir.
4. Çeviride Türkçe karakterleri MUTLAKA kullan: ç, ş, ğ, ü, ö, ı, İ, Ğ, Ş, Ç, Ü, Ö
5. SOZ alanında tırnak işareti (", ', «, ») KULLANMA.
6. SOZ alanında Almanca, İngilizce veya başka yabancı dil KULLANMA. Türkçe olmalı.
7. Hashtagleri # ile başlat, Türkçe karakter KULLANMA (o,u,s,c,i,g şeklinde yaz).
8. TWITTER alanında sadece Türkçe söz ve yazar adı olsun, hashtag YAZMA.

Yanıtını TAM OLARAK bu formatta ver:

SOZ:
[Seçilen sözün TÜRKÇE hali — başka dil YASAK, tırnak YOK, max 250 karakter]
---
YAZAR:
[Filozofun adı]
---
AKIM:
[Felsefi akım]
---
HASHTAG:
[5 hashtag — #Felsefe ve #Bilgelik zorunlu, 3 tane daha konuya uygun]
---
ACIKLAMA:
[Sözün 2-3 cümlelik Türkçe açıklaması — felsefi bağlamını anlat]
---
TWITTER:
[Türkçe söz tırnaksız — Yazar Adı]"""

    import time
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=700,
                system=system,
                messages=[{"role": "user", "content": "Dusunur: %s\nAkim: %s\nKonu: %s\n\nGERCEK sozler listesi (bu listeden sec):\n%s" % (philosopher, akim, konu, quotes_text)}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            log.warning("Claude API hatasi (deneme %d/3): %s" % (attempt+1, e))
            if attempt < 2:
                time.sleep(10)

    # Claude basarisiz — fallback ile dogrudan listeden sec (sadece Turkce)
    log.warning("Claude API basarisiz, fallback deneniyor: %s" % philosopher)
    result = _fallback_format(philosopher, akim, quotes_list)
    if result:
        return result
    # Turkce soz bulunamadi — bos don, generate_quote baska filozof dener
    return ""


def _is_turkish(text):
    """Metnin Türkçe olup olmadığını kontrol eder. Almanca/İngilizce sözleri reddeder."""
    if not text:
        return False

    # Türkçe karakterler varsa Türkçe olabilir — ama önce Almanca kontrol et
    # Almanca da ä, ö, ü kullanır — önce Almanca kelimeleri kontrol et
    almanca_kesin = {"der", "die", "das", "des", "dem", "den", "ein", "eine", "einer",
                     "und", "oder", "aber", "nicht", "ist", "sind", "hat", "haben",
                     "wird", "werden", "kann", "muss", "ich", "du", "er", "wir",
                     "von", "zu", "auf", "für", "mit", "durch", "über", "nach",
                     "lässt", "lasst", "böses", "seele", "geist", "mensch", "leben",
                     "wahrheit", "welt", "tod", "weg", "sprache", "missbrauch"}
    words_lower = set(text.lower().split())
    # Almanca kelimeler varsa Türkçe değil
    if len(words_lower & almanca_kesin) >= 2:
        return False

    # Şimdi Türkçe karakter kontrolü
    turkce_chars = set("çşğüöıÇŞĞÜÖİ")
    if any(c in text for c in turkce_chars):
        return True

    # Yaygın Türkçe kelimeler
    turkce_words = {"ve", "bir", "bu", "da", "de", "ile", "için", "ama",
                    "olan", "değil", "gibi", "kadar", "daha", "çok",
                    "her", "biz", "ben", "sen", "var", "yok", "ne",
                    "hayat", "insan", "dünya", "zaman", "gerçek", "akıl",
                    "bilgi", "ölüm", "güzel", "iyi", "kötü", "büyük",
                    "küçük", "yalnız", "mutlu", "özgür", "sevgi"}
    words = set(text.lower().split())
    if len(words & turkce_words) >= 2:
        return True

    # Almanca kelimeleri yakala (reddedilmeli)
    almanca_words = {"der", "die", "das", "des", "dem", "den", "ein", "eine", "einer",
                     "und", "oder", "aber", "nicht", "ist", "sind", "hat", "haben",
                     "wird", "werden", "kann", "muss", "ich", "du", "er", "sie", "wir",
                     "von", "zu", "in", "an", "auf", "für", "mit", "durch", "über",
                     "lässt", "lasst", "böses", "seele", "geist", "mensch", "leben",
                     "wahrheit", "welt", "zeit", "tod", "weg"}
    if len(words & almanca_words) >= 2:
        return False

    # İngilizce kelimeleri yakala (reddedilmeli)
    ingilizce_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                       "have", "has", "had", "do", "does", "did", "will", "would",
                       "can", "could", "should", "may", "might", "must",
                       "and", "or", "but", "not", "in", "on", "at", "to", "for",
                       "of", "with", "by", "from", "that", "this", "it", "he",
                       "she", "we", "they", "you", "i", "my", "your", "his", "her"}
    if len(words & ingilizce_words) >= 3:
        return False

    # Fransızca/Latince kelimeleri yakala
    diger_yabanci = {"les", "des", "une", "est", "sont", "dans", "pour", "avec",
                     "que", "qui", "ce", "se", "ne", "pas", "plus", "très",
                     "la", "le", "les", "du", "et", "ou", "mais",
                     "et", "sed", "non", "est", "sunt", "vel", "aut"}
    if len(words & diger_yabanci) >= 2:
        return False

    return False  # Bilinmeyen dil — reddet


def _fallback_format(philosopher, akim, quotes_list):
    """
    Claude API basarisiz olduğunda listeden Türkçe söz secer ve formatlar.
    İngilizce söz varsa ASLA paylaşmaz — boş döner, başka filozof denenir.
    """
    if not quotes_list:
        return ""

    # Sadece Türkçe sözleri al
    turkce_sozler = [q for q in quotes_list if _is_turkish(q)]

    if not turkce_sozler:
        # Türkçe söz yok — bu filozofu atla, boş dön
        log.warning("Fallback: Turkce soz bulunamadi (%s), atlanıyor." % philosopher)
        return ""

    # En kısa ve temiz Türkçe sözü seç (uzun sözler görsele sığmayabilir)
    turkce_sozler.sort(key=len)
    secim = turkce_sozler[0]
    secim = re.sub(r'[""\u201c\u201d\u2018\u2019«»\']', "", secim).strip()[:250]

    if len(secim) < 15:
        return ""

    akim_tag = re.sub(r"[^a-zA-Z0-9]", "", akim.split("/")[0].strip())
    yt_tag   = re.sub(r"[^a-zA-Z0-9]", "", (philosopher.split()[-1] if philosopher else "Felsefe"))
    hashtags = "#Felsefe #Bilgelik #%s #%s #DusunenInsan" % (akim_tag, yt_tag)

    return """SOZ:\n%s\n---\nYAZAR:\n%s\n---\nAKIM:\n%s\n---\nHASHTAG:\n%s\n---\nACIKLAMA:\n%s'nin felsefi düşüncesinden önemli bir gözlem.\n---\nTWITTER:\n%s — %s""" % (
        secim, philosopher, akim, hashtags, philosopher, secim, philosopher
    )
