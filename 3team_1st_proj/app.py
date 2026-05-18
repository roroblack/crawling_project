"""
수소차 등록 현황 & 충전소 대시보드 (기본 Streamlit 템플릿)

사이드바:
  - 등록 기간 선택 (start_year ~ end_year)
  - 지역 선택 ("전국", "서울", "부산", ... 17개 시도)

메인:
  1. 선택 지역의 연도별 등록 현황 선형 그래프
  2. 등록 현황 순위 바 그래프 (전국 합계 포함, 선택 기간 합계)
  3. (선택 지역 등록수 / 전체 등록수) 비율 메트릭
  4. 선택 지역의 수소차 충전소 지도

실행:
  .venv\\Scripts\\python.exe -m streamlit run app_preview.py
"""

# 데이터셋 ZIP 직렬화에 사용한다.
import io
import json
import zipfile
from pathlib import Path

# 저장 파일명에 현재 시각을 포함하기 위해 사용한다.
from datetime import datetime

# Streamlit 앱 UI 구성 라이브러리이다.
import streamlit as st

# 등록/충전소 데이터를 테이블 형태로 다루기 위해 사용한다.
import pandas as pd

# 인터랙티브 바/선형 그래프를 그리기 위해 사용한다.
import altair as alt

# 충전소 위치를 지도에 마커로 표시하기 위해 사용한다.
import folium

# folium 지도를 Streamlit 컴포넌트로 렌더링하기 위해 사용한다.
from streamlit_folium import st_folium

# 문자열 SQL을 SQLAlchemy가 실행 가능한 객체로 변환할 때 사용한다.
# DB 쿼리 함수(주석 참고)는 db.py 로 일원화했으므로 포트 임포트는 하지 않는다.

# 데이터 조회 함수 + 지역 표시 순서 상수를 가져온다.
from db import (
    fetch_registrations, fetch_stations, fetch_faqs,
    fetch_car_last_crawled, fetch_faq_last_crawled,
    save_car_registrations, save_faqs,
    init_table, REGION_ORDER,
)
from crawler_molit import MolitCarCrawler
from crawler_faq import crawl_all_faqs
from models import FaqItem


# 시도 표시 고정 순서는 db.REGION_ORDER 사용 (전국 + 17 시도)


# ──────────────────────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="수소차 등록 현황 대시보드",
    page_icon="💧",
    layout="wide",
)


# ──────────────────────────────────────────────────────────────
# 데이터 로드
# ──────────────────────────────────────────────────────────────
# @st.cache_data(ttl=300): 5분 동안 응답을 캐시해서 매 리런마다 DB를 오가는 것을 막는다.
# SQL 코드는 db.py의 fetch_* 함수에만 있고 여기서는 데이터를 호출만 한다.
@st.cache_data(ttl=300)
def load_registrations() -> pd.DataFrame:
    """등록 데이터 조회 (region_name, stat_year, count)"""
    return fetch_registrations()


@st.cache_data(ttl=300)
def load_stations() -> pd.DataFrame:
    """충전소 데이터 조회 (station_name, address, lat, lon, region_name)"""
    return fetch_stations()


regs_df_db      = load_registrations()
stations_df_db  = load_stations()

# ── 연도 표시 유틸리티 ─────────────────────────────────────────
# 현재 연도(예: 2026)는 연말 데이터가 아닌 특정 월 스냅샷이므로 "26년 4월" 형식으로 표시한다.

CURRENT_YEAR = datetime.now().year


