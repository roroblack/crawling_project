이 프로젝트는 Cron, schedule, APScheduler 기반 스케줄링 개념을 반영한 자동 크롤러입니다. 
Cron 형식, Windows 작업 스케줄러, schedule 모듈, APScheduler의 interval / cron / date 실행 방식입니다. 
특히 APScheduler는 작업 추가, 시작, 일시정지, 삭제 등 운영형 스케줄링에 적합하므로 이 프로젝트에서는 BackgroundScheduler를 사용합니다.

1. 프로젝트 구조
auto_crawler/
│- .venv
├─ app.py
├─ crawler.py
├─ db.py
├─ models.py
├─ scheduler_service.py
├─ requirements.txt
└─ .env

실행 방법 :
cd auto_crawler_project
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

streamlit run app.py