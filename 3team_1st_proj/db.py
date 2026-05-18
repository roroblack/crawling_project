# 운영체제 환경변수 값을 읽기 위해 os 모듈을 가져온다.
# 예: DB_HOST, DB_USER, DB_PASSWORD 같은 값을 읽을 때 사용한다.
import os
from datetime import datetime

# .env 파일에 작성된 설정값을 파이썬 환경변수로 불러오기 위해 사용한다.
# .env 파일에는 DB 접속 정보처럼 코드에 직접 쓰기 부담스러운 값을 저장한다.
from dotenv import load_dotenv

# create_engine은 SQLAlchemy에서 DB 연결 엔진을 만드는 함수이다.
# text는 문자열 SQL문을 SQLAlchemy가 실행 가능한 SQL 객체로 변환할 때 사용한다.
from sqlalchemy import create_engine, text


# 현재 프로젝트 폴더의 .env 파일을 읽어온다.
# 이 코드를 실행해야 os.getenv("DB_HOST")처럼 .env 값을 가져올 수 있다.
load_dotenv()


# MySQL 데이터베이스 연결 엔진을 생성하는 함수이다.
# 다른 파일에서 get_engine()을 호출하면 MySQL에 연결할 수 있는 객체를 받을 수 있다.
def get_engine():
    # .env 파일에서 DB_HOST 값을 읽는다.
    # 값이 없으면 기본값으로 "localhost"를 사용한다.
    # localhost는 현재 내 컴퓨터를 의미한다.
    host = os.getenv("DB_HOST", "localhost")

    # .env 파일에서 DB_PORT 값을 읽는다.
    # 값이 없으면 MySQL 기본 포트인 "3306"을 사용한다.
    port = os.getenv("DB_PORT", "3306")

    # .env 파일에서 DB_USER 값을 읽는다.
    # 값이 없으면 기본값으로 "student"를 사용한다.
    user = os.getenv("DB_USER", "student")

    # .env 파일에서 DB_PASSWORD 값을 읽는다.
    # 값이 없으면 기본값으로 "Student80*"를 사용한다.
    password = os.getenv("DB_PASSWORD", "Student80*")

    # .env 파일에서 DB_NAME 값을 읽는다.
    # 값이 없으면 기본값으로 "mydb"를 사용한다.
    db_name = os.getenv("DB_NAME", "mydb")

    # SQLAlchemy가 MySQL에 접속하기 위한 DB URL을 만든다.
    #
    # 형식:
    # mysql+pymysql://사용자명:비밀번호@호스트:포트/DB명?charset=utf8mb4
    #
    # mysql+pymysql:
    #   MySQL DB에 pymysql 드라이버를 사용해서 접속한다는 뜻이다.
    #
    # charset=utf8mb4:
    #   한글, 이모지, 특수문자까지 안정적으로 저장하기 위한 문자셋 설정이다.
    db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4"

    # create_engine()은 DB 연결을 관리하는 엔진 객체를 만든다.
    #
    # pool_pre_ping=True:
    #   DB 연결을 사용하기 전에 연결이 살아 있는지 확인한다.
    #   오래된 연결이 끊겨서 발생하는 오류를 줄일 수 있다.
    return create_engine(db_url, pool_pre_ping=True)


# 17개 시도 이름 (DB seed · 크롤러 · 앱 공통 사용)
REGIONS: list[str] = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]
# UI 표시 순서 — 전국을 맨 앞에 추가
REGION_ORDER: list[str] = ["전국"] + REGIONS


