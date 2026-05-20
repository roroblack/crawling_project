# 운영체제 환경변수 값을 읽기 위해 os 모듈을 가져온다.
import os

# 현재 날짜와 시간을 저장하기 위해 datetime을 가져온다.
from datetime import datetime

# 상대 URL을 절대 URL로 변환하기 위해 urljoin을 가져온다.
from urllib.parse import urljoin

# HTML 문서를 분석하기 위해 BeautifulSoup을 가져온다.
from bs4 import BeautifulSoup

# .env 파일에 저장된 환경변수를 읽기 위해 load_dotenv를 가져온다.
from dotenv import load_dotenv

# Playwright 비동기 API를 사용한다.
from playwright.async_api import async_playwright

# Streamlit 환경에서 asyncio 이벤트 루프를 별도 스레드에서 실행하기 위해 가져온다.
from concurrent.futures import ThreadPoolExecutor

# models.py에 정의된 CrawlItem 데이터 클래스를 가져온다.
from models import CrawlItem


# .env 파일을 읽어서 os.getenv()로 사용할 수 있게 한다.
load_dotenv()


# 네이버 뉴스 데이터를 크롤링하는 클래스이다.
class NaverNewsCrawler:
    # 객체가 생성될 때 자동으로 실행되는 생성자이다.
    def __init__(self):
        # .env 파일의 CRAWL_URL 값을 읽어온다.
        # 만약 CRAWL_URL 값이 없으면 기본값으로 https://news.naver.com/ 사용
        self.url = os.getenv("CRAWL_URL", "https://news.naver.com/")

    # 외부에서 호출하는 대표 크롤링 메서드이다.
    # limit은 최대 몇 개의 데이터를 수집할지 지정한다.
    def crawl(self, limit: int = 30) -> list[CrawlItem]:
        # 웹페이지 HTML을 가져온다.
        html = self._get_html()

        # 가져온 HTML에서 필요한 데이터를 추출한다.
        return self._parse(html, limit)

    # 실제 브라우저를 실행해서 HTML을 가져오는 내부 메서드이다.
    # 메서드 이름 앞의 _는 내부에서 사용하는 함수라는 의미로 자주 사용된다.
    def _get_html(self) -> str:
        # Streamlit은 asyncio 이벤트 루프를 사용하기 때문에
        # sync_playwright를 직접 호출하면 Windows에서 NotImplementedError가 발생한다.
        # 별도의 스레드에서 실행하면 이 문제를 피할 수 있다.
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_playwright)
            return future.result()

    def _run_playwright(self) -> str:
        # Windows에서 subprocess를 지원하는 ProactorEventLoop을 명시적으로 생성하여
        # 그 위에서 async_playwright를 실행한다.
        # sync_playwright는 내부적으로 asyncio.new_event_loop()를 사용하기 때문에
        # Streamlit/tornado가 설정한 SelectorEventLoop 정책과 충돌한다.
        # ProactorEventLoop을 직접 생성하면 이 문제를 완전히 피할 수 있다.
        import asyncio
        loop = asyncio.ProactorEventLoop()
        return loop.run_until_complete(self._async_get_html())

    async def _async_get_html(self) -> str:
        # async_playwright를 사용해 비동기로 HTML을 가져온다.
        async with async_playwright() as p:
            # Chromium 브라우저를 실행한다.
            # headless=True는 브라우저 창을 화면에 보이지 않게 실행한다는 뜻이다.
            browser = await p.chromium.launch(headless=True)

            # 새 브라우저 페이지를 만든다.
            # user_agent는 실제 사용자의 브라우저처럼 보이게 하기 위한 설정이다.
            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
                )
            )

            # 지정된 URL로 이동한다.
            # wait_until="networkidle"은 네트워크 요청이 어느 정도 끝날 때까지 기다린다.
            # timeout=60000은 최대 60초까지 기다린다는 뜻이다.
            await page.goto(self.url, wait_until="networkidle", timeout=60000)

            # 페이지가 완전히 렌더링될 시간을 조금 더 준다.
            # 1500ms = 1.5초
            await page.wait_for_timeout(1500)

            # 현재 브라우저 페이지의 전체 HTML을 문자열로 가져온다.
            html = await page.content()

            # 브라우저를 닫는다.
            await browser.close()

            # 수집한 HTML 문자열을 반환한다.
            return html

    # HTML에서 뉴스 제목과 링크를 추출하는 내부 메서드이다.
    def _parse(self, html: str, limit: int) -> list[CrawlItem]:
        # BeautifulSoup 객체를 생성한다.
        # "lxml"은 빠른 HTML 파서이다.
        soup = BeautifulSoup(html, "lxml")

        # 최종 수집 결과를 저장할 리스트이다.
        result = []

        # 중복 제목을 제거하기 위해 set 자료구조를 사용한다.
        # set은 같은 값을 중복 저장하지 않는다.
        seen = set()

        # HTML 문서 안의 모든 a 태그를 찾는다.
        # a 태그는 보통 링크를 의미한다.
        for a in soup.select("a"):
            # 네이버 뉴스 기사 제목은 a 태그 안의 h4.cn_title 태그에 들어있다.
            # a.get_text()를 쓰면 언론사명 등 제목 외 텍스트가 합쳐지므로
            # h4.cn_title이 있으면 그것만 추출한다.
            h4 = a.find("h4", class_="cn_title")
            title = h4.get_text(strip=True) if h4 else a.get_text(strip=True)

            # a 태그의 href 속성 값을 가져온다.
            # href에는 이동할 링크 주소가 들어 있다.
            href = a.get("href")

            # 제목이나 링크가 없으면 사용할 수 없는 데이터이므로 건너뛴다.
            if not title or not href:
                continue

            # https://n.news.naver.com/article/ 로 시작하는 링크만 수집한다.
            # 메뉴, 버튼, 언론사 링크 등 기사가 아닌 링크는 이 패턴과 맞지 않아 제외된다.
            if not href.startswith("https://n.news.naver.com/article/"):
                continue

            # 제목 길이가 너무 짧으면 뉴스 제목이 아닐 가능성이 높으므로 제외한다.
            if len(title) < 8:
                continue

            # 이미 수집한 제목이면 중복이므로 제외한다.
            if title in seen:
                continue

            # 현재 제목을 중복 확인용 set에 추가한다.
            seen.add(title)

            # CrawlItem 객체를 생성하여 결과 리스트에 추가한다.
            result.append(
                CrawlItem(
                    # 뉴스 제목
                    title=title,

                    # urljoin은 상대경로 링크를 절대경로 링크로 변환한다.
                    # 예: /main/read.naver → https://news.naver.com/main/read.naver
                    link=urljoin(self.url, href),

                    # 크롤링 대상 원본 URL
                    source_url=self.url,

                    # 현재 크롤링한 시간
                    crawled_at=datetime.now()
                )
            )

            # 수집 개수가 limit 이상이면 반복문을 중단한다.
            if len(result) >= limit:
                break

        # 최종 수집 결과 리스트를 반환한다.
        return result
