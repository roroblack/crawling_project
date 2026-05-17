# 수소차 등록 현황 & 수소충전소 대시보드

국토교통부 통계누리와 공공데이터 포털에서 수소차 등록 현황 및 수소충전소 데이터를 크롤링하여 MySQL에 저장하고, Streamlit으로 시각화하는 프로젝트입니다.

---

## 프로젝트 구조

```
├── app.py                  # 전국 수소충전소 지도 대시보드 (메인 앱)
├── app_preview.py          # 수소차 등록 현황 + 충전소 통합 대시보드
├── crawler_molit.py        # 국토교통부 수소차 등록 현황 크롤러
├── crawler_station.py      # 공공데이터 포털 수소충전소 현황 크롤러
├── load_station_csv.py     # 충전소 CSV 파일 → DB 수동 적재 스크립트
├── db.py                   # MySQL 연결 엔진 생성 모듈
├── models.py               # 데이터 클래스 정의
├── dbscript.sql            # DB 스키마 생성 SQL
├── requirements.txt        # Python 패키지 의존성
└── station_downloads/      # 충전소 CSV 자동 저장 폴더
```

---

## 파일별 설명

### `app.py`
전국 수소충전소 위치를 지도 위에 표시하는 Streamlit 앱입니다.

- 사이드바에서 시도 단위로 필터링 가능
- Folium `MarkerCluster`로 충전소 위치 클러스터링
- DB의 `hydrogen_charging_station` 테이블에서 데이터 조회

### `app_preview.py`
수소차 등록 현황과 충전소 정보를 통합한 풍부한 대시보드입니다.

- 연도별 등록 현황 선형 그래프
- 지역별 등록 현황 순위 바 그래프
- 선택 지역 등록 비율 메트릭
- 선택 지역 수소충전소 지도

### `crawler_molit.py`
[국토교통부 통계누리](https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=58)에서 수소차 등록 현황 엑셀 파일을 내려받아 DB에 저장하는 크롤러입니다.

- Playwright로 브라우저를 자동 조작하여 엑셀 다운로드
- `10.연료별_등록현황` 시트에서 수소/수소전기 행 추출
- 연말(12월) 스냅샷 위주로 수집하여 속도 최적화
- 파일은 `molit_downloads/` 폴더에 임시 저장

### `crawler_station.py`
[공공데이터 포털](https://www.data.go.kr/data/15066838/fileData.do)에서 한국가스안전공사 수소충전소 현황 CSV를 자동 다운로드하여 DB에 저장하는 크롤러입니다.

- Playwright로 CSV 파일 자동 다운로드
- 시도명 정규화 후 `hydrogen_charging_station` 테이블에 upsert
- 다운로드된 파일은 `station_downloads/` 폴더에 저장

### `load_station_csv.py`
크롤러를 사용하지 않고 직접 내려받은 CSV 파일을 DB에 수동으로 적재할 때 사용하는 스크립트입니다.

- `CSV_PATH` 변수에 파일 경로 지정 후 실행
- 다양한 컬럼명 자동 매핑 지원 (충전소명/시설명/station_name 등)
- `station_downloads/` 폴더의 기존 CSV 파일에도 사용 가능

### `db.py`
MySQL 연결 엔진을 생성하는 공통 모듈입니다.

- `.env` 파일의 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` 값을 읽어 연결
- `pymysql` 드라이버 사용, `utf8mb4` 문자셋 설정

### `models.py`
크롤러와 DB 사이에서 데이터를 주고받는 데이터 클래스들을 정의합니다.

| 클래스 | 용도 |
|---|---|
| `CarRegistrationItem` | 수소차 등록 현황 1건 |
| `StationItem` | 수소충전소 1건 |
| `FaqItem` | FAQ 1건 |

### `dbscript.sql`
프로젝트에서 사용하는 MySQL 테이블 생성 SQL입니다. DB 최초 설정 시 한 번 실행합니다.

생성 테이블:
- `regions` — 시도 지역 (17개 시도 + 전국)
- `car_registrations` — 수소차 연도별 등록 현황
- `hydrogen_charging_station` — 수소충전소 위치 정보
- `faq` — FAQ

---

## 환경 설정

### 1. 가상환경 생성 및 패키지 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. `.env` 파일 생성

프로젝트 루트에 `.env` 파일을 생성하고 DB 접속 정보를 입력합니다.

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=crawler_db
```

### 3. DB 스키마 생성

MySQL 클라이언트에서 `dbscript.sql`을 실행합니다.

```bash
mysql -u your_user -p < dbscript.sql
```

---

## 실행 방법

### 크롤러 실행

```bash
# 수소충전소 데이터 크롤링 및 DB 저장
python crawler_station.py

# 수소차 등록 현황 크롤링 및 DB 저장
python crawler_molit.py
```

### CSV 수동 적재 (크롤러 대신 직접 파일 사용 시)

```bash
# load_station_csv.py의 CSV_PATH 변수에 파일 경로를 지정한 뒤 실행
python load_station_csv.py
```

### 대시보드 실행

```bash
# 충전소 지도 앱
.venv\Scripts\python.exe -m streamlit run app.py

# 통합 대시보드
.venv\Scripts\python.exe -m streamlit run app_preview.py
```

---

## 주요 의존성

| 패키지 | 용도 |
|---|---|
| `streamlit` | 웹 대시보드 |
| `playwright` | 브라우저 자동화 크롤링 |
| `sqlalchemy` / `pymysql` | MySQL 연동 |
| `pandas` | 데이터 처리 |
| `folium` / `streamlit-folium` | 지도 시각화 |
| `openpyxl` | 엑셀 파일 파싱 |
| `python-dotenv` | 환경변수 관리 |
