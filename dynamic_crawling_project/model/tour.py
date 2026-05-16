# path : model\\tour.py
# module : model.tour
# 여행지 정보 저장용 클래스 정의 스크립트

# 순위(rank), 장소이름(name), 장소설명(description), 장소구분(category), 별점(score)
class TourInfo:
  # field : private
  __rank = None
  __name = None
  __description = None
  __category = None
  __score = 0.0
  
  # constructor
  def __init__(self, rank, name, description, category, score):
    self.__rank = rank
    self.__name = name
    self.__description = description
    self.__category = category
    self.__score = score
    
  # method : getter and setter, operator overloading
  # operator overloading : __str__(self)
  def __str__(self):
    '객체가 가진 필드값들을 하나의 문자열로 만들어서 리턴'
    return '{}, {}, {}, {}, {}'.format(self.__rank, self.__name, self.__description, self.__category, self.__score)
  
  # getters
  def get_rank(self):
    return self.__rank
  
  def get_name(self):
    return self.__name
  
  def get_description(self):
    return self.__description
  
  def get_category(self):
    return self.__category
  
  def get_score(self):
    return self.__score
  
  # setters
  def set_rank(self, rank):
    self.__rank = rank
    
  def set_name(self, name):
    self.__name = name
    
  def set_description(self, description):
    self.__description = description
    
  def set_category(self, category):
    self.__category = category
    
  def set_score(self, score):
    self.__score = score
# class TourInfo -----------------------
    
  