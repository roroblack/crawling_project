from crawler_molit import MolitCarCrawler
from datetime import datetime

crawler = MolitCarCrawler()

# ── crawl_yearly() 테스트: 19.연도별 시트 파싱 ──────────────────────
print("=== crawl_yearly() 테스트 (이미 받은 파일로 직접 파싱) ===")
import io, openpyxl

with open(r"molit_downloads\2026년_4월_자동차_등록자료_통계.xlsx", "rb") as f:
    xlsx_bytes = f.read()

yearly_items = crawler._parse_yearly(xlsx_bytes, datetime.now())
print(f"추출된 행 수: {len(yearly_items)}")

# 연도별 합계(승용-계) 만 출력
summary = [
    i for i in yearly_items
    if i.vehicle_type == "합계" and i.usage_type == "계"
]
print("\n연도별 전체 자동차 등록 대수 (합계-계):")
for item in summary:
    print(f"  {item.stat_year}년: {item.count:>12,}대")

# ── _parse_links + _find_link 테스트 ────────────────────────────────
print("\n=== _parse_links / _find_link 테스트 ===")
print("페이지 HTML 로딩 중...")
html = crawler._get_html()
links = crawler._parse_links(html)
print(f"전체 downFile 링크 수: {len(links)}")

found = crawler._find_link(links, 2026, 4)
print(f"2026년 4월 파일: {'발견' if found else '없음'}")
if found:
    print(f"  텍스트: {found['text'][:60]}")

# ── _build_year_list 테스트 ─────────────────────────────────────────
print("\n=== _build_year_list(years_back=3) 결과 ===")
for y, m in crawler._build_year_list(3):
    print(f"  {y}년 {m:02d}월")
