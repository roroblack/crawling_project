# 운영체제 환경변수 값을 읽기 위해 os 모듈을 가져온다.
import os

# 비동기 프로그래밍을 위해 asyncio를 가져온다.
import asyncio

# CSV 바이트 데이터를 파일처럼 다루기 위해 io를 가져온다.
import io

# 현재 날짜와 시간을 저장하기 위해 datetime을 가져온다.
from datetime import datetime

# Streamlit 환경에서 asyncio 이벤트 루프를 별도 스레드에서 실행하기 위해 가져온다.
from concurrent.futures import ThreadPoolExecutor

# CSV 데이터를 테이블 형태로 다루기 위해 pandas를 가져온다.
import pandas as pd

# .env 파일에 저장된 환경변수를 읽기 위해 load_dotenv를 가져온다.
from dotenv import load_dotenv

# Playwright 비동기 API를 사용한다.
from playwright.async_api import async_playwright

# SQLAlchemy에서 문자열 SQL을 실행 가능한 객체로 변환할 때 사용한다.
from sqlalchemy import text

# DB 연결 엔진 생성 함수를 가져온다.
from common.db import get_engine, REGIONS

# models.py에 정의된 StationItem 데이터 클래스를 가져온다.
from model.models import StationItem

# .env 파일을 읽어서 os.getenv()로 사용할 수 있게 한다.
load_dotenv()


# 시도명 정규화 테이블이다.
# CSV에 '서울특별시', '서울시' 등 다양한 형태로 오기 때문에 2글자 표준 형식으로 통일한다.
REGION_MAP = {r: r for r in REGIONS}


