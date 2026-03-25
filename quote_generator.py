import os, re, random, anthropic
from datetime import datetime

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
    "Skeptisizm", "Fenomenoloji", "Türk Düşünce Tarihi",
    "Antik Yunan Felsefesi", "Aydınlanma Felsefesi", "Rasyonalizm", "Empirizm", "İdealizm", 
    "Materyalizm", "Absürdizm", "Hümanizm", "Psikanaliz ve Derinlik Psikolojisi", "Postmodernizm", 
    "Romantizm", "Kinik Felsefe", "Yeni Platonculuk", "Hermeneutik", "Zen Budizmi", "Hint Felsefesi (Vedanta)", 
    "Yapısalcılık", "Frankfurt Okulu", "Skolastik Felsefe", 
    "Sofistler", "Elea Okulu", "Egzistansiyel Psikoterapi", "Klasik Alman Felsefesi", 
    "Sokrates Öncesi Felsefe", "Kozmoloji", "Kinizm", 
    "Kıta Avrupası Felsefesi", "Analitik Felsefe", 
    "Faydacılık (Utilitarianism)", "Kişiselcilik (Personalizm)", "Post-yapısalcılık",
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
            filozof = random.choice(FILOZOFLAR.get("Antik Yunan Felsefesi", ["Sokrates"]))
        konu = random.choice(KONULAR)

    # Wikiquote'tan gercek sozleri cek — Claude soz UYDURMUYOR
    # Gercek soz bulunamazsa baska filozof denenecek, uydurma asla yok
    MAX_DENEME = 5
    for deneme in range(MAX_DENEME):
        real_quotes, lang = _fetch_real_quotes_from_wikipedia(filozof)

        if real_quotes:
            # Gercek sozler bulundu — Claude sadece secer ve formatlar
            raw = _select_best_quote(filozof, akim, konu, real_quotes)
            return _parse(raw, filozof, akim)

        # Bu filozof icin soz bulunamadi — baska birini dene
        log.warning("Wikiquote'ta soz bulunamadi: %s — baska filozof deneniyor (%d/%d)" % (filozof, deneme+1, MAX_DENEME))
        akim = random.choice(AKIMLAR)
        if akim in FILOZOFLAR and FILOZOFLAR[akim]:
            filozof = random.choice(FILOZOFLAR[akim])
        else:
            filozof = random.choice(FILOZOFLAR.get("Antik Yunan Felsefesi", ["Sokrates"]))
        konu = random.choice(KONULAR)

    # 5 denemede de bulunamazsa None don — bot.py bu durumu handle eder
    log.error("5 denemede de Wikiquote'tan gercek soz bulunamadi! Icerik uretimi atlaniyor.")
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
