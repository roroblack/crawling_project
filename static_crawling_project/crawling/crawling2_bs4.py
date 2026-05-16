# path : .\\crawling\\crawling2_bs4.py
# url 을 키보드로 입력 받아서 (복사 > 붙여넣기) 크롤링 작동 테스트 스크립트

import urllib.request, bs4

url = input('접속할 url 을 입력 : ')
# url : 웹 상에서 자원까지의 경로 (주소) 를 의미함
# 표현 : 프로토콜://도메인/폴더/파일?이름=값&이름=값#표식이름
# 도메인명 : 웹서버의 ip주소:포트번호를 매핑한 이름
# 쿼리스트링 : 서버측의 연결 대상에게 전달되는 값들을 표현한 것 => ?이름=전송값&이름=전송값
# 쿼리스트림은 pathvariable 로 대체 가능
# https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%ED%98%84%EC%9E%AC%EC%83%81%EC%98%81%EC%98%81%ED%99%94


web_page = urllib.request.urlopen(url)
result_code = bs4.BeautifulSoup(web_page, 'html.parser')
print(result_code) # 접속한 페이지의 html 소스 출력 확인
