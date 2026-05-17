-- =========================================================
-- 자동차 등록 현황 조회 시스템 DB 스키마
--
-- 테이블 목록:
--   1. regions                   ← 시도 지역 (차원)
--   2. car_registrations         ← 수소차 등록 현황 (regions FK)
--   3. hydrogen_charging_station ← 수소 충전소 (regions FK)
--   4. faq                       ← FAQ (독립 엔티티)
--   5. crawl_stat                ← 크롤 대상별 수집 상태/메타
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
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);

-- FAQ
CREATE TABLE IF NOT EXISTS faq (
    faq_id   INT  AUTO_INCREMENT PRIMARY KEY,
    question TEXT NOT NULL,
    answer   TEXT
);


-- ─── 4. 메타 테이블 ───────────────────────────────────

-- 크롤 대상별 수집 상태 (크롤러/API/수동업로드 공통)
-- source_code는 CHECK 제약으로 닫힌 도메인을 강제한다 (ENUM 대신).
CREATE TABLE IF NOT EXISTS crawl_stat (
    crawl_id        INT         AUTO_INCREMENT PRIMARY KEY,
    target_type     VARCHAR(30) NOT NULL,
    last_crawled_at DATETIME    NULL,              -- 마지막 수집 완료 시각
    CONSTRAINT chk_target_type
        CHECK (target_type IN ('car_registration','station','faq'))
);

-- ─── 초기화 쿼리 (필요 시 주석 해제) ────────────────────────
-- TRUNCATE TABLE car_registrations;
-- TRUNCATE TABLE hydrogen_charging_station;
-- TRUNCATE TABLE regions;
-- TRUNCATE TABLE faq;-- TRUNCATE TABLE crawl_stat;

-- ─── data_sources 초기 레코드 ──────────────────────────────
INSERT IGNORE INTO crawl_stat (target_type) VALUES
    ('car_registration'),
    ('station'),
    ('faq');