# path : .\\crawling\\craling3_bs4.py
# 네이버 개봉영화 검색 결과 페이지에서 크롤링에서 분석하는 스크립트

import urllib.request, bs4

# 이전 코드 (문제 있음)
# web_page = urllib.request.urlopen('https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EA%B0%9C%EB%B4%89%EC%98%81%ED%99%94')
# result_code = bs4.BeautifulSoup(web_page, 'html.parser')
# print(result_code) # 접속한 페이지의 html 소스 출력 확인
# result_code = bs4.BeautifulSoup(web_page, 'html.parser') # 스트림 이미 소진 -> 빈 내용 파싱됨

url = 'https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EA%B0%9C%EB%B4%89%EC%98%81%ED%99%94'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
web_page = urllib.request.urlopen(req).read()  # 스트림을 한 번만 읽어서 변수에 저장

result_code = bs4.BeautifulSoup(web_page, 'html.parser')
#print(result_code) # 접속한 페이지의 html 소스 출력 확인

# 개봉영화 정보가 기록된 태그 엘리먼트 찾는 방법
'''
브라우져 개발자 도구 (F12) > 'element' 탭 왼쪽의 'select an element ... ' 화살표 툴버튼 클릭
> 페이지에서 마우스로 대상 영역을 찾아서 클릭함
> 'element' 뷰에 선택된 영역의 태그가 범위 지정 표시될 것임
> 찾을 대상 태그명과 class 또는 id 속성 값을 확인함

태그 안의 값을 추출 : find() 함수 => 찾은 엘리먼트 첫번째 것 하나만 리턴함
    find(찾을 데이터가 들어있는 태그명, 태그속성_='속성값')
    find(태그속성_='속성값')
    find(태그명)
'''

data_box = result_code.find('div', {'class': 'data_box'})
print(data_box) # 개봉영화 정보가 기록된 태그 엘리먼트 출력 확인
print('-----------------------------')

# 영화 제목만 추출한다면
movie_title = data_box.find('a', {'class': 'this_text'})
print(movie_title) # 영화 제목이 기록된 태그 엘리먼트 출력 확인
print('-----------------------------')

# find_all() 함수 :
# 태그 엘리먼트 여러 개 추출함 -> list 리턴
movie_list = result_code.find_all('a', {'class': 'this_text'})
print(len(movie_list))
print(movie_list) # 영화 제목이 기록된 태그 엘리먼트 여러 개 출력 확인

# 영화 제목만 추출하기
for idx in range(len(movie_list)) :
    title = movie_list[idx].text
    print(title) # 영화 제목만 출력
print('-----------------------------')

movie_div = result_code.find_all('div', class_='data_area')
print(len(movie_div))
button_div = result_code.find_all('div', class_='button_area')
print(len(button_div))
print(button_div)

movie_list = list()
for idx in range(len(movie_div)) :
    # 영화제목, 개봉일, 개요(장르), 별점, 예고편 링크 추출
    data_box = movie_div[idx].find('div', {'class': 'data_box'})
    print(data_box)
    print('-----------------------------')
    preview_tag = button_div[idx].find('a', {'class': 'btn_preview'})

    # 제목 추출
    # movie_title = data_box.find('a', {'class': 'this_text'}).text # get_text() 함수도 가능
    # movie_title = data_box[idx].find('a', {'class': 'this_text'}).get_text() # get_text() 함수도 가능
    movie_title = data_box.find('a', {'class': 'this_text'}).get_text() # get_text() 함수도 가능
    print(movie_title)
    print('-----------------------------')

    # 예고편 링크 추출 : a 태그의 href 속성값 추출
    # attrs['href'] or .['href'] or .get('href') 모두 가능
    movie_link = preview_tag.get('href') if preview_tag else None
    # 간단 조건문 : True 일 때 실행할 내용 if 조건 else False 일 때 실행 내용
    print(movie_link) # url 출력 확인
    print('-----------------------------')

    # 장르(개요), 개봉일, 별점 추출
    movie_genre         = None
    movie_open_date     = None
    star_point          = 0.0

    info_group = data_box.find_all('dl', class_='info_group')
    # 선택된 dl 태그들 하나씩 추출
    for dl_tag in info_group :
        # dl 태그 안에 dt 태그들 추출
        dt_tags = dl_tag.find_all('dt')
        
        for dt in dt_tags :                 # dt 태그 하나씩 처리
            label = dt.text.strip()         # 추출된 글자 양쪽 공백 제거
            # dt 태그 아래의 dd 태그 추출
            dd = dt.find_next_sibling('dd') # 선택된 dt 와 같은 레벨의 dd 를 선택함

            if label == '개요' :
                movie_genre = dd.text.strip()
            elif label == '개봉':
                movie_open_date = dd.text.strip()
            elif label == '평점' :
                star_point = float(dd.text.strip())

            if dd.find('span', class_='num') != None : # 평점이 없는 경우도 있음
                star_point = round(float(dd.find('span', class_='num').text.strip()), 2)
        #info for--------------------------------
                
    print(movie_genre)
    print(movie_open_date)
    print(star_point)
    print('-----------------------------')

    # 영화정보 하나씩 저장 : dict 로 작성해서 리스트에 추가
    movie = dict()
    movie['title'] = movie_title
    movie['link'] = movie_link
    movie['genre'] = movie_genre
    movie['star_point'] = star_point
    movie['open_date'] = movie_open_date

    movie_list.append(movie)
    print('-----------------------------')
# data_box for--------------------------------

print(len(movie_list))
print(movie_list)

# 별점순 내림차순정렬 처리
sort_list = sorted(movie_list, key=lambda x: x['star_point'], reverse=True)
print('------------------------------')
print(sort_list)

# 정렬 후 '순위' 항목을 추가함
for idx in range(len(sort_list)) :
    movie = sort_list[idx]
    movie['rank'] = idx + 1 # 순위는 1부터 시작하므로 인덱스 + 1
    print(movie)




 #-------------------------------------------------------------------------------- 
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
  