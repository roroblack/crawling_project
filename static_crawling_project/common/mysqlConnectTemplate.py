# path : common\\mysqlConnectTemplate.py
# module : common.mysqlConnectTemplate
# MySQL DB 연결 관리용 공통 모듈 (mysql-connector-python 기반)
# connect, close, commit, rollback 기능 제공

import mysql.connector      # 해당 모듈이 제공하는 모든 것을 임포트함
from contextlib import contextmanager  # 원하는 함수나 클래스만 임포트할 때 사용함
# from 모듈명 import 함수명 | 클래스명
from mysql.connector import Error  # mysql.connector 모듈에서 Error 클래스만 임포트함
from common.exceptions import DBException

class MySQLTemplate:
  # field
  HOST = 'localhost'    # 클라우드 public ip 지정
  PORT = 3306
  DB = 'mydb'
  USER = 'student'
  PASSWD = 'student80'
  
  @staticmethod
  @contextmanager    # app 관리자로 등록함
  def get_connection():
    conn = None
    try:
      conn = mysql.connector.connect(
        host=MySQLTemplate.HOST,
        port=MySQLTemplate.PORT,
        database=MySQLTemplate.DB,
        user=MySQLTemplate.USER,
        password=MySQLTemplate.PASSWD,
        autocommit=False       
      )
      yield conn
      conn.commit()
    except Error as e:
      if conn:
        conn.rollback()
      raise DBException(str(e))
    finally:
      if conn and conn.is_connected():
        conn.close()
    