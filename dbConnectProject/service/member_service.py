# path : service\\member_service.py
# module : service.member_service
# db connection, transaction 관리용 스크립트

from dao.member_dao import MemberDAO
from common.exceptions import DBException
from dto.member_dto import MemberDTO
from common.mysqlConnectTemplate import MySQLTemplate


class MemberService:
  def __init__(self):
    self.dao = MemberDAO()
  
  def get_members(self):
    with MySQLTemplate.get_connection() as conn:
      return self.dao.select_all(conn)
  
  def get_member(self, userid):
    with MySQLTemplate.get_connection() as conn:
      return self.dao.select_one(conn, userid)
  
  def register(self, member):
    with MySQLTemplate.get_connection() as conn:
      self.dao.insert(conn, member)
    
  def modify(self, userid, pwd, phone, email):
    with MySQLTemplate.get_connection() as conn:
      self.dao.update(conn, userid, pwd, phone, email)
    
  def remove(self, userid):
    with MySQLTemplate.get_connection() as conn:
      self.dao.delete(conn, userid)
