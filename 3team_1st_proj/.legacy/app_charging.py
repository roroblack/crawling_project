import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from sqlalchemy import text

from db import get_engine

st.set_page_config(
    page_title="수소충전소 지도",
    page_icon="⛽",
    layout="wide",
)

st.title("⛽ 전국 수소충전소 현황")


@st.cache_data(ttl=300)
def load_stations() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                h.station_name,
                h.address,
                h.lat,
                h.lon,
                r.region_name
            FROM hydrogen_charging_station h
            JOIN regions r ON h.region_id = r.region_id
            WHERE h.lat IS NOT NULL AND h.lon IS NOT NULL
            ORDER BY r.region_name, h.station_name
        """))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    return df


df = load_stations()

if df.empty:
    st.warning("충전소 데이터가 없습니다. crawler_station.py를 먼저 실행해주세요.")
    st.stop()

# ── 사이드바: 지역 필터 ─────────────────────────────────────
st.sidebar.header("필터")
regions = ["전체"] + sorted(df["region_name"].unique().tolist())
selected = st.sidebar.selectbox("시도 선택", regions)

if selected != "전체":
    filtered = df[df["region_name"] == selected]
else:
    filtered = df

st.sidebar.markdown(f"**표시 중: {len(filtered)}개 충전소**")

# ── 지도 ────────────────────────────────────────────────────
center_lat = filtered["lat"].mean()
center_lon = filtered["lon"].mean()
zoom = 10 if selected != "전체" else 7

m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="CartoDB positron")

cluster = MarkerCluster(
    options={"maxClusterRadius": 50, "disableClusteringAtZoom": 13}
).add_to(m)

for _, row in filtered.iterrows():
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=7,
        color="#0068C9",
        fill=True,
        fill_color="#0068C9",
        fill_opacity=0.85,
        popup=folium.Popup(
            f"<b>{row['station_name']}</b><br>{row['address'] or ''}",
            max_width=250,
        ),
        tooltip=row["station_name"],
    ).add_to(cluster)

st_folium(m, width=None, height=580, use_container_width=True)

# ── 테이블 ───────────────────────────────────────────────────
with st.expander("📋 목록 보기", expanded=False):
    st.dataframe(
        filtered[["region_name", "station_name", "address", "lat", "lon"]]
        .rename(columns={
            "region_name":  "시도",
            "station_name": "충전소명",
            "address":      "주소",
            "lat":          "위도",
            "lon":          "경도",
        })
        .reset_index(drop=True),
        use_container_width=True,
        height=300,
    )
