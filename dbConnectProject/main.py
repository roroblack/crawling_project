# path : main.py
# view 와 controller 연동, 앱 시작 실행 스크립트

from view.member_view import MemberView
from controller.member_controller import MemberController
from common.exceptions import DBException

def main():
  controller = MemberController()
  
  while True:
    try:
      action = MemberView.show_menu()
      
      if action == '1':
        MemberView.show_members(controller.select_all())
      
      elif action == '2':
        MemberView.show_member(controller.select_one(MemberView.get_userid()))
        
      elif action == '3':
        controller.insert(MemberView.get_member_insert())
        print('회원 등록 성공')
        
      elif action == '4':
        userid, pwd, phone, email = MemberView.get_member_update()
        controller.update(userid, pwd, phone, email)
        print('회원 정보 수정 성공')
        
      elif action == '5':
        controller.delete(MemberView.get_userid()) 
        print('회원 정보 삭제 성공')
        
      elif action == '0':
        print('회원 관리 프로그램 종료!!!')
        break
      
      else:
        print('잘못된 메뉴 번호 선택입니다. 확인하고 다시')                 
        
    except DBException as e:
      print(str(e))
    except Exception as e:
      print(f'오류 발생 : {e}')

# main() ------------------------------  
  
if __name__ == '__main__':
  main()
  