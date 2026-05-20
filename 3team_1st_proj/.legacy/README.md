# 3team_1st_proj

자동 크롤러 데모 프로젝트 (네이버 뉴스 수집 + Streamlit UI)

## 실행
```bash
streamlit run app.py
```

## 파일 구성
- `app.py` — Streamlit UI + 스케줄러 연동
- `crawler.py` — 네이버 뉴스 크롤러
- `db.py` — MySQL 연결 및 테이블 관리
- `models.py` — 데이터 모델
- `scheduler_service.py` — APScheduler 래퍼
- `dbscript.sql` — DB 스키마

## 환경 변수 (`.env`)
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=student
DB_PASSWORD=student80
DB_NAME=crawler_db
CRAWL_URL=https://news.naver.com/
```
└─ tests/
```

## 빠른 시작
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
playwright install chromium

Copy-Item .env.example .env
# .env 파일을 열어 DB 정보, KOSIS_API_KEY, HYDROGEN_STATION_API_KEY 채워넣기

streamlit run app_v2.py     # 신규 통합 UI
# 또는
streamlit run app.py        # 기존 베이스라인 UI
```

## 데이터 출처 (요약)
| 도메인 | 출처 | 문서 |
|---|---|---|
| 수소차 등록 현황 | KOSIS OpenAPI, MOLIT 통계누리 | [docs/research/03_hydrogen_registration_data.md](docs/research/03_hydrogen_registration_data.md) |
| 수소충전소 | 공공데이터포털 | [docs/research/04_hydrogen_station_api.md](docs/research/04_hydrogen_station_api.md) |
| 수소차 FAQ | ev.or.kr, h2korea, 현대차 등 | [docs/research/02_hydrogen_faq_urls.md](docs/research/02_hydrogen_faq_urls.md) |
| 선행 프로젝트 | SKNETWORKS-FAMILY-AICAMP GitHub | [docs/research/01_existing_projects.md](docs/research/01_existing_projects.md) |

> **할루시네이션 방지**: 본 저장소는 [.github/copilot-instructions.md](.github/copilot-instructions.md)
> 의 규칙을 따른다. URL/엔드포인트/통계 수치는 `[검증필요]` 표시 항목을 팀원이 확인 후 확정한다.

## 팀 작업 공유 (구글 스프레드시트)
- 시트 구조 (CSV 템플릿): [scripts/team_tracker_template.csv](scripts/team_tracker_template.csv)
- 자동 생성 스크립트: [scripts/google_sheet_setup.py](scripts/google_sheet_setup.py)
  1. Google Cloud 콘솔에서 서비스 계정 JSON 키 발급 (Sheets + Drive API 활성화)
  2. `GOOGLE_APPLICATION_CREDENTIALS` 와 `TEAM_EMAILS` 환경변수 설정
  3. `python scripts/google_sheet_setup.py "3팀 1차 프로젝트 트래커"`