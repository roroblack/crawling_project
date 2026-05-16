# path : controller\\member_controller.py
# module : controller.member_controller

from common.exceptions import DBException
from service.member_service import MemberService
from dto.member_dto import MemberDTO

class MemberController:
  # 생성자
  def __init__(self):
    self.service = MemberService()
    
  # method
  def select_all(self):
    return self.service.get_members()
  
  def select_one(self, userid):
    return self.service.get_member(userid)
  
  def insert(self, member: MemberDTO):
    self.service.register(member)
    
  def update(self, userid, pwd, phone, email):
    self.service.modify(userid, pwd, phone, email)
    
  def delete(self, userid):
    self.service.remove(userid)    