# 공공데이터 포털(data.go.kr)에서 수소충전소 현황 CSV를 내려받아
# DB에 저장하는 크롤러이다.
class StationCrawler:

    # 객체가 생성될 때 자동으로 실행되는 생성자이다.
    def __init__(self):
        # 공공데이터 포털 수소충전소 현황 파일데이터 페이지 URL이다.
        self.url = "https://www.data.go.kr/data/15066838/fileData.do"

        # 내려받은 CSV 파일을 저장할 폴더 경로이다.
        # 이 스크립트 파일과 같은 폴더 아래 station_downloads 폴더를 사용한다.
        self.download_dir = os.path.join(
            os.path.dirname(__file__), "station_downloads"
        )

    # 외부에서 호출하는 대표 크롤링 메서드이다.
    # CSV를 내려받아 파싱하고 DB에 저장한 뒤 저장된 행 수를 반환한다.
    def crawl(self) -> int:
        # 내려받은 CSV 파일의 바이트 데이터와 저장 경로를 가져온다.
        csv_bytes, save_path = self._get_csv()

        # CSV 바이트 데이터를 DataFrame으로 변환한다.
        dataframe = self._parse(csv_bytes)

        # DataFrame의 각 행을 StationItem 목록으로 변환한다.
        items = self._to_items(dataframe)

        # StationItem 목록을 DB에 저장하고 저장된 행 수를 반환한다.
        return self._save(items)

    # 실제 브라우저를 실행해서 CSV 파일을 내려받는 내부 메서드이다.
    # 메서드 이름 앞의 _는 내부에서 사용하는 메서드라는 의미이다.
    def _get_csv(self) -> tuple[bytes, str]:
        # Streamlit은 asyncio 이벤트 루프를 사용하기 때문에
        # sync_playwright를 직접 호출하면 Windows에서 충돌이 발생한다.
        # 별도의 스레드에서 실행하면 이 문제를 피할 수 있다.
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_playwright)
            return future.result()

    def _run_playwright(self) -> tuple[bytes, str]:
        # Windows에서 subprocess를 지원하는 ProactorEventLoop을 명시적으로 생성하여
        # 그 위에서 async_playwright를 실행한다.
        # sync_playwright는 내부적으로 asyncio.new_event_loop()를 사용하기 때문에
        # Streamlit/tornado가 설정한 SelectorEventLoop 정책과 충돌한다.
        # ProactorEventLoop을 직접 생성하면 이 문제를 완전히 피할 수 있다.
        loop = asyncio.ProactorEventLoop()
        return loop.run_until_complete(self._async_download())

    async def _async_download(self) -> tuple[bytes, str]:
        # CSV 파일을 저장할 폴더가 없으면 만든다.
        os.makedirs(self.download_dir, exist_ok=True)

        # async_playwright를 사용해 비동기로 CSV를 내려받는다.
        async with async_playwright() as p:
            # Chromium 브라우저를 실행한다.
            # headless=True는 브라우저 창을 화면에 보이지 않게 실행한다는 뜻이다.
            browser = await p.chromium.launch(headless=True)

            # 파일 다운로드를 허용하는 브라우저 컨텍스트를 만든다.
            context = await browser.new_context(accept_downloads=True)

            # 새 브라우저 페이지를 만든다.
            page = await context.new_page()

            # 지정된 URL로 이동한다.
            # wait_until="networkidle"은 네트워크 요청이 어느 정도 끝날 때까지 기다린다.
            print(f"[크롤러] 페이지 이동: {self.url}")
            await page.goto(self.url, wait_until="networkidle", timeout=30_000)

            # 다운로드 버튼을 찾기 위한 CSS 선택자 후보 목록이다.
            # data.go.kr 페이지 구조가 바뀌면 선택자도 달라질 수 있다.
            selectors = [
                "a.btn-m.type-down",
                "a:has-text('다운로드')",
                "button:has-text('다운로드')",
                ".file-down-btn",
                "a[onclick*='fileDownload']",
                "a[href*='fileDownload']",
            ]

            # 후보 선택자를 순서대로 시도해서 다운로드 버튼을 찾는다.
            download_btn = None
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        # 버튼을 찾았으면 저장하고 반복문을 중단한다.
                        download_btn = element
                        print(f"[크롤러] 다운로드 버튼 발견: {selector}")
                        break
                except Exception:
                    continue

            if download_btn is None:
                # 버튼을 찾지 못하면 페이지 HTML을 파일로 저장해 디버깅에 활용한다.
                html = await page.content()
                await browser.close()
                dump_path = os.path.join(self.download_dir, "page_dump.html")
                with open(dump_path, "w", encoding="utf-8") as file:
                    file.write(html)
                raise RuntimeError(
                    f"다운로드 버튼을 찾지 못했습니다.\n"
                    f"페이지 HTML이 {dump_path} 에 저장되었습니다.\n"
                    f"해당 파일을 확인 후 올바른 선택자를 알려주세요."
                )

            # 다운로드 이벤트가 발생할 때까지 기다린 뒤 버튼을 클릭한다.
            async with page.expect_download(timeout=60_000) as download_info:
                await download_btn.click()

            # 다운로드가 완료된 파일 객체를 가져온다.
            downloaded_file = await download_info.value

            # 원래 파일명을 가져온다. 없으면 기본값을 사용한다.
            original_name = downloaded_file.suggested_filename or "hydrogen_stations.csv"

            # 타임스탬프를 붙인 파일명으로 저장한다.
            # 이전 파일과 섞이지 않도록 실행 시각을 파일명에 포함한다.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_name = f"{os.path.splitext(original_name)[0]}_{timestamp}.csv"
            save_path = os.path.join(self.download_dir, save_name)

            await downloaded_file.save_as(save_path)
            print(f"[크롤러] CSV 저장 완료: {save_path}")

            # 브라우저를 닫는다.
            await browser.close()

            # 저장된 CSV 파일을 바이트로 읽어서 반환한다.
            with open(save_path, "rb") as file:
                return file.read(), save_path

    # CSV 바이트 데이터를 pandas DataFrame으로 변환하는 내부 메서드이다.
    def _parse(self, csv_bytes: bytes) -> pd.DataFrame:
        # 인코딩 후보 목록을 순서대로 시도한다.
        # 공공데이터 CSV는 euc-kr 또는 cp949 인코딩인 경우가 많다.
        for encoding in ["euc-kr", "cp949", "utf-8-sig", "utf-8"]:
            try:
                dataframe = pd.read_csv(io.BytesIO(csv_bytes), encoding=encoding)
                print(f"[파싱] 인코딩: {encoding}, 행 수: {len(dataframe)}")
                print(f"[파싱] 컬럼 목록: {list(dataframe.columns)}")
                return dataframe
            except Exception:
                continue
        raise ValueError("CSV 인코딩 감지 실패: euc-kr, cp949, utf-8-sig, utf-8 모두 실패했습니다.")

    # DataFrame의 각 행을 StationItem 목록으로 변환하는 내부 메서드이다.
    def _to_items(self, dataframe: pd.DataFrame) -> list[StationItem]:
        # 컬럼 후보 이름으로 실제 컬럼명을 찾는다.
        col_station_name = self._find_col(dataframe, ["충전소명", "시설명", "station_name", "name", "충전소 명"])
        col_address      = self._find_col(dataframe, ["주소", "소재지", "address", "도로명주소", "상세주소", "소재지도로명주소"])
        col_lat          = self._find_col(dataframe, ["위도", "lat", "latitude", "y좌표"])
        col_lon          = self._find_col(dataframe, ["경도", "lon", "lng", "longitude", "x좌표"])
        col_region       = self._find_col(dataframe, ["시도", "시도명", "시·도", "region", "지역", "광역시도"])

        print(f"[매핑] 충전소명: {col_station_name}")
        print(f"[매핑] 주소:     {col_address}")
        print(f"[매핑] 위도:     {col_lat}")
        print(f"[매핑] 경도:     {col_lon}")
        print(f"[매핑] 시도:     {col_region}")

        if col_station_name is None:
            raise ValueError(
                f"충전소명 컬럼을 찾지 못했습니다.\nCSV 컬럼 목록: {list(dataframe.columns)}"
            )

        # 최종 수집 결과를 저장할 리스트이다.
        result = []

        for _, row in dataframe.iterrows():
            # 충전소명이 없는 행은 건너뛴다.
            station_name = str(row[col_station_name]).strip()
            if not station_name or station_name == "nan":
                continue

            # 주소가 없으면 None으로 처리한다.
            address = (
                str(row[col_address]).strip()
                if col_address and not pd.isna(row[col_address])
                else None
            )

            # 위도가 없거나 숫자로 변환할 수 없으면 None으로 처리한다.
            try:
                lat = float(row[col_lat]) if col_lat and not pd.isna(row[col_lat]) else None
            except (ValueError, TypeError):
                lat = None

            # 경도가 없거나 숫자로 변환할 수 없으면 None으로 처리한다.
            try:
                lon = float(row[col_lon]) if col_lon and not pd.isna(row[col_lon]) else None
            except (ValueError, TypeError):
                lon = None

            # 시도명을 2글자 표준 형식으로 변환한다.
            raw_region = (
                str(row[col_region]).strip()
                if col_region and not pd.isna(row[col_region])
                else (address[:3] if address else "")
            )
            region = self._normalize_region(raw_region)

            # StationItem 객체를 생성하여 결과 리스트에 추가한다.
            result.append(
                StationItem(
                    station_name=station_name,
                    address=address,
                    lat=lat,
                    lon=lon,
                    region=region,
                )
            )

        return result

    # StationItem 목록을 DB의 hydrogen_charging_station 테이블에 저장하는 내부 메서드이다.
    def _save(self, items: list[StationItem]) -> int:
        engine = get_engine()

        # regions 테이블에서 시도명 → region_id 매핑을 미리 읽어온다.
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT region_id, region_name FROM regions"))
            region_id_map = {row.region_name: row.region_id for row in rows}

        if not region_id_map:
            raise RuntimeError("regions 테이블이 비어 있습니다. db.init_table()을 먼저 실행하세요.")

        # 저장 성공 횟수와 건너뜀 횟수이다.
        inserted = 0
        skipped  = 0

        with engine.begin() as conn:
            # 기존 충전소 데이터를 모두 삭제한 뒤 새 데이터를 넣는다.
            # 분기마다 최신 현황으로 전체 교체하는 방식이다.
            conn.execute(text("DELETE FROM hydrogen_charging_station"))

            for item in items:
                # 시도명으로 region_id를 찾는다.
                region_id = region_id_map.get(item.region)

                if region_id is None:
                    # 매핑되지 않는 시도명이면 건너뛴다.
                    skipped += 1
                    continue

                conn.execute(text("""
                    INSERT INTO hydrogen_charging_station
                        (region_id, station_name, address, lat, lon)
                    VALUES
                        (:region_id, :station_name, :address, :lat, :lon)
                """), {
                    "region_id":    region_id,
                    "station_name": item.station_name,
                    "address":      item.address,
                    "lat":          item.lat,
                    "lon":          item.lon,
                })
                inserted += 1

        print(f"[DB] 삽입: {inserted}개 / 건너뜀(지역 미매핑): {skipped}개")
        return inserted

    # 컬럼 후보 목록에서 DataFrame에 실제로 존재하는 컬럼명을 찾아 반환하는 내부 메서드이다.
    # 공백과 대소문자를 무시하고 비교한다.
    def _find_col(self, dataframe: pd.DataFrame, candidates: list[str]) -> str | None:
        # 비교를 위해 컬럼명에서 공백을 제거하고 소문자로 변환한다.
        cols_lower = {col.lower().replace(" ", ""): col for col in dataframe.columns}
        for candidate in candidates:
            key = candidate.lower().replace(" ", "")
            if key in cols_lower:
                return cols_lower[key]
        # 후보 목록에 없으면 None을 반환한다.
        return None

    # 시도명 문자열을 2글자 표준 형식으로 변환하는 내부 메서드이다.
    # 예: '서울특별시' → '서울', '경기도' → '경기'
    def _normalize_region(self, raw: str) -> str | None:
        if not raw or raw == "nan":
            return None
        raw = str(raw).strip()
        for key in REGION_MAP:
            if raw.startswith(key):
                return REGION_MAP[key]
        # 앞 2글자로 최후 시도한다.
        return raw[:2]


# 동기 래퍼 함수이다.
# Streamlit이나 스케줄러처럼 asyncio 루프가 이미 실행 중인 환경에서 안전하게 호출할 수 있다.
def run_sync() -> int:
    return StationCrawler().crawl()


def load_from_file(path: str) -> int:
    """로컬 CSV 파일을 읽어 hydrogen_charging_station 테이블에 저장한다.
    크롤러 없이 직접 내려받은 파일을 적재할 때 사용한다.
    저장된 레코드 수를 반환한다."""
    crawler = StationCrawler()
    with open(path, "rb") as f:
        csv_bytes = f.read()
    items = crawler._to_items(crawler._parse(csv_bytes))
    return crawler._save(items)


# 이 파일을 직접 실행하면 크롤링을 즉시 시작한다.
if __name__ == "__main__":
    count = StationCrawler().crawl()
    print(f"[완료] 수소충전소 {count}개 DB 저장")
