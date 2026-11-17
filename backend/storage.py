
# backend/storage.py  —— MySQL 版（可直接替换原 SQLite 版）
#
# 对外接口与旧版完全一致：init_db() / save_record(record) / get_history(limit)
# 因此 main.py 中的业务代码无需任何改动。
import os

import pymysql
from pymysql.cursors import DictCursor

# ---------------------------------------------------------------- 连接配置
# 密码等敏感信息一律走环境变量，不要写死在代码里提交到 Git。
# 未设置环境变量时，退回你当前环境的默认值，方便本地直接跑通。
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
    "charset": "utf8mb4",          # 中文 + emoji 必须 utf8mb4，用 utf8 会存不下部分汉字
}
DB_NAME = os.getenv("MYSQL_DATABASE", "word_lab")


def _ensure_database():
    """库不存在时自动创建（对应你说的“当前数据库中没有相对应的表”）。"""
    conn = pymysql.connect(**DB_CONFIG)          # 注意：此时不指定 database
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS `{}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(DB_NAME)
            )
        conn.commit()
    finally:
        conn.close()


def get_conn():
    """等价于旧版的 get_conn()：返回一个连接。
    DictCursor 让查询结果自带列名，替代 sqlite3.Row 的作用。
    """
    cfg = dict(DB_CONFIG)
    cfg["database"] = DB_NAME
    return pymysql.connect(
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=5,
        **cfg
    )


def init_db():
    """建库 + 建表 + 建索引。MySQL 不支持 CREATE INDEX IF NOT EXISTS，
    所以索引必须写在 CREATE TABLE 里面。"""
    _ensure_database()

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    `text`     TEXT            NOT NULL,
                    score      DOUBLE          NULL,
                    `label`    VARCHAR(16)     NULL,
                    pinyin     TEXT            NULL,
                    created_at VARCHAR(32)     NOT NULL,
                    PRIMARY KEY (id),
                    KEY idx_history_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
        conn.commit()
    finally:
        conn.close()


def save_record(record):
    """写入一条分析记录。占位符由 SQLite 的 ? 改为 MySQL 的 %s。"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO history (`text`, score, `label`, pinyin, created_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    record["text"],
                    record["score"],
                    record["label"],
                    record["pinyin"],
                    record["created_at"],
                ),
            )
        conn.commit()          # autocommit=False，必须显式 commit
    finally:
        conn.close()


def get_history(limit):
    """取最近 limit 条，返回 list[dict]，与旧版返回结构一致。"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, `text`, score, `label`, pinyin, created_at "
                "FROM history ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return list(cur.fetchall())      # DictCursor 直接给出 dict，无需 dict(row)
    finally:
        conn.close()