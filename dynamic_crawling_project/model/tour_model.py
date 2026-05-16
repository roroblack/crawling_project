# path : model\\tour_model.py
# module : model.tour_model
# MySQL DB에 TourInfo 객체 정보를 CRUD 처리하는 비지니스 로직 모델 클래스 정의 스크립트

from common.mysqlConnectTemplate import MySQLTemplate
from common.exceptions import DBException

class TourModel:
  # method
  # insert method
  def insert_tour(self, tp_tour):
    '''
    tp_tour: tuple(rank, name, description, category, score)
    '''
    sql = '''
    insert into tour (`rank`, name, description, category, score)
    values (%s, %s, %s, %s, %s)
    '''
    try:
      with MySQLTemplate.get_connection() as conn:
        with conn.cursor() as cursor:
          cursor.execute(sql, tp_tour)
    except DBException as e:
      print('insert_tour error : ', e)
  # insert_tour --------------------------------------
  
  # delete all method
  def delete_all(self):    
    sql = 'delete from tour'
    
    try:
      with MySQLTemplate.get_connection() as conn:
        with conn.cursor() as cursor:
          cursor.execute(sql)
    except DBException as e:
      print('delete_all error : ', e)
  # delete_all --------------------------------------
  
  # select all method
  def select_all(self):
    sql = 'select * from tour'
    try:
      with MySQLTemplate.get_connection() as conn:
        with conn.cursor() as cursor:
          cursor.execute(sql)
          return cursor.fetchall()
    except DBException as e:
      print('select_all error : ', e)
      return []
  # select_all ----------------------------------
  
  # select one method
  def select_one(self, rank):
    '''
    rank: tuple(rank,)
    '''
    sql = '''
    select * from tour
    where `rank` = %s
    '''
    try:
      with MySQLTemplate.get_connection() as conn:
        with conn.cursor() as cursor:
          cursor.execute(sql, (rank,))
          return cursor.fetchone()
    except DBException as e:
      print('select_one error : ', e)
      return None
  # select_one -----------------------------------------
# TourModel -----------------------  