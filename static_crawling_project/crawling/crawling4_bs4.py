# path : crawling\\crawling4_bs4.py

# movie 테이블에 기록된 행들을 모두 조회해 와서 출력 처리함
# 등수순 오름차순정렬해서 모두 조회해 옴
# 조회된 하나의 행 정보를 Movie 클래스 객체로 생성하고, 객체를 리스트에 저장 처리함

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.mysqlConnectTemplate import MySQLTemplate
from entity.Movie import Movie

select_sql = '''
select `rank`, title, star_point, release_date, genre, link
from movie
order by `rank` asc
'''

movie_list = []

with MySQLTemplate.get_connection() as conn:
  cursor = conn.cursor()
  cursor.execute(select_sql)
  result = cursor.fetchall()
  
  for row in result:
    # print(row)
    movie = Movie(
      row[0],
      row[1],
      row[2],
      row[3],
      row[4],
      row[5]
    )
    # print(movie)
    movie_list.append(movie)
  cursor.close()
# with end

# 조회 결과 출력
for movie in movie_list:
  print(movie)
  
  