# 크롤링 데이터를 저장할 테이블을 생성하는 함수이다.
# 앱 실행 시 한 번 호출하면, 테이블이 없을 경우 자동으로 생성된다.
#
# 생성 순서 (FK 제약 때문에 regions를 먼저 만든다):
#   차원 테이블: regions
#   팩트 테이블: car_registrations, hydrogen_charging_station (regions FK)
#   독립 엔티티: faq, crawl_news
def init_table():
    engine = get_engine()

    sqls = [
        # ── 차원 테이블 ──────────────────────────────────────────
        # 시도 지역 테이블 (서울 ~ 제주 17개 시도 + 전국, 총 18개)
        """
        CREATE TABLE IF NOT EXISTS regions (
            region_id   SMALLINT    AUTO_INCREMENT PRIMARY KEY,
            region_name VARCHAR(20) NOT NULL UNIQUE
        )
        """,
        # ── 팩트 테이블 ──────────────────────────────────────────
        # 수소차 등록 현황 — 지역별 연도별 누적 등록 대수
        """
        CREATE TABLE IF NOT EXISTS car_registrations (
            id        BIGINT   AUTO_INCREMENT PRIMARY KEY,
            region_id SMALLINT NOT NULL,
            stat_year SMALLINT NOT NULL,
            count     INT      NOT NULL DEFAULT 0,
            FOREIGN KEY (region_id) REFERENCES regions(region_id),
            UNIQUE KEY uq_stat (region_id, stat_year)
        )
        """,
        # 수소 충전소 — 공공데이터 포털 CSV에서 적재
        # lat/lon 있어야 folium 지도 마커 표시 가능
        """
        CREATE TABLE IF NOT EXISTS hydrogen_charging_station (
            id           INT            AUTO_INCREMENT PRIMARY KEY,
            region_id    SMALLINT       NOT NULL,
            station_name VARCHAR(100)   NOT NULL,
            address      VARCHAR(255),
            lat          DECIMAL(10, 7),
            lon          DECIMAL(10, 7),
            FOREIGN KEY (region_id) REFERENCES regions(region_id)
        )
        """,
        # ── 독립 엔티티 ──────────────────────────────────────────
        # FAQ
        """
        CREATE TABLE IF NOT EXISTS faq (
            faq_id   INT  AUTO_INCREMENT PRIMARY KEY,
            question TEXT NOT NULL,
            answer   TEXT
        )
        """,
        # ── 메타 테이블 ──────────────────────────────────────────
        # 크롤 대상별 수집 상태/메타 (크롤러/API/수동업로드 공통)
        # source_code는 CHECK 제약으로 닫힌 도메인을 강제한다 (ENUM 대신).
        """
        CREATE TABLE IF NOT EXISTS crawl_stat (
            crawl_id        INT         AUTO_INCREMENT PRIMARY KEY,
            target_type     VARCHAR(30) NOT NULL,
            last_crawled_at DATETIME    NULL,
            CONSTRAINT chk_target_type
                CHECK (target_type IN ('car_registration','station','faq'))
        )
        """,
    ]

    # engine.begin()은 트랜잭션을 시작한다.
    # 모든 테이블 생성이 완료되면 자동 commit, 오류 시 rollback 처리된다.
    with engine.begin() as conn:
        for sql in sqls:
            conn.execute(text(sql))

        # regions 기초 데이터 삽입 (처음 한 번만, 중복 무시)
        for name in REGIONS:
            conn.execute(
                text("INSERT IGNORE INTO regions (region_name) VALUES (:name)"),
                {"name": name},
            )

        # crawl_stat 기초 레코드 삽입 (대상별 1행)
        for t in ("car_registration", "station", "faq"):
            conn.execute(
                text("INSERT IGNORE INTO crawl_stat (target_type) VALUES (:t)"),
                {"t": t},
            )




# ── 데이터 조회 함수 ────────────────────────────────────────────
# app_preview.py 등 UI 레이어에서 SQL 없이 데이터를 가져올 수 있도록 제공한다.
# SQL 쿼리는 모두 이 파일(db.py)에서만 작성한다.

import pandas as pd   # 쿼리 결과를 DataFrame으로 반환하기 위해 사용한다.


