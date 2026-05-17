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
from db import fetch_registrations, fetch_stations, fetch_faqs, REGION_ORDER


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
     "현대 넷쒑 기준 1회 완충(약 6.33kg) 시 약 609km를 주행할 수 있습니다."),
    ("수소차 구매 보조금은 얼마인가요?",
     "2026년 기준 국비 2,250만원 + 지자체 보조금 1,000만원 내외가 지원되며, 지역에 따라 차이가 있습니다."),
    ("수소충전소는 전국에 몇 곳 있나요?",
     "한국가스안전공사 기준 약 270여 곳이 운영 중이며, 매년 확대되고 있습니다."),
    ("수소차는 안전한가요?",
     "수소탱크는 700bar 압력과 총격 테스트를 통과한 고강도 탄소섬유 복합소재로 제작되어 매우 안전합니다."),
]


@st.cache_data(ttl=300)
def load_faqs() -> list[tuple[str, str]]:
    """드비 faq 테이블 조회; 비어 있으면 FAQ_FALLBACK 반환"""
    rows = fetch_faqs()
    if not rows:
        return FAQ_FALLBACK
    return rows


# ──────────────────────────────────────────────────────────────
# 사이드바 — 필터
# ──────────────────────────────────────────────────────────────
st.sidebar.title("🔍 필터")

# DB에서 로드된 연도 범위를 슬라이더 기본값으로 사용한다.
year_min        = int(regs_df["stat_year"].min())
year_max        = int(regs_df["stat_year"].max())
# DB에 실제로 데이터가 있는 시도만 selectbox에 표시한다.
available       = set(regs_df["region_name"].unique().tolist())
# REGION_ORDER 기준으로 정렬한 선택 가능한 지역 목록이다 (전국 + 데이터 있는 시도).
region_options  = [r for r in REGION_ORDER if r == "전국" or r in available]

default_years   = (year_min, year_max)
default_region  = "전국"

# 1) 등록 기간 선택
year_range      = st.sidebar.slider(
    "등록 기간 선택",
    min_value=year_min,
    max_value=year_max,
    value=default_years,
    step=1,
    key="year_range",
)

# 2) 지역 선택 (전국 + 17개 시도, 고정 순서)
selected_region = st.sidebar.selectbox(
    "지역 선택",
    region_options,
    index=region_options.index(default_region),
    key="selected_region",
)

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

# 지역별 합계 (선택 기간) + “전국” 합계 행 추가
# 남저용 바 차트와 비율 메트릭에 공통으로 사용하는 지역별 합계 테이블이다.
rank_df = (
    filtered.groupby("region_name", as_index=False)["count"]
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
# 메인 헤더
# ──────────────────────────────────────────────────────────────
st.title("💧 수소차 등록 현황 대시보드")
st.caption(
    f"선택 지역: **{selected_region}**  ·  기간: **{start_year} ~ {end_year}**"
)


# ──────────────────────────────────────────────────────────────
# 상단 메트릭
# ──────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
m1.metric(f"{selected_region} 등록수 (기간 합계)",  f"{selected_count:,} 대")
m2.metric("전국 등록수 (기간 합계)",                f"{nation_total:,} 대")
m3.metric("전국 대비 비중",                         f"{ratio:.2f} %")

st.divider()


# ──────────────────────────────────────────────────────────────
# 1. 연도별 등록 현황 선형 그래프
# ──────────────────────────────────────────────────────────────
st.subheader(f"📈 {selected_region} 연도별 수소차 등록 현황")

if yearly.empty:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")
else:
    line_df         = yearly.set_index      ("stat_year")
    line_df.index   = line_df.index.astype  (str)   # x축을 정수가 아닌 문자열 연도로
    line_df.columns = ["등록 대수"]
    st.line_chart(line_df, height=320)

st.divider()


# ──────────────────────────────────────────────────────────────
# 2. 지역별 등록 순위 바 그래프 (전국 포함)
# ──────────────────────────────────────────────────────────────
st.subheader(f"🏆 지역별 등록 현황 ({start_year}~{end_year} 합계)")
st.caption  ("표시 순서: 전국 → 서울 → 경기 → 광역시 → 도. 선택한 지역은 강조 표시됩니다.")

bar_df          = rank_df_with_nation.copy()
bar_df["강조"]  = bar_df["region_name"].apply(
    lambda x: "선택" if x == selected_region else "기타"
)

bar_chart = (
    alt.Chart(bar_df)
    .mark_bar(cornerRadiusEnd=4)
    .encode(
        x=alt.X(
            "region_name:N",
            sort=REGION_ORDER,
            title=None,
            axis=alt.Axis(labelAngle=0),
        ),
        y=alt.Y("count:Q", title="등록 대수"),
        color=alt.Color(
            "강조:N",
            scale=alt.Scale(
                domain=["선택", "기타"],
                range=["#ef4444", "#9ca3af"],   # 선택 = 빨강, 기타 = 회색
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("region_name:N", title="지역"),
            alt.Tooltip("count:Q", title="등록 대수", format=","),
        ],
    )
    .properties(height=420)
)
st.altair_chart(bar_chart, use_container_width=True)

st.divider()


# ──────────────────────────────────────────────────────────────
# 3. 수소차 충전소 지도
# ──────────────────────────────────────────────────────────────
st.subheader(f"🗺️ {selected_region} 수소충전소 지도")

if selected_region == "전국":
    map_stations = stations_df
else:
    map_stations = stations_df[stations_df["region_name"] == selected_region]

st.caption(f"표시된 충전소: **{len(map_stations):,}** 곳")

if map_stations.empty:
    st.info("해당 지역의 충전소 데이터가 없습니다.")
else:
    center_lat  = map_stations["lat"].mean()
    center_lon  = map_stations["lon"].mean()
    zoom        = 7 if selected_region == "전국" else 10

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
    for _, row in map_stations.iterrows():
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(
                f"<b>{row['station_name']}</b><br>{row['address'] or ''}",
                max_width=260,
            ),
            tooltip=row["station_name"],
            icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
        ).add_to(m)

    st_folium(m, height=480, use_container_width=True, returned_objects=[])


st.divider()


# ──────────────────────────────────────────────────────────────
# 4. FAQ
# ──────────────────────────────────────────────────────────────
st.subheader("💬 자주 묻는 질문 (FAQ)")

faqs        = st.session_state.get("faqs_override") or load_faqs()
faq_search  = st.text_input(
    "검색어",
    placeholder="예: 충전 시간, 보조금, 안전성 ...",
    label_visibility="collapsed",
)

filtered_faqs = [
    (q, a) for q, a in faqs
    if not faq_search
    or faq_search.lower() in q.lower()
    or faq_search.lower() in (a or "").lower()
]

if not filtered_faqs:
    st.info("검색 결과가 없습니다.")
else:
    for q, a in filtered_faqs:
        with st.expander(f"Q. {q}"):
            st.write(a)

st.caption(
    f"총 {len(faqs)}개 항목  ·  "
    f"출처: faq 테이블 (현재 더미 데이터 표시 중 — 크롤러 적재 후 자동 교체)"
)
