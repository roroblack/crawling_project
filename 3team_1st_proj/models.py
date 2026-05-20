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
    stat_year: int      # 연도
    stat_month: int     # 월 (0 = 연간합계, 1~12 = 해당 월)
    fuel_type: str      # 수소 / 수소전기 / 전기 / 휘발유 등  → fuel_types.fuel_name
    vehicle_type: str   # 승용 / 승합 / 화물 / 특수 / 소계   → vehicle_types.vehicle_type_name
    usage_type: str     # 비사업용 / 사업용 / 계              → usage_types.usage_type_name
    region: str         # 서울 / 부산 / ... / 제주 / 전국    → regions.region_name
    count: int          # 등록 대수
    crawled_at: datetime


@dataclass
class FaqItem:
    source_site: str    # 출처 사이트 식별자 ('ev.or.kr', 'hyundai.com' 등)
    category: str       # 질문 카테고리 (없으면 빈 문자열)
    question: str       # 질문 내용
    answer: str         # 답변 내용
    crawled_at: datetime


@dataclass
class StationItem:
    station_name: str       # 충전소명                    → hydrogen_charging_station.station_name
    address: str | None     # 상세 주소 (없으면 None)     → hydrogen_charging_station.address
    lat: float | None       # 위도 (없으면 None)          → hydrogen_charging_station.lat
    lon: float | None       # 경도 (없으면 None)          → hydrogen_charging_station.lon
    region: str | None      # 시도명 (서울, 경기 ...)     → regions.region_name
    crawled_at: datetime    # 크롤링 시각                 → hydrogen_charging_station.crawled_at
