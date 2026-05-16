-- root 계정에서 실행

CREATE DATABASE crawler_db
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;


-- 프로젝트가 사용할 user 계정과 암호 만들기
-- 사용자 계정에 권한 설정

-- 사용자가 계정에 접속함 ------------------------
USE crawler_db;

CREATE TABLE crawl_news (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    link TEXT,
    source_url TEXT,
    crawled_at DATETIME NOT NULL
);

desc crawl_news;

select * from crawl_news;

-- 테이블 데이터 전체 삭제 (초기화)
TRUNCATE TABLE crawl_news;