@st.cache_data(ttl=300)
def load_stat_month() -> int:
    """현재 연도 통계 월: 데이터 로드 시점에 molit_downloads/ 파일명에서 파싱해 캐싱한다.
    load_registrations() 와 동일한 TTL 로 묶여 있어 데이터 갱신 시 함께 무효화된다."""
    import re as _re
    folder = Path(__file__).parent / "molit_downloads"
    files = sorted(
        [f for f in folder.glob(f"{CURRENT_YEAR}년_*.xlsx") if not f.name.startswith("~$")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for f in files:
        m = _re.search(r"_(\d{1,2})월", f.name)
        if m:
            return int(m.group(1))
    return datetime.now().month


# 데이터 로드와 동시에 통계 월을 메모리에 확정한다.
STAT_MONTH: int = load_stat_month()


@st.cache_data(ttl=3600)
def _load_last_crawled():
    """crawl_stat 의 car_registration last_crawled_at 반환. 기록 없으면 None."""
    try:
        return fetch_car_last_crawled()
    except Exception:
        return None


@st.cache_data(ttl=3600)
def _load_faq_last_crawled():
    """crawl_stat 의 faq last_crawled_at 반환. 기록 없으면 None."""
    try:
        return fetch_faq_last_crawled()
    except Exception:
        return None


_last_crawled = _load_last_crawled()


def year_label(y: int) -> str:
    """연도 → UI 표시 문자열. 현재 연도면 '26년 N월' 형식(N=STAT_MONTH), 그 외에는 연도 그대로."""
    if y == CURRENT_YEAR:
        return f"{str(y)[2:]}년 {STAT_MONTH}월"
    return str(y)


# ── DB 스키마 최신화 + 자동 크롤링 ────────────────────────────

if "db_init_done" not in st.session_state:
    st.session_state["db_init_done"] = True
    try:
        init_table()
    except Exception:
        pass

# 현재 연도 데이터가 DB에 없으면 앱 시작 시 자동으로 갱신한다 (세션당 1회).
# 우선순위: ① data_backup/ 폴더의 최신 ZIP → ② 국토교통부 웹 크롤링
_db_year_max = int(regs_df_db["stat_year"].max()) if not regs_df_db.empty else 0
_BACKUP_DIR  = Path(__file__).parent / "data_backup"


def _find_backup_zip() -> "Path | None":
    """data_backup/ 폴더에서 현재 연도 데이터가 담긴 최신 ZIP을 반환한다."""
    if not _BACKUP_DIR.exists():
        return None
    zips = sorted(_BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for zp in zips:
        try:
            with zipfile.ZipFile(zp) as _zf:
                if "car_registrations.csv" not in _zf.namelist():
                    continue
                _bdf = pd.read_csv(_zf.open("car_registrations.csv"))
                if "stat_year" in _bdf.columns and int(_bdf["stat_year"].max()) >= CURRENT_YEAR:
                    return zp
        except Exception:
            continue
    return None


def _find_faq_backup() -> "tuple[Path, pd.DataFrame] | None":
    """data_backup/ 폴더의 ZIP 중 faq.csv가 있고 내용이 있는 최신 파일과
    DataFrame을 (path, df) 튜플로 반환한다. 없으면 None."""
    if not _BACKUP_DIR.exists():
        return None
    zips = sorted(_BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for _zp in zips:
        try:
            with zipfile.ZipFile(_zp) as _zf:
                if "faq.csv" not in _zf.namelist():
                    continue
                _fdf = pd.read_csv(_zf.open("faq.csv"))
                if not _fdf.empty and "question" in _fdf.columns:
                    return (_zp, _fdf)
        except Exception:
            continue
    return None


def _df_to_faq_items(df: pd.DataFrame) -> list[FaqItem]:
    """DataFrame(question, answer)을 FaqItem 리스트로 변환한다."""
    now = datetime.now()
    result = []
    for _, row in df.iterrows():
        q = str(row.get("question", "")).strip()
        a = str(row.get("answer", "") or "").strip()
        if q:
            result.append(FaqItem(source_site="backup", category="", question=q, answer=a, crawled_at=now))
    return result


if _db_year_max < CURRENT_YEAR and (_last_crawled is None or _last_crawled.date() < datetime.now().date()) and "auto_crawl_done" not in st.session_state:
    st.session_state["auto_crawl_done"] = True
    _backup_zip = _find_backup_zip()
    if _backup_zip is not None:
        # ① 로컬 백업 ZIP 로드 — 웹 크롤링 스킵
        try:
            with zipfile.ZipFile(_backup_zip) as _zf:
                _bdf = pd.read_csv(_zf.open("car_registrations.csv"))
            st.session_state["regs_df_override"] = _bdf
            for _k in ("year_range", "selected_region"):
                st.session_state.pop(_k, None)
            st.rerun()
        except Exception as _be:
            st.warning(f"백업 ZIP 로드 실패, 크롤링으로 전환합니다: {_be}")
            _backup_zip = None
    if _backup_zip is None:
        # ② 국토교통부 웹 크롤링
        with st.spinner(f"📡 {CURRENT_YEAR}년 최신 수소차 등록 데이터를 수집하고 있습니다..."):
            try:
                _ac = MolitCarCrawler()
                _ai = _ac.crawl()
                if _ai:
                    save_car_registrations(_ai)
                    load_registrations.clear()
                    load_stat_month.clear()
                    _load_last_crawled.clear()
                    st.rerun()
            except Exception as _ae:
                st.warning(f"자동 크롤링 실패 (기존 데이터로 표시): {_ae}")

# 사이드바에서 ZIP을 업로드한 경우 세션 state의 override 데이터를 우선 사용한다.
# 업로드한 데이터가 없으면 DB에서 로드한 원본 데이터를 그대로 사용한다.
regs_df         = st.session_state.get("regs_df_override",     regs_df_db)
stations_df     = st.session_state.get("stations_df_override", stations_df_db)


# ── FAQ 로더 (DB faq 테이블, 비어있으면 더미) ────────────────────
# faq 테이블이 비어 있을 때 표시할 예비 질문/답변 목록이다.
# 크롤러가 faq 테이블을 채우면 자동으로 실제 데이터로 교체된다.
FAQ_FALLBACK = [
    ("수소차는 어떻게 충전하나요?",
     "수소충전소에서 5분 내외로 완충이 가능합니다. LPG 충전과 유사한 방식으로 노즐을 연결하면 자동으로 충전됩니다."),
    ("수소차 한 번 충전으로 얼마나 갈 수 있나요?",
     "현대 넥쏘 기준 1회 완충(약 6.33kg) 시 약 609km를 주행할 수 있습니다."),
    ("수소차 구매 보조금은 얼마인가요?",
     "2026년 기준 국비 2,250만원 + 지자체 보조금 1,000만원 내외가 지원되며, 지역에 따라 차이가 있습니다."),
    ("수소충전소는 전국에 몇 곳 있나요?",
     "한국가스안전공사 기준 약 270여 곳이 운영 중이며, 매년 확대되고 있습니다."),
    ("수소차는 안전한가요?",
     "수소탱크는 700bar 압력과 총격 테스트를 통과한 고강도 탄소섬유 복합소재로 제작되어 매우 안전합니다."),
]


@st.cache_data(ttl=300)
def load_faqs() -> list[ tuple[str, str]]:
    """드비 faq 테이블 조회; 비어 있으면 FAQ_FALLBACK 반환"""
    rows = fetch_faqs()
    if not rows:
        return FAQ_FALLBACK
    return rows


# ──────────────────────────────────────────────────────────────
# 사이드바 — 네비게이션 메뉴
# ──────────────────────────────────────────────────────────────
_PAGES = ["🏠 홈", "📈 수소차 등록현황", "🗺️ 수소차 충전소", "💬 FAQ"]
_page  = st.sidebar.radio("메뉴", _PAGES, key="nav_page", label_visibility="collapsed")

# ── 슬라이더 파란색 CSS (전역 주입) ───────────────────────────
st.markdown("""
<style>
div[data-testid="stSlider"] [role="slider"]      { background: #2563eb !important; }
div[data-testid="stSlider"] [class*="TrackFill"] { background: #2563eb !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

# DB에서 로드된 연도 범위를 슬라이더 기본값으로 사용한다.
year_min        = int(regs_df["stat_year"].min())
year_max        = int(regs_df["stat_year"].max())
# 슬라이더 최댓값 = 실제 데이터 최댓값으로 고정 → 선형 그래프 x축과 항상 동기화된다.
slider_year_max = year_max
# DB에 실제로 데이터가 있는 시도만 selectbox에 표시한다.
available       = set(regs_df["region_name"].unique().tolist())
# REGION_ORDER 기준으로 정렬한 선택 가능한 지역 목록이다 (전국 + 데이터 있는 시도).
region_options  = [r for r in REGION_ORDER if r == "전국" or r in available]
default_region  = "전국"

# 등록현황·충전소 페이지에서만 필터를 표시한다.
if _page in ("📈 수소차 등록현황", "🗺️ 수소차 충전소"):
    st.sidebar.markdown("**🔍 필터**")

    if _page == "📈 수소차 등록현황":
        # 1) 등록 기간 선택 (기본: 전체 기간, 26년 N월 포함)
        year_range = st.sidebar.slider(
            "등록 기간 선택",
            min_value=year_min,
            max_value=slider_year_max,
            value=(year_min, slider_year_max),
            step=1,
            key="year_range",
        )
        st.sidebar.caption(
            f"기간: **{year_label(year_range[0])} ~ {year_label(year_range[1])}**"
        )
    else:
        year_range = (year_min, slider_year_max)

    # 2) 지역 선택 (전국 + 17개 시도, 고정 순서)
    selected_region = st.sidebar.selectbox(
        "지역 선택",
        region_options,
        index=region_options.index(default_region),
        key="selected_region",
    )
else:
    year_range      = (year_min, slider_year_max)
    selected_region = default_region

st.sidebar.markdown("---")

# ── 전체 데이터 저장 / 불러오기 (DB 스냅샷) ──────────────────
st.sidebar.subheader("💾 데이터 저장 / 불러오기")
st.sidebar.caption("현재 로드된 전체 데이터셋을 ZIP으로 내보내거나, 채워 넣을 수 있습니다.")

def _build_dataset_zip() -> bytes:
    """현재 표시 중인 등록/충전소/FAQ 데이터를 CSV 3개 + meta.json 으로 묶어 ZIP 반환"""
    faqs = load_faqs()
    faqs_df = pd.DataFrame(faqs, columns=["question", "answer"])

    meta = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "counts": {
            "car_registrations":         len(regs_df),
            "hydrogen_charging_station": len(stations_df),
            "faq":                        len(faqs_df),
        },
        "format": "v1",
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("car_registrations.csv",         regs_df.to_csv     (index=False, encoding="utf-8"))
        zf.writestr("hydrogen_charging_station.csv", stations_df.to_csv (index=False, encoding="utf-8"))
        zf.writestr("faq.csv",                       faqs_df.to_csv     (index=False, encoding="utf-8"))
        zf.writestr("meta.json",                     json.dumps         (meta, ensure_ascii=False, indent=2))
    return buf.getvalue()

st.sidebar.download_button(
    label="⬇️  전체 데이터 저장 (ZIP)",
    data=_build_dataset_zip(),
    file_name=f"h2_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
    mime="application/zip",
    use_container_width=True,
)

uploaded_zip = st.sidebar.file_uploader(
    "⬆️  저장된 데이터 불러오기 (ZIP)",
    type=["zip"],
    key="dataset_uploader",
)
if uploaded_zip is not None:
    try:
        with zipfile.ZipFile(uploaded_zip) as zf:
            names           = zf.namelist()
            new_regs        = pd.read_csv(zf.open("car_registrations.csv")) \
                if "car_registrations.csv"          in names else None
            new_stations    = pd.read_csv(zf.open("hydrogen_charging_station.csv")) \
                if "hydrogen_charging_station.csv"  in names else None
            new_faqs        = pd.read_csv(zf.open("faq.csv")) \
                if "faq.csv"                        in names else None

        if new_regs     is not None:
            st.session_state["regs_df_override"]        = new_regs
        if new_stations is not None:
            st.session_state["stations_df_override"]    = new_stations
        if new_faqs     is not None:
            # DataFrame → (question, answer) 튜플 리스트로 변환한다.
            st.session_state["faqs_override"]           = [
                (q, a) for q, a in zip(new_faqs["question"], new_faqs["answer"].fillna(""))
            ]

        # 리로드 전에 위젯 key를 삭제해서 Streamlit이 기본값으로 다시 그리게 한다.
        # 삭제하지 않으면 이전 위젯 값이 남아 필터가 잘못 적용될 수 있다.
        for k in ("year_range", "selected_region", "dataset_uploader"):
            st.session_state.pop(k, None)
        st.sidebar.success(
            f"불러오기 완료  ·  등록    {0 if new_regs      is None else len(new_regs):,} / "
            f"충전소                     {0 if new_stations  is None else len(new_stations):,} / "
            f"FAQ                        {0 if new_faqs      is None else len(new_faqs):,}"
        )
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"불러오기 실패: {e}")

if (    "regs_df_override"          in st.session_state
        or "stations_df_override"   in st.session_state
        or "faqs_override"          in st.session_state):
    if st.sidebar.button("↻  DB 데이터로 되돌리기", use_container_width=True):
        for k in ("regs_df_override", "stations_df_override", "faqs_override"):
            st.session_state.pop(k, None)
        st.rerun()
    st.sidebar.info("📂 현재 업로드된 데이터를 표시 중입니다.")

st.sidebar.markdown("---")
st.sidebar.caption(
    f"📊 등록 데이터: {len(regs_df):,} 행\n\n"
    f"🗺️ 충전소: {len(stations_df):,} 개"
)


# ──────────────────────────────────────────────────────────────
# 데이터 필터링
# ──────────────────────────────────────────────────────────────
start_year, end_year = year_range

# 선택한 연도 범위로 DB 데이터를 자른다.
filtered = regs_df[
    (regs_df["stat_year"] >= start_year) & (regs_df["stat_year"] <= end_year)
].copy()

# 선택 지역의 연도별 시계열: 전국이면 전체 합산, 특정 시도면 해당 지역만 가져온다.
if selected_region == "전국":
    yearly = filtered.groupby("stat_year", as_index=False)["count"].sum()
else:
    yearly = (
        filtered[filtered["region_name"] == selected_region]
        .groupby("stat_year", as_index=False)["count"]
        .sum()
    )

# 지역별 합계 — end_year 기준 누적 등록 대수 (최신 스냅샷)
# 각 연도의 count는 그 시점까지의 누적값이므로, 연도 합산이 아닌
# end_year 단일 연도의 데이터를 사용해야 올바른 현황을 표시한다.
rank_df = (
    regs_df[regs_df["stat_year"] == end_year]
    .groupby("region_name", as_index=False)["count"]
    .sum()
)
nation_total        = int(rank_df["count"].sum())
nation_row          = pd.DataFrame([{"region_name": "전국", "count": nation_total}])
rank_df_with_nation = pd.concat([nation_row, rank_df], ignore_index=True)

# REGION_ORDER 기준으로 정렬 — 향수 ui에서 항상 지역이 같은 순서로 표시된다.
order_index                     = {name: i for i, name in enumerate(REGION_ORDER)}
rank_df_with_nation["_order"]   = rank_df_with_nation["region_name"].map(order_index)
rank_df_with_nation             = (
    rank_df_with_nation.sort_values("_order")
    .drop(columns="_order")
    .reset_index(drop=True)
)

# 선택 지역의 백분율 계산 (전국이면 100%)
if selected_region == "전국":
    selected_count = nation_total
else:
    sel             = rank_df[rank_df["region_name"] == selected_region]["count"]
    selected_count  = int(sel.iloc[0]) if not sel.empty else 0

ratio = (selected_count / nation_total * 100) if nation_total else 0


# ──────────────────────────────────────────────────────────────
# 페이지 라우팅 — 홈 / 충전소 / FAQ (이 블록 이후는 등록현황 전용)
# ──────────────────────────────────────────────────────────────
if _page == "🏠 홈":
    st.title("💧 물로간다")
    st.markdown("#### 🌱 수소 모빌리티의 현재를 한눈에 확인하세요")
    st.write(
        "전국 수소차 등록 현황과 충전소 위치 정보를 제공합니다. "
        "아래 카드 또는 좌측 메뉴에서 원하는 페이지를 선택하세요."
    )
    st.markdown("---")

    _hc1, _hc2, _hc3 = st.columns(3)
    def _nav_to(page: str):
        st.session_state["nav_page"] = page

    with _hc1:
        st.markdown("""<div style='padding:20px;border-radius:12px;background:#eff6ff;
border:1px solid #bfdbfe;min-height:130px'>
<h4 style='color:#1d4ed8;margin-top:0'>📈 수소차 등록현황</h4>
<p style='color:#374151;margin:0'>연도별·지역별 수소차 등록 추이를 다양한 차트로 확인하세요.</p>
</div>""", unsafe_allow_html=True)
        st.button("바로가기 →", key="h_reg", use_container_width=True,
                  on_click=_nav_to, args=("📈 수소차 등록현황",))
    with _hc2:
        st.markdown("""<div style='padding:20px;border-radius:12px;background:#f0fdf4;
border:1px solid #bbf7d0;min-height:130px'>
<h4 style='color:#15803d;margin-top:0'>🗺️ 수소차 충전소</h4>
<p style='color:#374151;margin:0'>전국 수소충전소 위치와 상세 정보를 지도로 확인하세요.</p>
</div>""", unsafe_allow_html=True)
        st.button("바로가기 →", key="h_map", use_container_width=True,
                  on_click=_nav_to, args=("🗺️ 수소차 충전소",))
    with _hc3:
        st.markdown("""<div style='padding:20px;border-radius:12px;background:#fdf4ff;
border:1px solid #e9d5ff;min-height:130px'>
<h4 style='color:#7e22ce;margin-top:0'>💬 FAQ</h4>
<p style='color:#374151;margin:0'>수소차에 관한 자주 묻는 질문과 답변을 확인하세요.</p>
</div>""", unsafe_allow_html=True)
        st.button("바로가기 →", key="h_faq", use_container_width=True,
                  on_click=_nav_to, args=("💬 FAQ",))

    st.markdown("---")
    _sm1, _sm2, _sm3 = st.columns(3)
    _sm1.metric("전국 수소차 누적 등록", f"{int(regs_df_db['count'].sum()):,} 대")
    _sm2.metric("전국 수소충전소", f"{len(stations_df_db):,} 곳")
    _sm3.metric("최신 데이터 기준", year_label(slider_year_max))
    st.stop()

elif _page == "🗺️ 수소차 충전소":
    st.title("🗺️ 수소차 충전소")
    st.caption(f"선택 지역: **{selected_region}**")
    _map_st = (
        stations_df if selected_region == "전국"
        else stations_df[stations_df["region_name"] == selected_region]
    )
    st.caption(f"표시된 충전소: **{len(_map_st):,}** 곳")
    if _map_st.empty:
        st.info("해당 지역의 충전소 데이터가 없습니다.")
    else:
        _m = folium.Map(
            location=[_map_st["lat"].mean(), _map_st["lon"].mean()],
            zoom_start=7 if selected_region == "전국" else 10,
        )
        for _, _r in _map_st.iterrows():
            folium.Marker(
                location=[_r["lat"], _r["lon"]],
                popup=folium.Popup(
                    f"<b>{_r['station_name']}</b><br>{_r['address'] or ''}",
                    max_width=260,
                ),
                tooltip=_r["station_name"],
                icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
            ).add_to(_m)
        st_folium(_m, height=540, use_container_width=True, returned_objects=[])
    st.stop()

elif _page == "💬 FAQ":
    st.title("💬 자주 묻는 질문 (FAQ)")

    # ── FAQ 자동 갱신: 이 탭에 들어왜을 때만 실행 (세션당 1회) ─────────────────
    # 펰보 ① st.cache_data · DB 수집 시각 확인
    #       ② data_backup/*.zip 에 faq.csv 오프라인 백업 확인
    #       ③ ev.or.kr + hyundai.com 웹 크롤링
    _faq_last_crawled = _load_faq_last_crawled()
    _faq_needs_update = (
        _faq_last_crawled is None
        or (datetime.now().date() - _faq_last_crawled.date()).days >= 7
    )
    if _faq_needs_update and "auto_faq_crawl_done" not in st.session_state:
        st.session_state["auto_faq_crawl_done"] = True

        # ① data_backup/ 폴더 오프라인 백업 ZIP 자동 확인 — 대용량 크롤링 생략
        _faq_backup = _find_faq_backup()
        if _faq_backup is not None:
            _faq_zip_path, _faq_df = _faq_backup
            try:
                _faq_items_bk = _df_to_faq_items(_faq_df)
                if _faq_items_bk:
                    save_faqs(_faq_items_bk)
                    load_faqs.clear()
                    _load_faq_last_crawled.clear()
                    st.info(f"📂 FAQ 데이터를 로컈 백업에서 로드했습니다. ({_faq_zip_path.name})")
            except Exception as _faq_be:
                st.warning(f"FAQ 백업 로드 실패, 크롤링으로 전환합니다: {_faq_be}")
                _faq_backup = None  # 크롤링으로 폴백

        # ② 백업 ZIP 없거나 로드 실패 시 웹 크롤링
        if _faq_backup is None:
            with st.spinner("📡 FAQ 데이터를 수집하고 있습니다 (ev.or.kr · hyundai.com)..."):
                try:
                    _faq_items = crawl_all_faqs()
                    if _faq_items:
                        save_faqs(_faq_items)
                        load_faqs.clear()
                        _load_faq_last_crawled.clear()
                except Exception as _faq_e:
                    st.warning(f"FAQ 자동 수집 실패 (기존 데이터로 표시): {_faq_e}")

    _faqs    = st.session_state.get("faqs_override") or load_faqs()
    _fsearch = st.text_input(
        "검색어",
        placeholder="예: 충전 시간, 보조금, 안전성 ...",
        label_visibility="collapsed",
    )
    _flist = [
        (q, a) for q, a in _faqs
        if not _fsearch
        or _fsearch.lower() in q.lower()
        or _fsearch.lower() in (a or "").lower()
    ]
    if not _flist:
        st.info("검색 결과가 없습니다.")
    else:
        for q, a in _flist:
            with st.expander(f"Q. {q}"):
                st.write(a)
    st.caption(f"총 {len(_faqs)}개 항목  ·  출처: faq 테이블")
    st.stop()

# ── 이하: 📈 수소차 등록현황 페이지 ───────────────────────────
# ──────────────────────────────────────────────────────────────
# 메인 헤더
# ──────────────────────────────────────────────────────────────
st.title("📈 수소차 등록 현황 대시보드")
st.caption(
    f"선택 지역: **{selected_region}**  ·  기간: **{year_label(start_year)} ~ {year_label(end_year)}**"
)


# ──────────────────────────────────────────────────────────────
# 상단 메트릭
# ──────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
m1.metric(f"{selected_region} 누적 등록수 ({year_label(end_year)} 기준)",  f"{selected_count:,} 대")
m2.metric(f"전국 누적 등록수 ({year_label(end_year)} 기준)",                f"{nation_total:,} 대")
m3.metric("전국 대비 비중",                                                f"{ratio:.2f} %")

st.divider()


# ──────────────────────────────────────────────────────────────
# 1. 연도별 등록 현황 선형 그래프 (3선: 누적/신규/증가율)
# ──────────────────────────────────────────────────────────────
st.subheader(f"📈 {selected_region} 연도별 수소차 등록 현황")

if yearly.empty:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")
else:
    # 파생 지표 계산을 위해 start_year-1 한 해 앞 데이터도 포함 (end_year까지만)
    _ext_base = regs_df[
        (regs_df["stat_year"] >= start_year - 1) &
        (regs_df["stat_year"] <= end_year)
    ].copy()
    if selected_region == "전국":
        _yearly_ext = _ext_base.groupby("stat_year", as_index=False)["count"].sum()
    else:
        _yearly_ext = (
            _ext_base[_ext_base["region_name"] == selected_region]
            .groupby("stat_year", as_index=False)["count"].sum()
        )
    _yearly_ext = _yearly_ext.sort_values("stat_year").copy()
    _yearly_ext["신규등록"] = _yearly_ext["count"].diff()
    _yearly_ext["증가율"]   = _yearly_ext["count"].pct_change().mul(100).round(1)

    # start_year 이전 보조 행 제거 (파생 계산에만 사용)
    line_data = _yearly_ext[_yearly_ext["stat_year"] >= start_year].copy()
    line_data["year_str"] = line_data["stat_year"].apply(year_label)
    # end_year까지 x축 레이블 표시 (데이터 없는 연도도 포함)
    _data_max_year = int(line_data["stat_year"].max()) if not line_data.empty else start_year - 1
    if end_year > _data_max_year:
        _extra = pd.DataFrame([{
            "stat_year": y, "count": float("nan"),
            "신규등록": float("nan"), "증가율": float("nan"),
            "year_str": year_label(y)
        } for y in range(_data_max_year + 1, end_year + 1)])
        line_data = pd.concat([line_data, _extra], ignore_index=True)
    x_sort = line_data["year_str"].tolist()

    # 체크박스: 표시할 선 선택
    _cb1, _cb2, _cb3 = st.columns(3)
    _show_cum  = _cb1.checkbox("📈 누적 등록 대수",      value=True,  key="line_cb_cum")
    _show_new  = _cb2.checkbox("🆕 신규 등록 대수",      value=True,  key="line_cb_new")
    _show_rate = _cb3.checkbox("📊 전년 대비 증가율 (%)", value=False, key="line_cb_rate")

    _C_CUM  = "#2563eb"   # 파란색 — 누적
    _C_NEW  = "#16a34a"   # 초록색 — 신규
    _C_RATE = "#dc2626"   # 빨간색 — 증가율
    _PT     = 70          # 꼭지점 마커 크기
    _LW     = 2.5

    # ── 좌측 y축 레이어 (누적 + 신규, 단위: 등록 대수) ──────────
    _left_rows: list[dict] = []
    _color_domain, _color_range, _dash_domain, _dash_range = [], [], [], []

    if _show_cum:
        for _, r in line_data.dropna(subset=["count"]).iterrows():
            _left_rows.append({"year_str": r["year_str"], "val": r["count"],    "항목": "누적 등록 대수"})
        _color_domain.append("누적 등록 대수"); _color_range.append(_C_CUM)
        _dash_domain.append("누적 등록 대수");  _dash_range.append([0, 0])
    if _show_new:
        for _, r in line_data.dropna(subset=["신규등록"]).iterrows():
            _left_rows.append({"year_str": r["year_str"], "val": r["신규등록"], "항목": "신규 등록 대수"})
        _color_domain.append("신규 등록 대수"); _color_range.append(_C_NEW)
        _dash_domain.append("신규 등록 대수");  _dash_range.append([6, 3])

    _x_enc = alt.X("year_str:N", sort=x_sort, title=None, axis=alt.Axis(labelAngle=0))

    # 좌측 y축 스케일 기준 (누적 등록 최댓값) — 데이터 없을 때도 스케일 고정에 사용
    _left_max = int(_yearly_ext["count"].dropna().max()) if not _yearly_ext["count"].dropna().empty else 1

    if _left_rows:
        _ldf = pd.DataFrame(_left_rows)
        _cs  = alt.Scale(domain=_color_domain, range=_color_range)
        _ds  = alt.Scale(domain=_dash_domain,  range=_dash_range)
        _color_enc = alt.Color("항목:N", scale=_cs, legend=None)
        _dash_enc  = alt.StrokeDash("항목:N", scale=_ds, legend=None)
        _left_line  = alt.Chart(_ldf).mark_line(strokeWidth=_LW).encode(
            x=_x_enc, y=alt.Y("val:Q", title="등록 대수"),
            color=_color_enc, strokeDash=_dash_enc,
            tooltip=[alt.Tooltip("year_str:N", title="연도"),
                     alt.Tooltip("val:Q", title="등록 대수", format=","),
                     alt.Tooltip("항목:N", title="항목")],
        )
        _left_pts = alt.Chart(_ldf).mark_point(size=_PT, filled=True).encode(
            x=_x_enc, y=alt.Y("val:Q", axis=None), color=_color_enc,
        )
    else:
        # 등록 대수 항목 미선택 시에도 좌측 y축 고정 표시 (투명 더미 레이어)
        _dummy_ldf = pd.DataFrame([{"year_str": s, "val": 0.0} for s in x_sort])
        _left_line = alt.Chart(_dummy_ldf).mark_line(opacity=0).encode(
            x=_x_enc,
            y=alt.Y("val:Q", title="등록 대수",
                    scale=alt.Scale(domain=[0, _left_max * 1.1])),
        )
        _left_pts = None

    # ── 우측 y축 레이어 (전년 대비 증가율 %, 이중 축) ────────────
    if _show_rate:
        _rdf = line_data.dropna(subset=["증가율"])
        _rate_line = alt.Chart(_rdf).mark_line(
            color=_C_RATE, strokeWidth=_LW, strokeDash=[4, 2]
        ).encode(
            x=_x_enc,
            y=alt.Y("증가율:Q", title="전년 대비 증가율 (%)",
                    axis=alt.Axis(orient="right", labelExpr="datum.value + '%'")),
            tooltip=[alt.Tooltip("year_str:N", title="연도"),
                     alt.Tooltip("증가율:Q", title="증가율 (%)", format=".1f")],
        )
        _rate_pts = alt.Chart(_rdf).mark_point(
            color=_C_RATE, size=_PT, filled=True
        ).encode(
            x=_x_enc,
            y=alt.Y("증가율:Q", axis=None),
        )
        _right_chart = _rate_line + _rate_pts
    else:
        _right_chart = None

    # ── 최종 합성 — 좌측 y축(등록 대수)은 항상 포함 ─────────────
    if not _show_cum and not _show_new and not _show_rate:
        st.info("최소 하나의 항목을 선택하세요.")
    else:
        _all_layers = [_left_line]
        if _left_pts is not None:
            _all_layers.append(_left_pts)
        if _show_rate:
            _all_layers.extend([_rate_line, _rate_pts])
        _final = alt.layer(*_all_layers).resolve_scale(y="independent")

        st.altair_chart(_final.properties(height=380), use_container_width=True)

        # 범례 (Altair color legend 대신 HTML 인라인으로 표시)
        _leg = []
        if _show_cum:  _leg.append(f"<span style='color:{_C_CUM}'>━</span> 누적 등록 대수")
        if _show_new:  _leg.append(f"<span style='color:{_C_NEW}'>╌</span> 신규 등록 대수")
        if _show_rate: _leg.append(f"<span style='color:{_C_RATE}'>╌</span> 전년 대비 증가율 (%, 우측 축)")
        st.caption("  ·  ".join(_leg), unsafe_allow_html=True)

st.divider()


# ──────────────────────────────────────────────────────────────
# 2. 지역별 등록 현황 (바 차트 / 파이 차트 선택)
# ──────────────────────────────────────────────────────────────
st.subheader(f"📊 지역별 등록 현황 ({year_label(end_year)} 기준 누적)")

chart_type = st.radio(
    "차트 유형",
    ["바 차트", "원형 차트"],
    horizontal=True,
    label_visibility="collapsed",
)

# 전국 행 제외 — 전국 선택 시 모든 지역 강조, 특정 지역 선택 시 해당 지역만 강조
chart_df = rank_df.copy()
chart_df["percent"] = (chart_df["count"] / nation_total * 100).round(2) if nation_total else 0.0
chart_df["강조"] = chart_df["region_name"].apply(
    lambda x: "선택" if (selected_region == "전국" or x == selected_region) else "기타"
)

_COLOR_SEL   = "#5244ef"
_COLOR_OTHER = "#808895"
_SEL_PRED    = alt.FieldEqualPredicate(field="강조", equal="선택")

if chart_type == "바 차트":
    st.caption("전국 선택 시 모든 지역이 강조됩니다.")

    _bar_x = alt.X(
        "region_name:N",
        sort=[r for r in REGION_ORDER if r != "전국"],
        title=None,
        axis=alt.Axis(labelAngle=0),
    )
    _bar_base = alt.Chart(chart_df)

    bars = (
        _bar_base
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=_bar_x,
            y=alt.Y("count:Q", title="등록 대수"),
            color=alt.condition(
                _SEL_PRED,
                alt.value(_COLOR_SEL),
                alt.value(_COLOR_OTHER),
            ),
            tooltip=[
                alt.Tooltip("region_name:N", title="지역"),
                alt.Tooltip("count:Q",       title="등록 대수", format=","),
                alt.Tooltip("percent:Q",     title="비중 (%)",  format=".1f"),
            ],
        )
    )

    bar_pct_labels = (
        _bar_base
        .mark_text(dy=-6, size=11, color="#374151")
        .encode(
            x=_bar_x,
            y=alt.Y("count:Q"),
            text=alt.Text("percent:Q", format=".1f"),
        )
    )

    st.altair_chart(
        (bars + bar_pct_labels).properties(height=420),
        use_container_width=True,
    )

else:  # 원형 차트
    st.caption("전국 선택 시 모든 지역이 강조됩니다. 마우스 오버 시 지역·등록 대수·비중이 표시됩니다.")

    # 2% 미만 슬라이스는 레이블 생략 (겹침 방지)
    chart_df["label_text"] = chart_df.apply(
        lambda row: row["region_name"] if row["percent"] >= 2 else "", axis=1
    )

    # base를 공유하면 theta 스택이 한 번만 계산되어 arc·label 위치가 정확히 일치한다.
    base = (
        alt.Chart(chart_df)
        .encode(
            theta=alt.Theta("count:Q", stack=True),
            order=alt.Order("count:Q", sort="descending"),
        )
    )

    arc = base.mark_arc(outerRadius=130, innerRadius=50).encode(
        color=alt.condition(_SEL_PRED, alt.value(_COLOR_SEL), alt.value(_COLOR_OTHER)),
        opacity=alt.condition(_SEL_PRED, alt.value(1.0), alt.value(0.7)),
        tooltip=[
            alt.Tooltip("region_name:N", title="지역"),
            alt.Tooltip("count:Q",       title="등록 대수", format=","),
            alt.Tooltip("percent:Q",     title="비중 (%)",  format=".1f"),
        ],
    )

    label = base.mark_text(radius=155, size=10, color="#374151").encode(
        text=alt.Text("label_text:N"),
    )

    # 도넛 중앙에 강조 지역의 등록 대수 · 비중 표시
    if selected_region == "전국":
        _cx_count = nation_total
        _cx_pct   = 100.0
    else:
        _cx_row   = chart_df[chart_df["region_name"] == selected_region]
        _cx_count = int(_cx_row["count"].iloc[0])   if not _cx_row.empty else 0
        _cx_pct   = float(_cx_row["percent"].iloc[0]) if not _cx_row.empty else 0.0

    _cdf_name  = pd.DataFrame([{"v": 1, "txt": selected_region}])
    _cdf_count = pd.DataFrame([{"v": 1, "txt": f"{_cx_count:,}"}])
    _cdf_pct   = pd.DataFrame([{"v": 1, "txt": f"{_cx_pct:.1f}%"}])

    # radius=0 → 파이 중심점, dy로 위아래 줄 간격 조절
    _center_name = (
        alt.Chart(_cdf_name)
        .mark_text(radius=0, dy=-22, size=13, fontWeight="bold", color="#374151")
        .encode(theta=alt.Theta("v:Q"), text="txt:N")
    )
    _center_count = (
        alt.Chart(_cdf_count)
        .mark_text(radius=0, dy=0, size=15, fontWeight="bold", color="#374151")
        .encode(theta=alt.Theta("v:Q"), text="txt:N")
    )
    _center_pct = (
        alt.Chart(_cdf_pct)
        .mark_text(radius=0, dy=20, size=13, color="#6b7280")
        .encode(theta=alt.Theta("v:Q"), text="txt:N")
    )

    st.altair_chart(
        (arc + label + _center_name + _center_count + _center_pct).properties(height=380),
        use_container_width=True,
    )
