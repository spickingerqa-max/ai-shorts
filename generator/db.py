import os
import time
import json
import pymysql


def get_connection():
    for attempt in range(1, 11):
        try:
            conn = pymysql.connect(
                host=os.getenv('MYSQL_HOST', 'mysql'),
                user=os.getenv('MYSQL_USER', 'shorts'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('MYSQL_DATABASE', 'shortsdb'),
                charset='utf8mb4',
            )
            print(f"[DB] MySQL 연결 성공 (시도 {attempt}회)")
            return conn
        except pymysql.Error as e:
            print(f"[DB] MySQL 연결 실패 ({attempt}/10): {e}")
            if attempt < 10:
                time.sleep(5)
    raise RuntimeError("[DB] MySQL 연결 실패 — 10회 재시도 초과")


def get_recent_titles(limit=20):
    """최근 생성된 제목 목록 반환 (중복 방지용)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT title FROM shorts ORDER BY id DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            return [r[0] for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def save_short(title, genre, hook, hashtags, filename, file_size_mb):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO shorts (title, genre, hook, hashtags, filename, file_size_mb, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'done')
            """
            cursor.execute(sql, (
                title,
                genre,
                hook,
                json.dumps(hashtags, ensure_ascii=False),
                filename,
                file_size_mb,
            ))
        conn.commit()
        print(f"[DB] 저장 완료: {title} ({genre})")
    finally:
        conn.close()
