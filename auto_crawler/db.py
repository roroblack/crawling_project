# 운영체제 환경변수 값을 읽기 위해 os 모듈을 가져온다.
# 예: DB_HOST, DB_USER, DB_PASSWORD 같은 값을 읽을 때 사용한다.
import os

# .env 파일에 작성된 설정값을 파이썬 환경변수로 불러오기 위해 사용한다.
# .env 파일에는 DB 접속 정보처럼 코드에 직접 쓰기 부담스러운 값을 저장한다.
from dotenv import load_dotenv

# create_engine은 SQLAlchemy에서 DB 연결 엔진을 만드는 함수이다.
# text는 문자열 SQL문을 SQLAlchemy가 실행 가능한 SQL 객체로 변환할 때 사용한다.
from sqlalchemy import create_engine, text


# 현재 프로젝트 폴더의 .env 파일을 읽어온다.
# 이 코드를 실행해야 os.getenv("DB_HOST")처럼 .env 값을 가져올 수 있다.
load_dotenv()


# MySQL 데이터베이스 연결 엔진을 생성하는 함수이다.
# 다른 파일에서 get_engine()을 호출하면 MySQL에 연결할 수 있는 객체를 받을 수 있다.
def get_engine():
    # .env 파일에서 DB_HOST 값을 읽는다.
    # 값이 없으면 기본값으로 "localhost"를 사용한다.
    # localhost는 현재 내 컴퓨터를 의미한다.
    host = os.getenv("DB_HOST", "localhost")

    # .env 파일에서 DB_PORT 값을 읽는다.
    # 값이 없으면 MySQL 기본 포트인 "3306"을 사용한다.
    port = os.getenv("DB_PORT", "3306")

    # .env 파일에서 DB_USER 값을 읽는다.
    # 값이 없으면 기본값으로 "student"를 사용한다.
    user = os.getenv("DB_USER", "student")

    # .env 파일에서 DB_PASSWORD 값을 읽는다.
    # 값이 없으면 기본값으로 "Student80*"를 사용한다.
    password = os.getenv("DB_PASSWORD", "Student80*")

    # .env 파일에서 DB_NAME 값을 읽는다.
    # 값이 없으면 기본값으로 "mydb"를 사용한다.
    db_name = os.getenv("DB_NAME", "mydb")

    # SQLAlchemy가 MySQL에 접속하기 위한 DB URL을 만든다.
    #
    # 형식:
    # mysql+pymysql://사용자명:비밀번호@호스트:포트/DB명?charset=utf8mb4
    #
    # mysql+pymysql:
    #   MySQL DB에 pymysql 드라이버를 사용해서 접속한다는 뜻이다.
    #
    # charset=utf8mb4:
    #   한글, 이모지, 특수문자까지 안정적으로 저장하기 위한 문자셋 설정이다.
    db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4"

    # create_engine()은 DB 연결을 관리하는 엔진 객체를 만든다.
    #
    # pool_pre_ping=True:
    #   DB 연결을 사용하기 전에 연결이 살아 있는지 확인한다.
    #   오래된 연결이 끊겨서 발생하는 오류를 줄일 수 있다.
    return create_engine(db_url, pool_pre_ping=True)


# 크롤링 데이터를 저장할 테이블을 생성하는 함수이다.
# 앱 실행 시 한 번 호출하면, 테이블이 없을 경우 자동으로 생성된다.
def init_table():
    # MySQL 연결 엔진을 가져온다.
    engine = get_engine()

    # crawl_news 테이블 생성 SQL문이다.
    #
    # CREATE TABLE IF NOT EXISTS:
    #   테이블이 없을 때만 생성한다.
    #   이미 테이블이 있으면 오류 없이 넘어간다.
    #
    # id:
    #   각 데이터의 고유 번호이다.
    #   BIGINT는 큰 정수형이다.
    #   AUTO_INCREMENT는 데이터가 추가될 때 자동으로 1씩 증가한다.
    #   PRIMARY KEY는 기본키로, 각 행을 구분하는 고유값이다.
    #
    # title:
    #   크롤링한 뉴스 제목을 저장한다.
    #   VARCHAR(500)은 최대 500자 문자열이다.
    #   NOT NULL은 반드시 값이 있어야 한다는 뜻이다.
    #
    # link:
    #   뉴스 링크 주소를 저장한다.
    #   TEXT는 긴 문자열 저장에 사용한다.
    #
    # source_url:
    #   크롤링을 수행한 원본 사이트 주소를 저장한다.
    #
    # crawled_at:
    #   크롤링한 날짜와 시간을 저장한다.
    #   DATETIME은 날짜와 시간을 함께 저장하는 MySQL 자료형이다.
    #   NOT NULL은 반드시 값이 있어야 한다는 뜻이다.
    sql = """
    CREATE TABLE IF NOT EXISTS crawl_news (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        link TEXT,
        source_url TEXT,
        crawled_at DATETIME NOT NULL
    )
    """

    # engine.begin()은 DB 트랜잭션을 시작한다.
    #
    # with 구문:
    #   작업이 끝나면 연결을 자동으로 정리한다.
    #
    # 정상 실행:
    #   자동 commit 처리된다.
    #
    # 오류 발생:
    #   자동 rollback 처리된다.
    with engine.begin() as conn:
        # text(sql)은 문자열 SQL을 실행 가능한 SQLAlchemy SQL 객체로 변환한다.
        # conn.execute()는 실제로 SQL문을 DB에 실행한다.
        conn.execute(text(sql))