# Streamlit 라이브러리를 st라는 이름으로 가져온다.
# Streamlit은 파이썬 코드로 웹 화면을 만들 수 있는 라이브러리이다.
import streamlit as st

# Plotly Express를 px라는 이름으로 가져온다.
# Plotly는 데이터를 그래프로 시각화할 때 사용한다.
import plotly.express as px

# db.py 파일에 작성된 init_table 함수를 가져온다.
# init_table()은 MySQL에 필요한 테이블이 없으면 자동 생성하는 역할을 한다.
from db import init_table

# scheduler_service.py 파일에서 크롤링 서비스와 스케줄러 관리 클래스를 가져온다.
from scheduler_service import CrawlService, SchedulerManager


# Streamlit 웹페이지의 기본 설정이다.
# page_title: 브라우저 탭에 표시될 제목
# layout="wide": 화면을 넓은 레이아웃으로 사용
st.set_page_config(
    page_title="자동 크롤러 만들기",
    layout="wide"
)


# 프로그램 시작 시 MySQL 테이블이 존재하는지 확인하고,
# 없으면 crawl_news 테이블을 생성한다.
init_table()


# Streamlit은 버튼 클릭이나 화면 갱신 시 코드가 위에서 아래로 다시 실행된다.
# 그래서 객체를 매번 새로 만들면 스케줄러가 중복 실행될 수 있다.
# st.session_state는 Streamlit 실행 중 값을 유지하는 저장 공간이다.
if "crawl_service" not in st.session_state:
    # CrawlService 객체를 처음 한 번만 생성해서 저장한다.
    st.session_state.crawl_service = CrawlService()


# 스케줄러 객체도 한 번만 생성해야 한다.
# 그렇지 않으면 새로고침할 때마다 스케줄러가 여러 개 실행될 수 있다.
if "scheduler_manager" not in st.session_state:
    # SchedulerManager 객체 생성
    st.session_state.scheduler_manager = SchedulerManager()

    # APScheduler를 시작한다.
    # 이 작업을 해야 interval, cron 작업이 실제로 실행된다.
    st.session_state.scheduler_manager.start()


# session_state에 저장된 CrawlService 객체를 service 변수에 담는다.
# 이후 service.run_crawling(), service.find_all()처럼 사용할 수 있다.
service = st.session_state.crawl_service

# session_state에 저장된 SchedulerManager 객체를 scheduler 변수에 담는다.
scheduler = st.session_state.scheduler_manager


# 웹페이지 상단 제목 출력
st.title("Streamlit + MySQL + APScheduler 자동 크롤러")


# 왼쪽 사이드바 영역을 만든다.
with st.sidebar:
    # 사이드바 제목
    st.header("크롤링 설정")

    # 슬라이더를 사용하여 크롤링할 데이터 개수를 선택한다.
    # 최소 5개, 최대 100개, 기본값 30개
    limit = st.slider("수집 개수", 5, 100, 30)

    # 사용자가 "즉시 크롤링 실행" 버튼을 클릭했는지 확인한다.
    if st.button("즉시 크롤링 실행"):
        # spinner는 작업 중임을 사용자에게 알려주는 로딩 표시이다.
        with st.spinner("크롤링 실행 중..."):
            # service.run_crawling(limit)는 실제 크롤링을 실행하고 MySQL에 저장한다.
            # 반환값 count는 저장된 데이터 개수이다.
            count = service.run_crawling(limit)

        # 크롤링 완료 후 성공 메시지를 출력한다.
        st.success(f"{count}건 수집 완료")

    # 구분선 출력
    st.divider()

    # Interval 스케줄링 영역 제목
    st.subheader("Interval 스케줄링")

    # 몇 분마다 자동 크롤링을 실행할지 입력받는다.
    # min_value=1: 최소 1분
    # max_value=1440: 최대 1440분, 즉 하루
    # value=10: 기본값 10분
    interval_minutes = st.number_input(
        "몇 분마다 실행",
        min_value=1,
        max_value=1440,
        value=10
    )

    # Interval 작업 등록 버튼 클릭 여부 확인
    if st.button("Interval 작업 등록"):
        # 지정한 분 간격으로 자동 크롤링 작업을 등록한다.
        scheduler.add_interval_job(interval_minutes, limit)

        # 등록 완료 메시지 출력
        st.success(f"{interval_minutes}분마다 자동 크롤링 등록 완료")

    # 구분선 출력
    st.divider()

    # Cron 스케줄링 영역 제목
    st.subheader("Cron 스케줄링")

    # 매일 몇 시에 실행할지 입력받는다.
    # 0~23 사이의 값을 입력한다.
    cron_hour = st.number_input("실행 시", 0, 23, 9)

    # 매일 몇 분에 실행할지 입력받는다.
    # 0~59 사이의 값을 입력한다.
    cron_minute = st.number_input("실행 분", 0, 59, 0)

    # Cron 작업 등록 버튼 클릭 여부 확인
    if st.button("Cron 작업 등록"):
        # 매일 지정된 시각에 자동 크롤링 작업을 등록한다.
        scheduler.add_cron_job(cron_hour, cron_minute, limit)

        # 등록 완료 메시지 출력
        st.success(f"매일 {cron_hour}시 {cron_minute}분 자동 크롤링 등록 완료")

    # 스케줄 작업 삭제 버튼 클릭 여부 확인
    if st.button("스케줄 작업 삭제"):
        # 현재 등록된 자동 크롤링 작업을 삭제한다.
        scheduler.remove_job()

        # 삭제 완료 메시지 출력
        st.warning("자동 크롤링 작업이 삭제되었습니다.")


