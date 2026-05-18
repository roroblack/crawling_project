import os

import pandas as pd
from dataclasses import asdict, fields
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from common.constants import ALLOWED_MODELS

# DB 작업을 처리하는 클래스이다.
class Repository:
    def __init__(self):
        self.engine = self._get_engine()

    # DB 연결을 관리하는 엔진 객체를 만들고, 이를 반환하는 함수이다.
    def _get_engine(self):
        # 프로젝트 폴더의 .env 파일을 불러온다.
        load_dotenv()

        # .env 파일에서 DB 환경 변수를 불러온다.
        # 불러올 수 없는 경우 기본값을 사용한다.
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', 3306)
        user = os.getenv('DB_USER', 'student')
        password = os.getenv('DB_PASSWORD', 'Student80*')
        db_name = os.getenv('DB_NAME', 'mydb')

        # DB에 접속하기 위한 DB URL을 만든다.
        # 한글을 안전하게 저장하기 위해 utf8mb4 문자셋을 사용한다.
        db_url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4'

        # DB 연결을 관리하는 엔진 객체를 만들고, 이를 반환한다.
        # pool_pre_ping 옵션
        #   DB에 연결하기 전에 연결이 살아 있는지 확인한다.
        #   연결이 유효하면 그대로 사용하고, 아니면 새 연결을 만든다.
        #   매 연결마다 약간의 오버헤드가 있지만, 연결 문제로 인한 오류를 줄여준다.
        return create_engine(db_url, pool_pre_ping=True)
    
    # 아이템 리스트를 DB에 저장하는 함수이다.
    def save_items(self, items: list):
        # 아이템 리스트인지 확인한다.
        if not isinstance(items, list):
            raise TypeError('Items should be a list.')
        
        # 아이템 리스트가 비어 있는지 확인한다.
        if not items:
            raise TypeError('Items is empty.')
        
        # 아이템 리스트에 허용되지 않은 모델이 포함되어 있는지 확인한다.
        if not all(isinstance(item, ALLOWED_MODELS) for item in items):
            raise TypeError('Items contains an unsupported model type.')

        # 아이템의 모델에 따라 DB에 추가하는 SQL을 만든다.
        # SQL Injection 위험을 낮추기 위해 바인딩 방식을 사용한다.
        # 1. 자동차 등록 현황인 경우
        model_class = type(items[0])
        if isinstance(items[0], ALLOWED_MODELS[0]):
            sql = '''
            INSERT INTO car_registrations (
                region_id,
                stat_year,
                count,
                crawled_at
            )
            VALUES (
                :region_id,
                :stat_year,
                :count,
                :crawled_at
            )
            '''
        # 2. FAQ인 경우
        elif isinstance(items[0], ALLOWED_MODELS[1]):
            sql = '''
            INSERT INTO faq (
                question,
                answer,
                crawled_at
            )
            VALUES (
                :question,
                :answer,
                :crawled_at
            )
            '''
        # 3. 충전소인 경우
        elif isinstance(items[0], ALLOWED_MODELS[2]):
            sql = '''
            INSERT INTO hydrogen_charging_station (
                region_id,
                station_name,
                address,
                lat,
                lon,
                crawled_at
            )
            VALUES (
                :region_id,
                :station_name,
                :address,
                :lat,
                :lon,
                :crawled_at
            )
            '''
        # 예외 처리
        else:
            return
        
        # 데이터 모델 클래스의 컬럼명을 불러온다.
        column_names = [column.name for column in fields(model_class)]

        # 아이템 리스트를 파라미터 리스트로 변환한다.
        params_list = [self._item_to_params(item, column_names) for item in items]
        print(params_list)

        # begin() : 한 블록 안에서 트랜잭션을 처리한다.
        #   정상 종료되면 자동으로 commit 처리된다.
        #   예외가 생기면 자동으로 rollback 처리된다.
        with self.engine.begin() as conn:
            # SQL에 파라미터 리스트를 바인딩하여 처리한다.
            # text() : 문자열 SQL을 SQLAlchemy가 처리할 수 있는 객체로 바꾼다.
            # execute() : SQL을 실제 DB에 실행한다.
            result = conn.execute(text(sql), params_list)
    
    # 아이템을 파라미터로 변환하는 함수이다.
    def _item_to_params(self, item, column_names: list[str]) -> dict:
        raw = asdict(item)
        return {k: v for k, v in raw.items() if k in column_names}
    
    # DB의 지정한 테이블에서 저장된 전체 데이터를 조회하여 반환하는 함수이다.
    def find_all(self, model_class) -> pd.DataFrame:
        # 모델 클래스로 데이터를 조회할 테이블을 지정한다.
        # 데이터를 조회할 테이블에 따라 SQL을 만든다.
        # 1. 자동차 등록 현황인 경우
        if issubclass(model_class, ALLOWED_MODELS[0]):
            sql = '''
            SELECT
                region_id,
                stat_year,
                count,
                crawled_at
            FROM car_registrations
            '''
        # 2. FAQ인 경우
        elif issubclass(model_class, ALLOWED_MODELS[1]):
            sql = '''
            SELECT
                faq_id,
                question,
                answer,
                crawled_at
            FROM faq
            '''
        # 3. 충전소인 경우
        elif issubclass(model_class, ALLOWED_MODELS[2]):
            sql = '''
            SELECT
                region_id,
                station_name,
                address,
                lat,
                lon,
                crawled_at
            FROM hydrogen_charging_station
            '''
        # 예외 처리
        else:
            return None

        # SQL 실행 결과를 pandas DataFrame으로 반환한다.
        return pd.read_sql(sql, self.engine)