def fetch_registrations() -> pd.DataFrame:
    """car_registrations + regions JOIN → (region_name, stat_year, count) DataFrame 반환"""
    engine = get_engine()
    sql = """
        SELECT r.region_name, cr.stat_year, cr.count
        FROM car_registrations cr
        JOIN regions r ON cr.region_id = r.region_id
        ORDER BY cr.stat_year, r.region_id
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def fetch_stations() -> pd.DataFrame:
    """hydrogen_charging_station + regions JOIN → (station_name, address, lat, lon, region_name) DataFrame 반환.
    lat/lon 이 NULL 인 행은 지도 마커를 그릴 수 없으므로 제외한다."""
    engine = get_engine()
    sql = """
        SELECT h.station_name, h.address, h.lat, h.lon, r.region_name
        FROM hydrogen_charging_station h
        JOIN regions r ON h.region_id = r.region_id
        WHERE h.lat IS NOT NULL AND h.lon IS NOT NULL
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def fetch_faqs() -> list[tuple[str, str]]:
    """faq 테이블 전체를 (question, answer) 튜플 리스트로 반환한다.
    테이블이 비어 있으면 빈 리스트를 반환한다."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT question, answer FROM faq ORDER BY faq_id")
        ).fetchall()
    return [(r[0], r[1] or "") for r in rows]


def fetch_car_last_crawled() -> datetime | None:
    """crawl_stat의 car_registration 행에서 last_crawled_at(마지막 수집 시각)을 반환한다.
    기록이 없으면 None 반환."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT last_crawled_at FROM crawl_stat WHERE target_type = 'car_registration'")
        ).fetchone()
    if row and row[0]:
        return row[0] if isinstance(row[0], datetime) else datetime.fromisoformat(str(row[0]))
    return None


def fetch_faq_last_crawled() -> datetime | None:
    """crawl_stat의 faq 행에서 last_crawled_at(마지막 수집 시각)을 반환한다.
    기록이 없으면 None 반환."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT last_crawled_at FROM crawl_stat WHERE target_type = 'faq'")
        ).fetchone()
    if row and row[0]:
        return row[0] if isinstance(row[0], datetime) else datetime.fromisoformat(str(row[0]))
    return None


def save_faqs(items) -> int:
    """FaqItem 목록을 faq 테이블에 저장하고
    crawl_stat 의 last_crawled_at 을 현재 시각으로 갱신한다.

    기존 faq 데이터를 삭제한 후 items 를 새로 삽입한다.
    저장된 레코드 수를 반환한다."""
    engine = get_engine()
    with engine.begin() as conn:
        # 기존 FAQ 전체 삭제 (최신 크롤링 결과로 교체)
        conn.execute(text("DELETE FROM faq"))

        for item in items:
            conn.execute(text("""
                INSERT INTO faq (question, answer)
                VALUES (:q, :a)
            """), {"q": item.question, "a": item.answer or ""})

        # crawl_stat 갱신: 마지막 수집 시각
        conn.execute(text("""
            UPDATE crawl_stat
            SET last_crawled_at = NOW()
            WHERE target_type = 'faq'
        """))

    return len(items)


def save_car_registrations(items) -> int:
    """CarRegistrationItem 목록을 car_registrations에 UPSERT 저장하고
    crawl_stat의 last_crawled_at을 현재 시각으로 갱신한다.
    저장된 레코드 수를 반환."""
    engine = get_engine()
    with engine.begin() as conn:
        # 지역명 → region_id 매핑
        rows   = conn.execute(text("SELECT region_id, region_name FROM regions")).fetchall()
        rid_map = {r[1]: r[0] for r in rows}

        saved = 0
        for item in items:
            rid = rid_map.get(item.region)
            if rid is None:
                continue
            conn.execute(text("""
                INSERT INTO car_registrations (region_id, stat_year, count)
                VALUES (:rid, :year, :cnt)
                ON DUPLICATE KEY UPDATE count = VALUES(count)
            """), {"rid": rid, "year": item.stat_year, "cnt": item.count})
            saved += 1

        # crawl_stat 갱신: 마지막 수집 시각
        conn.execute(text("""
            UPDATE crawl_stat
            SET last_crawled_at = NOW()
            WHERE target_type = 'car_registration'
        """))

    return saved