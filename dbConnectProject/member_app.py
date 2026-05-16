# path : member_app.py
# 실행용 스크립트

from dao.member_dao import MemberDAO
from dto.member_dto import MemberDTO

dao = MemberDAO()

try:
  # insert test
  dao.insert(MemberDTO('user077', 'pass077', '이순신', 'M', 40, '010-1234-7777', 'leess77@test.org'))
  
  # select all
  for member in dao.select_all():
    print(member)
    
  # update test
  result = dao.update('user077', 'pass789', '010-4949-7878', 'lss7788@test.org')
  print('수정된 행 갯수 : ', result)
  
  # select one test
  print('한 개 행 조회')
  print(dao.select_one('user077'))
    
  # delete test
  result = dao.delete('user077')
  print('삭제된 행갯수 : ', result)
  
  # select all
  for member in dao.select_all():
    print(member)    
    
except Exception as e:
  print(e)
  
    