# -*- coding: utf-8 -*-
"""Veritabanı bağlantı modülü — felsefemiz.net"""
import os, logging, time
import pymysql, pymysql.cursors

log = logging.getLogger(__name__)

_conn = None

def _cfg():
    return {
        "host":        os.environ.get("DB_HOST", "mt-pony.guzelhosting.com"),
        "port":        int(os.environ.get("DB_PORT", "3306")),
        "user":        os.environ.get("DB_USER", "sere6176_felsefemizdata"),
        "password":    os.environ.get("DB_PASSWORD", ""),
        "db":          os.environ.get("DB_NAME", "sere6176_felsefemizdata"),
        "charset":     "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "connect_timeout": 15,
        "autocommit":  True,
    }

def get_conn():
    global _conn
    try:
        if _conn and _conn.open:
            _conn.ping(reconnect=True)
            return _conn
    except Exception:
        _conn = None
    try:
        _conn = pymysql.connect(**_cfg())
        log.info("DB baglantisi kuruldu.")
        return _conn
    except Exception as e:
        log.error("DB baglanti hatasi: %s" % e)
        return None

def query(sql, params=None, fetchone=False):
    for _ in range(3):
        conn = get_conn()
        if not conn:
            time.sleep(2)
            continue
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone() if fetchone else cur.fetchall()
        except pymysql.OperationalError:
            global _conn
            _conn = None
            time.sleep(2)
        except Exception as e:
            log.error("DB query hatasi: %s" % e)
            return None
    return None

def execute(sql, params=None):
    for _ in range(3):
        conn = get_conn()
        if not conn:
            time.sleep(2)
            continue
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.lastrowid
        except pymysql.OperationalError:
            global _conn
            _conn = None
            time.sleep(2)
        except Exception as e:
            log.error("DB execute hatasi: %s" % e)
            return None
    return None

def test_connection():
    r = query("SELECT COUNT(*) as c FROM akimlar", fetchone=True)
    if r:
        log.info("DB test OK — akimlar: %d" % r["c"])
        return True
    return False
