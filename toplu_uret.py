# -*- coding: utf-8 -*-
"""
Toplu söz üretim scripti — felsefemiz.net
Railway'de çalıştırılabilir: python toplu_uret.py 50
Wikiquote'tan söz çeker, Türkçeye çevirir, DB'ye kaydeder.
"""
import sys, os, random, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

try:
    from db import query as db_query, execute as db_execute, test_connection
    DB_AVAILABLE = True
except ImportError:
    log.error("db.py bulunamadi!")
    sys.exit(1)

# quote_generator'dan fonksiyonları al
from quote_generator import (
    _fetch_real_quotes_from_wikipedia,
    _select_best_quote,
    _parse,
    _is_turkish,
    _get_akimlar,
    _get_random_filozof,
    _get_random_konu,
    _db_save_quote,
)

def uret(hedef=50):
    """DB'ye hedef kadar yeni Türkçe söz üret ve kaydet."""
    if not test_connection():
        log.error("DB bağlantısı yok!")
        return

    # Mevcut söz sayısı
    mevcut = db_query("SELECT COUNT(*) as c FROM sozler WHERE dil='tr' AND dogrulanmis=1 AND filozof_ad != 'Mustafa Kemal Atatürk'", fetchone=True)
    log.info("Mevcut Türkçe söz sayısı: %d" % (mevcut["c"] if mevcut else 0))
    log.info("Hedef: %d yeni söz üretilecek" % hedef)

    akimlar_list = _get_akimlar()
    basarili = 0
    deneme   = 0
    max_deneme = hedef * 5  # Fazla deneme hakkı

    while basarili < hedef and deneme < max_deneme:
        deneme += 1
        akim    = random.choice(akimlar_list)
        filozof = _get_random_filozof(akim)
        konu    = _get_random_konu()

        # Bu filozoftan DB'de zaten çok söz var mı?
        count = db_query(
            "SELECT COUNT(*) as c FROM sozler WHERE filozof_ad = %s", (filozof,), fetchone=True
        )
        if count and count["c"] >= 5:
            log.info("Atlandı (zaten %d söz var): %s" % (count["c"], filozof))
            continue

        log.info("[%d/%d] Çekiliyor: %s (%s)" % (basarili+1, hedef, filozof, akim))

        real_quotes, lang = _fetch_real_quotes_from_wikipedia(filozof)
        if not real_quotes:
            log.warning("Wikiquote'ta söz yok: %s" % filozof)
            continue

        raw    = _select_best_quote(filozof, akim, konu, real_quotes)
        result = _parse(raw, filozof, akim)

        if not result or not result.get("quote"):
            log.warning("Parse başarısız: %s" % filozof)
            continue

        if not _is_turkish(result["quote"]):
            log.warning("Türkçe değil, atlandı: %s" % result["quote"][:50])
            continue

        # DB'de aynı söz var mı?
        mevcut_soz = db_query(
            "SELECT id FROM sozler WHERE filozof_ad=%s AND LEFT(soz,60)=%s",
            (result["author"], result["quote"][:60]),
            fetchone=True
        )
        if mevcut_soz:
            log.info("Zaten var: %s" % result["quote"][:40])
            continue

        _db_save_quote(result)
        basarili += 1
        log.info("✅ Kaydedildi [%d/%d]: %s — %s" % (basarili, hedef, result["author"], result["quote"][:50]))

    log.info("=" * 50)
    log.info("Tamamlandı: %d/%d söz üretildi (%d deneme)" % (basarili, hedef, deneme))

    # Güncel durum
    toplam = db_query("SELECT COUNT(*) as c FROM sozler WHERE dil='tr'", fetchone=True)
    log.info("DB'deki toplam Türkçe söz: %d" % (toplam["c"] if toplam else 0))

if __name__ == "__main__":
    hedef = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    uret(hedef)
