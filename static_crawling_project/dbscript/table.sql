create table movie (	
	`rank`  int,    -- rank 는 예약어임. 빽틱 사용하면 컬럼명으로 사용할 수 있음
    title varchar(100),
    star_point decimal(5, 2),
    release_date  datetime,
    genre varchar(100),
    link varchar(2000)
);

desc movie;

select * from movie;
