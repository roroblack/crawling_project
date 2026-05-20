-- =========================================================
-- 자동차 등록 현황 조회 시스템 DB 스키마
--
-- 테이블 목록:
--   1. regions                  ← 시도 지역 (FK 대상, 먼저 생성)
--   2. car_registrations        ← 수소차 등록 현황 (regions FK)
--   3. hydrogen_charging_station← 수소 충전소 (regions FK)
--   4. faq                      ← FAQ 독립 엔티티
--   5. faq                      ← FAQ 독립 엔티티
-- =========================================================

CREATE DATABASE IF NOT EXISTS crawler_db
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE crawler_db;


-- ─── 1. 차원 테이블 ──────────────────────────────────────────

-- 시도 지역 테이블 (서울 ~ 제주 17개 시도 + 전국 합계, 총 18개)
-- region_id는 AUTO_INCREMENT로 자동 부여
CREATE TABLE IF NOT EXISTS regions (
    region_id   SMALLINT    AUTO_INCREMENT PRIMARY KEY,
    region_name VARCHAR(20) NOT NULL UNIQUE   -- '서울', '부산', ... '전국'
);


-- ─── 2. 팩트 테이블 ──────────────────────────────────────────

-- 수소차 등록 현황 (국토교통부 통계누리 stat.molit.go.kr)
-- 지역별 연도별 수소차 누적 등록 대수를 저장한다.
-- FK 관계: regions(1) ──< car_registrations(N)
CREATE TABLE IF NOT EXISTS car_registrations (
    id        BIGINT   AUTO_INCREMENT PRIMARY KEY,
    region_id SMALLINT NOT NULL,
    stat_year SMALLINT NOT NULL,
    count     INT      NOT NULL DEFAULT 0,
    FOREIGN KEY (region_id) REFERENCES regions(region_id),
    UNIQUE KEY uq_stat (region_id, stat_year)
);


-- ─── 3. 독립 엔티티 ──────────────────────────────────────────

-- 수소 충전소 (공공데이터 포털 CSV → DB 적재)
-- lat/lon: 지도 마커 표시에 필수
-- FK 관계: regions(1) ──< hydrogen_charging_station(N)
CREATE TABLE IF NOT EXISTS hydrogen_charging_station (
    id           INT            AUTO_INCREMENT PRIMARY KEY,
    region_id    SMALLINT       NOT NULL,
    station_name VARCHAR(100)   NOT NULL,
    address      VARCHAR(255),
    lat          DECIMAL(10, 7),    -- 위도
    lon          DECIMAL(10, 7),    -- 경도
    crawled_at   DATETIME       NOT NULL,  -- 크롤링 시각
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);

-- 이미 테이블이 생성된 경우 crawled_at 컬럼 추가 (최초 1회 실행)
-- ALTER TABLE hydrogen_charging_station ADD COLUMN crawled_at DATETIME NOT NULL DEFAULT NOW();

-- FAQ
CREATE TABLE IF NOT EXISTS faq (
    faq_id   INT  AUTO_INCREMENT PRIMARY KEY,
    question TEXT NOT NULL,
    answer   TEXT
);

-- ─── 초기화 쿼리 (필요 시 주석 해제) ────────────────────────
-- TRUNCATE TABLE car_registrations;
-- TRUNCATE TABLE hydrogen_charging_station;
-- TRUNCATE TABLE regions;
-- TRUNCATE TABLE faq;