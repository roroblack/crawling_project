# path : entity\\Movie.py
# module : entity.Movie
# 크롤링해서 추출한 영화정보 저장용 클래스 정의 스크립트

class Movie:
  # field (attribute, property, 멤버변수) : private (이름 앞에 __ 2개 붙임)
  __rank = 0            # 영화순위
  __title = None        # 영화제목
  __star_point = 0.00   # 영화평점
  __release_date = None # 개봉일
  __genre = None        # 영화장르
  __link = None         # 예고편 url
  
  # constructor (1개만 작성할 수 있음, 매개변수 있는 생성자 작성함)
  def __init__(self, rank, title, star_point, release_date, genre, link):
    self.__rank           = rank
    self.__title          = title
    self.__star_point     = star_point
    self.__release_date   = release_date
    self.__genre          = genre
    self.__link           = link
    
  # method
  # 연산자 오버로딩 추가 : 자바의 toString() == 파이썬의 __str__(self)
  # 객체가 가진 필드값들을 하나의 문장(str)으로 만들어서 리턴 처리함
  def __str__(self):
    return f'{self.__rank}위: {self.__title}, {self.__genre}, 평점: {self.__star_point}, 개봉일: {self.__release_date}, 예고편: {self.__link}'

  # __repr__ = __str__    
