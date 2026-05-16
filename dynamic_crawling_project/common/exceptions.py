# path : common\\exceptions.py
# module : common.exceptions


class DBException (Exception):
  '''DB 처리 공통 예외 Custom Exception'''
  
  def __init__(self, message: str):   # 매개변수에 자료형 지정할 수 있음 - 매개변수명: 자료형
    super().__init__(f'[DB ERROR] {message}')
    