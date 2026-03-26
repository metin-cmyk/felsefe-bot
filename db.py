# -*- coding: utf-8 -*-
"""
Veritabanı bağlantı modülü — felsefemiz.net
Railway env variables üzerinden bağlanır.
"""
import os, logging, time
import pymysql
import pymysql.cursors

log = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "port":     int(os.environ.get("DB_PORT", "3306")),
    "user":     os.environ.get("DB_USER",     "sere6176_felsefemizdata"),
    "password": os.environ.get("DB_PASSWORD", "NeMutluTürkümDiyene@1923"),
    "db":       os.environ.get("DB_NAME",     "sere6176_felsefemizdata"),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 10,
    "autocommit": True,
}

_conn = None

def get_conn():
    """Bağlantı al — kopuksa yeniden bağlan."""
    global _conn
    try:
        if _conn and _conn.open:
            _conn.ping(reconnect=True)
            return _conn
    except Exception:
        pass
    try:
        _conn = pymysql.connect(**DB_CONFIG)
        log.info("DB bağlantısı kuruldu.")
        return _conn
    except Exception as e:
        log.error("DB bağlantı hatası: %s" % e)
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
