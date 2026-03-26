# -*- coding: utf-8 -*-
"""
Veritabanı bağlantı modülü — felsefemiz.net
Railway env variables üzerinden bağlanır.
"""
import os, logging, time
import pymysql
import pymysql.cursors

log = logging.getLogger(__name__)

def _get_db_config():
    """DB bağlantı ayarlarını environment variables'dan al."""
    host     = os.environ.get("DB_HOST",     "mt-pony.guzelhosting.com")
    port     = int(os.environ.get("DB_PORT", "3306"))
    user     = os.environ.get("DB_USER",     "sere6176_felsefemizdata")
    password = os.environ.get("DB_PASSWORD", "NeMutluTürkümDiyene@1923")
    dbname   = os.environ.get("DB_NAME",     "sere6176_felsefemizdata")
    return {
        "host":        host,
        "port":        port,
        "user":        user,
        "password":    password,
        "db":          dbname,
        "charset":     "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "connect_timeout": 15,
        "read_timeout":    30,
        "write_timeout":   30,
        "autocommit":  True,
        "ssl_disabled": True,  # cPanel MySQL SSL gerektirmez
    }

DB_CONFIG = _get_db_config()

_conn = None

def get_conn():
    """Bağlantı al — kopuksa yeniden bağlan."""
    global _conn
    try:
        if _conn and _conn.open:
            _conn.ping(reconnect=True)
            return _conn
    except Exception:
        _conn = None
    try:
        cfg = _get_db_config()  # Her bağlantıda env'den taze oku
        _conn = pymysql.connect(**cfg)
        log.info("DB bağlantısı kuruldu: %s@%s/%s" % (
            cfg["user"], cfg["host"], cfg["db"]))
        return _conn
    except pymysql.err.OperationalError as e:
        errno = e.args[0] if e.args else 0
        if errno == 1045:
            log.error("DB Erisim reddedildi (1045) — kullanici/sifre yanlis!")
        elif errno == 2003:
            log.error("DB baglanti zaman asimi (2003) — host/port kontrol edin: %s:%s" % (
                os.environ.get("DB_HOST","?"), os.environ.get("DB_PORT","?")))
        else:
            log.error("DB baglanti hatasi (%s): %s" % (errno, e))
        return None
    except Exception as e:
        log.error("DB beklenmedik hata: %s" % e)
        return None

def query(sql, params=None, fetchone=False):
    """SELECT sorgusu — liste veya tek satır döner."""
    for attempt in range(3):
        conn = get_conn()
        if not conn:
            time.sleep(2)
            continue
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone() if fetchone else cur.fetchall()
        except pymysql.OperationalError:
            _conn = None
            time.sleep(2)
        except Exception as e:
            log.error("DB query hatası: %s | SQL: %s" % (e, sql[:100]))
            return None
    return None

def execute(sql, params=None):
    """INSERT/UPDATE/DELETE — lastrowid döner."""
    for attempt in range(3):
        conn = get_conn()
        if not conn:
            time.sleep(2)
            continue
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.lastrowid
        except pymysql.OperationalError:
            _conn = None
            time.sleep(2)
        except Exception as e:
            log.error("DB execute hatası: %s | SQL: %s" % (e, sql[:100]))
            return None
    return None

def test_connection():
    """Bağlantıyı test et."""
    result = query("SELECT COUNT(*) as c FROM akimlar", fetchone=True)
    if result:
        log.info("DB test OK — akimlar: %d" % result["c"])
        return True
    return False
