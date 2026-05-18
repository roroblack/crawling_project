import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

from data.repository import Repository
from common.constants import ALLOWED_MODELS

# 테스트용
from model.models import FaqItem
from datetime import datetime

# 크롤러와 DB를 연결하는 서비스 클래스이다.
class CrawlService:
    def __init__(self):
        # 크롤러 클래스 작성 후 변경
        # self.crawler = Crawler()

        self.repository = Repository()

    # 크롤러를 실행하고 가져온 아이템들을 DB에 저장하는 함수이다.
    def crawl_and_save(self):
        # 크롤러를 실행하여 아이템 리스트를 가져온다.
        # 크롤러 클래스 작성 후 변경
        # items = self.crawler.crawl()

        # 테스트용 아이템 리스트
        items = [FaqItem('Question1', 'Answer1', datetime.now()),
                 FaqItem('Question2', 'Answer2', datetime.now()),
                 FaqItem('Question3', 'Answer3', datetime.now())]

        # 아이템 리스트를 DB에 저장한다.
        self.repository.save_items(items)


# 스케줄러를 관리하는 클래스이다.
class SchedulerService:
    def __init__(self):
        # 백그라운드 스케줄러 객체를 만든다.
        self.scheduler = BackgroundScheduler()

        # 스케줄러가 실행할 크롤링 서비스 객체를 만든다.
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
            func=self.service.crawl_and_save,

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
            func=self.service.crawl_and_save,

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