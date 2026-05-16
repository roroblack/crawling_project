# path: crawling\\crawling3_bs4.py
# 네이버 개봉영화 정보 페이지에서 크롤링 분석용 스크립트 3

import urllib.request, bs4

web_page = urllib.request.urlopen('https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=%EA%B0%9C%EB%B4%89%EC%98%81%ED%99%94&ackey=npf3byca')

result_code = bs4.BeautifulSoup(web_page, 'html.parser')
# print(result_code)

# 개봉영화 정보가 기록된 태그 앨리먼트 찾는 방법:
# 개발자도구 > element 탭의 왼쪽의 'select an element ....' 화살표 툴 클릭 
#  > 페이지에서 마우스로 대상 영역을 찾아서 클릭함
# 찾아진 태그 앨리먼트 안의 값을 추출함 : find() 함수 - 찾은 첫번째 앨리먼트만 리턴함
# find(찾을 데이터가 들어있는 태그명, 태그속성_='속성값')
# find(태그속성_='속성값')
# find(찾을태그명)

# data_box = result_code.find('div', {'class', 'data_box'})
# print(data_box)  # 첫번째 항목 한 개만 출력 확인됨
# 영화제목만 추출한다면
# movie_title = data_box.find('a', {'class': 'this_text'})
# print(movie_title)  # 제목 한 개만 출력 확인

# 태그 앨리먼트 여러 개 추출: find_all() 함수 사용
# movie_list = result_code.find_all('a', {'class': 'this_text'})
# print(len(movie_list))
# print(movie_list)  # a 태그들에 대한 목록

# 영화 제목만 추출하기
# for idx in range(len(movie_list)):
  # title = movie_list[idx].text   # a 태그 안의 글자 추출
  # print(title)
  
movie_div = result_code.find_all('div', class_='data_area')  
print(len(movie_div))
button_div = result_code.find_all('div', class_='button_area') 
print(len(button_div))
# print(button_div)

movie_list = list()
for idx in range(len(movie_div)):
  # 영화제목, 개봉일, 개요(장르), 별점, 예고편 링크 추출
  data_box = movie_div[idx].find('div', {'class': 'data_box'})
  # print(data_box)
  movie_title = data_box.find('a', {'class': 'this_text'}).text  # get_text() 사용해도 됨
  # print(movie_title)  
  preview_tag = button_div[idx].find('a', {'class': 'btn_preview'})
  # a 태그의 href 속성값 추출 : .attrs['href'] or .['href'] or .get('href')
  movie_link = preview_tag.get('href') if preview_tag else None
  # print(movie_link)
  
  # 장르(개요), 개봉일, 별점 추출
  movie_genre = None
  movie_open_date = None
  star_poine = 0.0
    
  info_groups = data_box.find_all('dl', class_='info_group')
  for dl_tag in info_groups:   # 선택된 dl 태그 하나씩 추출함
    dt_tags = dl_tag.find_all('dt')  # dl 태그 안의 dt 태그들 선택
    for dt in dt_tags:  # 선택된 dt 태그들에서 dt 태그 하나씩 추출함
      label = dt.text.strip()   # 추출된 글자 양쪽의 공백 없음
      dd = dt.find_next_sibling('dd') # 선택된 dt 와 같은 레벨의 dd 를 선택함
      
      if label == '개요':
        movie_genre = dd.text.strip()
      elif label == '개봉':
        movie_open_date = dd.text.strip()
      
      if dd.find('span', class_='num') != None:  
        star_point = round(float(dd.find('span', class_='num').text.strip()), 2)
        print(star_point)
  
  # 영화 하나씩 dict 로 작성해서 리스트 추가 처리
  movie = dict()
  movie['title'] = movie_title
  movie['link'] = movie_link
  movie['genre'] = movie_genre
  movie['star_point'] = star_point
  movie['release_date'] = movie_open_date
  
  movie_list.append(movie)
  # for end
  
print(len(movie_list)) 
print(movie_list)   
 
# 별점순 내림차순정렬 처리
sort_list = sorted(movie_list, key=lambda x: x['star_point'], reverse=True)
print('sorted after ------------------')
print(sort_list)  
  
# 정렬 후 '순위' 항목을 추가해 봄
for idx in range(len(sort_list)):
  movie = sort_list[idx]
  movie['rank'] = idx + 1
  print(movie)
  
  
# MySQL DB 에 movie 테이블에 기록 저장 처리해 봄
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.mysqlConnectTemplate import MySQLTemplate
# pip install mysql-connector-python
# 현재 파일에서 common 은 상위폴더에 위치함 => 현재 소스파일과 common 폴더가 같은 위치가 아님
# 해결방법 : common 폴더를 패키지로 인지되게 처리함 => common 폴더 안에 __init__.py 라는 빈 파일을 만듦

insert_sql = '''
insert into movie 
(`rank`, title, star_point, release_date, genre, link)
values (%s, %s, %s, %s, %s, %s)
'''
# 컬럼명에 빽틱 사용되었으면, 쿼리문에서 컬럼명에 빽틱 표기해야 함

with MySQLTemplate.get_connection() as conn:  # conn과 트랜잭션(commit, rollback) 자동 실행 처리됨
  cursor = conn.cursor()
  
  for movie in movie_list:
    cursor.execute(insert_sql, (
      movie['rank'],
      movie['title'],
      movie['star_point'],
      movie['release_date'],
      movie['genre'],
      movie['link']
    ))
    
  cursor.close()
# with end -------  
  