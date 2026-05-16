-- dbscript\\table.sql
-- 동적 웹 크롤링에서 여행지 검색 결과 저장용 테이블 생성 스크립트
use mydb;

create table tour (
	`rank` int, 
    name  varchar(100),
    description  varchar(1000),
    category  varchar(100),
    score  decimal(3, 1)
);

desc tour;

select * from tour;
