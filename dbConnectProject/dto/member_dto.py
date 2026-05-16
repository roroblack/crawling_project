# path : dto\\member_dto.py
# module : dto.member_dto

from dataclasses import dataclass

@dataclass   # getter/ setter 자동 생성
class MemberDTO:
  # field : 필드명: 자료형 (db table 컬럼명은 대소문자이고, dto 의 필드명은 소문자임, 그대로 매핑하면 에러임)
  userid: str
  userpwd: str
  username: str
  gender: str
  age: int
  phone: str
  email: str
  # ENROLL_DATE
  # LASTMODIFIED
  # signtype: str
  # ADMIN_YN:str
  # login_ok: str
  # photo_filename: str
  