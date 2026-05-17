from dataclasses import dataclass
from datetime import datetime


@dataclass
class CrawlItem:
    title: str
    link: str
    source_url: str
    crawled_at: datetime


@dataclass
class CarRegistrationItem:
    stat_year: int   # 연도
    region: str      # 서울 / 부산 / ... / 제주 / 전국 → regions.region_name
    count: int       # 등록 대수 (해당 연도 수소차 전체 누적 합산)
    # ── 아래 필드는 DB 스키마에 없으므로 주석 처리 ──
    # stat_month: int     # 월 — DB는 stat_year만 저장하므로 불필요
    # fuel_type: str      # 수소/수소전기 — 합산 후 저장하므로 불필요
    # vehicle_type: str   # 차종 — 합산 후 저장하므로 불필요
    # usage_type: str     # 용도 — 합산 후 저장하므로 불필요
    # crawled_at: datetime  # 크롤 시각 — crawl_stat.last_crawled_at 으로 일원화


@dataclass
class FaqItem:
    source_site: str    # 출처 사이트 식별자 ('ev.or.kr', 'hyundai.com' 등)
    category: str       # 질문 카테고리 (없으면 빈 문자열)
    question: str       # 질문 내용
    answer: str         # 답변 내용
    crawled_at: datetime


@dataclass
class StationItem:
    station_name: str       # 충전소명                -> hydrogen_charging_station.station_name
    address: str | None     # 상세 주소 (없으면 None) -> hydrogen_charging_station.address
    lat: float | None       # 위도 (없으면 None)      -> hydrogen_charging_station.lat
    lon: float | None       # 경도 (없으면 None)      -> hydrogen_charging_station.lon
    region: str | None      # 시도명 (서울, 경기 ...) -> regions.region_name
    # crawled_at 는 DB에 저장하지 않으므로 여기에 없음
    # 수집 시각 추적은 crawl_stat.last_crawled_at 으로 일괄 관리