# 메인 화면에 탭 3개를 만든다.
# tab1: 수집된 데이터 조회
# tab2: 수집 통계 그래프
# tab3: 현재 등록된 스케줄 확인
tab1, tab2, tab3 = st.tabs(
    ["수집 데이터", "수집 통계", "스케줄 상태"]
)


# 첫 번째 탭: MySQL에 저장된 크롤링 데이터 출력
with tab1:
    # 소제목 출력
    st.subheader("MySQL 저장 데이터")

    # MySQL에서 전체 크롤링 데이터를 조회한다.
    df = service.find_all()

    # 조회 결과가 비어 있는지 확인한다.
    if df.empty:
        # 데이터가 없으면 안내 메시지 출력
        st.info("아직 저장된 데이터가 없습니다.")
    else:
        # 데이터가 있으면 표 형태로 출력
        # use_container_width=True는 화면 너비에 맞게 표를 보여준다.
        st.dataframe(df, use_container_width=True)


# 두 번째 탭: 수집량 통계 시각화
with tab2:
    # 소제목 출력
    st.subheader("크롤링 수집량 시각화")

    # MySQL에서 시간별 수집 건수를 조회한다.
    stat_df = service.find_count_by_time()

    # 통계 데이터가 없는지 확인
    if stat_df.empty:
        # 시각화할 데이터가 없으면 안내 메시지 출력
        st.info("시각화할 데이터가 없습니다.")
    else:
        # Plotly 막대그래프 생성
        # x축: 크롤링 시간
        # y축: 수집 건수
        # text="count": 막대 위에 수집 건수 표시
        fig = px.bar(
            stat_df,
            x="crawl_time",
            y="count",
            title="시간별 크롤링 수집 건수",
            text="count"
        )

        # 생성한 그래프를 Streamlit 화면에 출력
        st.plotly_chart(fig, use_container_width=True)


# 세 번째 탭: 현재 등록된 APScheduler 작업 상태 출력
with tab3:
    # 소제목 출력
    st.subheader("현재 등록된 스케줄 작업")

    # 현재 등록된 스케줄 작업 목록을 가져온다.
    jobs = scheduler.get_jobs()

    # 등록된 작업이 없으면
    if not jobs:
        # 안내 메시지 출력
        st.info("등록된 스케줄 작업이 없습니다.")
    else:
        # 등록된 작업이 있으면 하나씩 출력
        for job in jobs:
            # 작업 ID 출력
            st.write(f"작업 ID: {job.id}")

            # 다음 실행 예정 시간 출력
            st.write(f"다음 실행 시간: {job.next_run_time}")

            # 구분선 출력
            st.write("---")