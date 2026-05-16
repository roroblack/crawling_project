# MySQL 조회 결과를 DataFrame으로 처리하기 위해 pandas를 가져온다.
import pandas as pd

# APScheduler의 백그라운드 스케줄러를 가져온다.
# BackgroundScheduler는 프로그램이 실행되는 동안 백그라운드에서 작업을 예약 실행한다.
from apscheduler.schedulers.background import BackgroundScheduler

# SQLAlchemy에서 SQL문을 안전하게 실행하기 위해 text를 가져온다.
from sqlalchemy import text

# crawler.py에 작성된 네이버 뉴스 크롤러 클래스를 가져온다.
from crawler import NaverNewsCrawler

# db.py에 작성된 get_engine 함수를 가져온다.
# get_engine()은 MySQL 연결 객체를 만든다.
from db import get_engine


# 크롤링 실행, MySQL 저장, MySQL 조회를 담당하는 서비스 클래스이다.
class CrawlService:
    # 객체가 생성될 때 실행되는 생성자이다.
    def __init__(self):
        # MySQL 연결 엔진을 생성한다.
        self.engine = get_engine()

        # 네이버 뉴스 크롤러 객체를 생성한다.
        self.crawler = NaverNewsCrawler()

    # 크롤링을 실행하고 결과를 MySQL에 저장하는 메서드이다.
    # limit은 수집할 데이터 개수이다.
    def run_crawling(self, limit: int = 30) -> int:
        # 크롤러를 실행해서 CrawlItem 리스트를 가져온다.
        items = self.crawler.crawl(limit=limit)

        # MySQL에 데이터를 저장하기 위한 INSERT SQL문이다.
        # :title, :link 같은 부분은 SQLAlchemy의 바인딩 변수이다.
        # 직접 문자열을 붙이는 방식보다 SQL Injection 위험이 낮다.
        sql = """
        INSERT INTO crawl_news
        (
            title,
            link,
            source_url,
            crawled_at
        )
        VALUES
        (
            :title,
            :link,
            :source_url,
            :crawled_at
        )
        """

        # self.engine.begin()은 DB 트랜잭션을 시작한다.
        # with 구문이 정상 종료되면 commit,
        # 오류가 발생하면 rollback된다.
        with self.engine.begin() as conn:
            # 크롤링된 아이템을 하나씩 DB에 저장한다.
            for item in items:
                # SQL문 실행
                conn.execute(
                    # 문자열 SQL을 SQLAlchemy 실행 객체로 변환
                    text(sql),

                    # SQL의 바인딩 변수에 실제 값을 전달한다.
                    {
                        "title": item.title,
                        "link": item.link,
                        "source_url": item.source_url,
                        "crawled_at": item.crawled_at,
                    }
                )

        # 저장한 데이터 개수를 반환한다.
        return len(items)

    # MySQL에 저장된 전체 크롤링 데이터를 조회하는 메서드이다.
    def find_all(self) -> pd.DataFrame:
        # crawl_news 테이블에서 데이터를 조회하는 SQL이다.
        # 최근 수집 데이터가 위에 나오도록 crawled_at DESC, id DESC로 정렬한다.
        sql = """
        SELECT
            id,
            title,
            link,
            source_url,
            crawled_at
        FROM crawl_news
        ORDER BY crawled_at DESC, id DESC
        """

        # SQL 실행 결과를 pandas DataFrame으로 반환한다.
        return pd.read_sql(sql, self.engine)

    # 크롤링 시간별 수집 건수를 조회하는 메서드이다.
    # 시각화 그래프에서 사용된다.
    def find_count_by_time(self) -> pd.DataFrame:
        # MySQL의 DATE_FORMAT 함수를 사용하여 crawled_at을 분 단위 문자열로 변환한다.
        # 주의: pandas.read_sql과 pymysql 조합에서는 % 기호가 파이썬 포맷 문자로 해석될 수 있다.
        # 그래서 MySQL 포맷 문자 %Y, %m, %d 등을 %%Y, %%m, %%d처럼 두 번 써야 한다.
        sql = """
        SELECT
            DATE_FORMAT(crawled_at, '%%Y-%%m-%%d %%H:%%i') AS crawl_time,
            COUNT(*) AS count
        FROM crawl_news
        GROUP BY DATE_FORMAT(crawled_at, '%%Y-%%m-%%d %%H:%%i')
        ORDER BY crawl_time
        """

        # 시간별 수집 건수 결과를 DataFrame으로 반환한다.
        return pd.read_sql(sql, self.engine)


# APScheduler 작업 등록, 시작, 삭제, 조회를 담당하는 클래스이다.
class SchedulerManager:
    # 객체 생성 시 실행되는 생성자이다.
    def __init__(self):
        # 백그라운드 스케줄러 객체를 생성한다.
        self.scheduler = BackgroundScheduler()

        # 스케줄러가 실행할 크롤링 서비스 객체를 생성한다.
        self.service = CrawlService()

    # 스케줄러를 시작하는 메서드이다.
    def start(self):
        # 스케줄러가 이미 실행 중인지 확인한다.
        # 실행 중이 아니면 시작한다.
        if not self.scheduler.running:
            self.scheduler.start()

    # interval 방식의 자동 실행 작업을 등록한다.
    # 예: 10분마다 크롤링 실행
    def add_interval_job(self, minutes: int, limit: int):
        # 기존에 등록된 작업이 있으면 먼저 삭제한다.
        # 이렇게 하면 같은 작업이 중복 등록되지 않는다.
        self.remove_job()

        # APScheduler에 작업을 등록한다.
        self.scheduler.add_job(
            # 실행할 함수
            func=self.service.run_crawling,

            # interval 방식: 일정 간격으로 반복 실행
            trigger="interval",

            # 몇 분마다 실행할지 지정
            minutes=minutes,

            # run_crawling 함수에 전달할 인자
            # run_crawling(limit) 형태로 실행된다.
            args=[limit],

            # 작업 ID
            # 나중에 삭제하거나 조회할 때 사용한다.
            id="auto_crawling_job",

            # 같은 ID의 작업이 있으면 교체한다.
            replace_existing=True
        )

    # cron 방식의 자동 실행 작업을 등록한다.
    # 예: 매일 9시 0분에 크롤링 실행
    def add_cron_job(self, hour: int, minute: int, limit: int):
        # 기존 작업이 있으면 먼저 삭제한다.
        self.remove_job()

        # APScheduler에 cron 작업을 등록한다.
        self.scheduler.add_job(
            # 실행할 함수
            func=self.service.run_crawling,

            # cron 방식: 특정 시각에 실행
            trigger="cron",

            # 실행할 시
            hour=hour,

            # 실행할 분
            minute=minute,

            # run_crawling 함수에 전달할 인자
            args=[limit],

            # 작업 ID
            id="auto_crawling_job",

            # 같은 ID 작업이 있으면 교체
            replace_existing=True
        )

    # 등록된 자동 크롤링 작업을 삭제하는 메서드이다.
    def remove_job(self):
        # auto_crawling_job이라는 ID의 작업을 찾는다.
        job = self.scheduler.get_job("auto_crawling_job")

        # 해당 작업이 존재하면 삭제한다.
        if job:
            self.scheduler.remove_job("auto_crawling_job")

    # 현재 등록된 모든 스케줄 작업을 반환한다.
    def get_jobs(self):
        return self.scheduler.get_jobs()