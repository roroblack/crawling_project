# path : view\\member_view.py
# module : view.member_view
# 메뉴 출력, 키보드입력, 콘솔 출력에 대한 사용자 인터렉션 담당

from dto.member_dto import MemberDTO

class MemberView:
  # method
  @staticmethod
  def show_menu() -> int:
    print('\n===== 회원 관리 메뉴 =====\n')
    print('1. 전체 회원 조회')
    print('2. 회원 아이디로 조회')
    print('3. 회원 등록')
    print('4. 회원 정보 수정')
    print('5. 회원 삭제')
    print('0. 종료')
    return input('메뉴 번호 선택 : ')
  # def show_menu() -------------------------------
  
  @staticmethod
  def get_userid() -> str:
    return input('아이디 입력 : ')
  # def get_userid() ------------------
  
  @staticmethod
  def get_member_insert() -> MemberDTO:
    print('\n등록할 신규 회원 정보를 입력하세요.')
    return MemberDTO(
      userid=input('회원 아이디 : '),
      userpwd=input('비밀번호 : '),
      username=input('이름 : '),
      gender=input('성별(M/F) : '),
      age=int(input('나이 : ')),
      phone=input('전화번호 : '),
      email=input('이메일 : ')
    )
  # def get_member_insert() -----------------------
  
  @staticmethod
  def get_member_update():
    print('\n수정할 회원 정보 입력하세요.')
    userid = input('대상 회원 아이디 : ')
    pwd = input('수정할 암호 : ')
    phone = input('수정할 전화번호 : ')
    email = input('수정할 이메일 : ')
    return userid, pwd, phone, email
  # def get_member_update() -------------------------
  
  @staticmethod
  def show_member(member:MemberDTO):
    print('\n조회한 회원 정보는 다음과 같습니다.')
    print(member)
  # def show_member() ----------------------
  
  @staticmethod
  def show_members(members):
    print('\n회원 목록')
    for m in members:
      print(m)
  # def show_members() --------------------    