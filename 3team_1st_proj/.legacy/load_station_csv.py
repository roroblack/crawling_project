"""
수소 충전소 CSV → DB 적재 스크립트

사용법:
  1. data.go.kr 에서 CSV 다운로드 후 이 스크립트와 같은 폴더에 저장
  2. CSV_PATH 변수에 파일명 입력
  3. python load_station_csv.py 실행

지원하는 CSV 컬럼명 (대소문자 무관, 자동 매핑):
  충전소명 / 시설명 / station_name / name
  주소     / 소재지 / address
  위도     / lat
  경도     / lon  / lng
  시도     / 시도명 / region / 지역
"""

import os
import sys
import pandas as pd
from sqlalchemy import text
from db import get_engine, REGIONS

# ── 설정 ──────────────────────────────────────────────────────
# 다운받은 CSV 파일 경로를 여기에 입력하세요
CSV_PATH = "hydrogen_stations.csv"

# CSV 인코딩 (보통 euc-kr 또는 utf-8)
ENCODING = "euc-kr"
# ──────────────────────────────────────────────────────────────

# 시도명 -> region_name 정규화 테이블
# (CSV에 '서울특별시', '서울시' 등 다양하게 올 수 있음)
REGION_MAP = {r: r for r in REGIONS}


def normalize_region(raw: str) -> str:
    """'서울특별시' -> '서울' 변환"""
    if pd.isna(raw):
        return "전국"
    raw = str(raw).strip()
    for key in REGION_MAP:
        if raw.startswith(key):
            return REGION_MAP[key]
    return raw[:2]  # 앞 2글자로 매핑 시도


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """컬럼 후보 목록에서 실제 존재하는 컬럼명 반환"""
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


def load_csv(path: str) -> pd.DataFrame:
    """CSV 읽기 (인코딩 자동 시도)"""
    for enc in [ENCODING, "utf-8", "cp949"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"[OK] CSV 읽기 성공 (인코딩: {enc}), {len(df)}행")
            return df
        except Exception:
            continue
    print("[ERROR] CSV 읽기 실패. ENCODING 변수를 확인하세요.")
    sys.exit(1)


def main():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] 파일이 없습니다: {CSV_PATH}")
        print("  - data.go.kr에서 수소충전소 CSV를 다운받아 이 폴더에 저장하세요.")
        print(f"  - 저장 파일명: {CSV_PATH}")
        sys.exit(1)

    df = load_csv(CSV_PATH)
    print(f"컬럼 목록: {list(df.columns)}")

    # 컬럼 자동 매핑
    col_name    = find_col(df, ["충전소명", "시설명", "station_name", "name", "충전소 명", "소재지명"])
    col_address = find_col(df, ["주소", "소재지", "address", "도로명주소", "지번주소"])
    col_lat     = find_col(df, ["위도", "lat", "latitude", "y좌표", "y_coord"])
    col_lon     = find_col(df, ["경도", "lon", "lng", "longitude", "x좌표", "x_coord"])
    col_region  = find_col(df, ["시도", "시도명", "region", "지역", "광역시도"])

    print(f"\n[컬럼 매핑 결과]")
    print(f"  충전소명: {col_name}")
    print(f"  주소:     {col_address}")
    print(f"  위도:     {col_lat}")
    print(f"  경도:     {col_lon}")
    print(f"  시도:     {col_region}")

    if col_name is None:
        print("\n[ERROR] 충전소명 컬럼을 찾지 못했습니다. 위 컬럼 목록을 확인하세요.")
        sys.exit(1)

    engine = get_engine()

    # 1. regions 테이블에서 region_name → region_id 매핑 로드
    with engine.connect() as conn:
        result = conn.execute(text("SELECT region_id, region_name FROM regions"))
        region_id_map = {row.region_name: row.region_id for row in result}

    if not region_id_map:
        print("[ERROR] regions 테이블이 비어 있습니다. init_table()을 먼저 실행하세요.")
        sys.exit(1)

    print(f"\n[DB] regions 로드: {list(region_id_map.keys())}")

    # 2. 행별로 INSERT
    inserted = 0
    skipped  = 0

    with engine.begin() as conn:
        for _, row in df.iterrows():
            # 충전소명
            station_name = str(row[col_name]).strip() if col_name else "알 수 없음"

            # 주소
            address = str(row[col_address]).strip() if col_address and not pd.isna(row[col_address]) else None

            # 위도/경도
            try:
                lat = float(row[col_lat]) if col_lat and not pd.isna(row[col_lat]) else None
            except (ValueError, TypeError):
                lat = None
            try:
                lon = float(row[col_lon]) if col_lon and not pd.isna(row[col_lon]) else None
            except (ValueError, TypeError):
                lon = None

            # 시도 → region_id
            raw_region = str(row[col_region]).strip() if col_region and not pd.isna(row[col_region]) else (
                address[:3] if address else ""
            )
            region_name = normalize_region(raw_region)
            region_id   = region_id_map.get(region_name)

            if region_id is None:
                skipped += 1
                continue

            conn.execute(text("""
                INSERT IGNORE INTO hydrogen_charging_station
                    (region_id, station_name, address, lat, lon)
                VALUES
                    (:region_id, :station_name, :address, :lat, :lon)
            """), {
                "region_id":    region_id,
                "station_name": station_name,
                "address":      address,
                "lat":          lat,
                "lon":          lon,
            })
            inserted += 1

    print(f"\n[완료] 삽입: {inserted}개 / 건너뜀(지역 미매핑): {skipped}개")


if __name__ == "__main__":
    main()
