# path : dao\\member_dao.py
# module : dao.member_dao

# 모듈에서 클래스만 임포트
from common.exceptions import DBException
from dto.member_dto import MemberDTO

class MemberDAO:
  # method
  def insert(self, conn, member: MemberDTO) -> None:  # -> None : 반환값 없는 메소드 선언임
    sql = '''
    insert into member 
    (userid, userpwd, username, gender, age, phone, email)
    values (%s, %s, %s, %s, %s, %s, %s)
    '''    
    
    try:
      with conn.cursor() as cur:   # 문장객체 만들기
        cur.execute(sql, (
          member.userid,
          member.userpwd,
          member.username,
          member.gender,
          member.age,
          member.phone,
          member.email
        ))
    except Exception as e:
      raise DBException(f'INSERT 실패: {e}')
  # def insert() -------------------------
  
  def select_one(self, conn, userid: str) -> MemberDTO | None:
    '''
    userid 로 회원 1명 조회
    
    :param userid: 회원 아이디
    :return: MemberDTO 또는 None
    :rtype: MemberDTO | None
    '''
    # 필드명과 컬럼명이 일치하지 않을 때 또 다른 해결방법 : select 절의 컬럼 별칭을 필드명과 맞춤
    sql = '''
    select 
      USERID AS userid,
      USERPWD AS userpwd,
      USERNAME AS username,
      GENDER AS gender,
      AGE AS age,
      PHONE AS phone,
      EMAIL AS email
    from member 
    where USERID = %s'''
        
    try:
      with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, (userid,))
        row = cur.fetchone()          
        
        if row is None:
          return None
        
        return MemberDTO(**row)
          
    except Exception as e:
      raise DBException(f'SELECT one 실패: {e}')  
    
  # def select_one() ---------------------
  
  
  def select_all(self, conn) -> list[MemberDTO]:
    sql = 'select * from member'
    members = []    
    
    try:
      with conn.cursor(dictionary=True) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        
        # for r in rows:
        #   members.append(MemberDTO(**r))  # 13개 컬럼을 dto(7개) 에 매핑하는 것임:error
        # 컬럼명과 필드명의 대소문자도 일치해야 함
        
        # 7개의 컬럼에만 값 매핑하고, 컬럼명 대소문자 매칭 처리함
        for r in rows:  # 조회해 온 전체행(rows)에서 행 하나(r)를 추출
          dto = MemberDTO(
            userid = r['USERID'],   # dto 의 필드명=r['컬럼명'] : r(행)의 컬럼값을 필드에 대입
            userpwd = r['USERPWD'],
            username = r['USERNAME'],
            gender = r['GENDER'],
            age = r['AGE'],
            phone = r['PHONE'],
            email = r['EMAIL']
          )
          members.append(dto)
    except Exception as e:
      raise DBException(f'SELECT 실패: {e}')        
        
    return members
  # def select_all() ---------------------
  
  # def 메소드명(self, 매개변수:자료형,  .... ) -> 반환자료형
  def update(self, conn, userid: str, pwd: str, phone: str, email: str) -> int:
    sql = '''
    update member
    set userpwd = %s, phone = %s, email = %s
    where userid = %s
    '''

    try:
      with conn.cursor() as cur:
        cur.execute(sql, (pwd, phone, email, userid))
        return cur.rowcount
    except Exception as e:
      raise DBException(f'UPDATE 실패: {e}')
  # def update() ----------------------
  
  def delete(self, conn, userid: str) -> int:
    sql = 'delete from member where userid = %s'
  
    try:
      with conn.cursor() as cur:  # with ~ 문 : 자동 close() 해 주는 문장임
        cur.execute(sql, (userid,))
        return cur.rowcount
    except Exception as e:
      raise DBException(f'DELETE 실패: {e}')
  # def delete() -------------------------