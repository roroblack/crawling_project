# path : .\\crawling\\crawling_bs4.py
# BeautifulSoup4 모듈을 이용한 정적 웹 크롤링 예제

# 모듈 설치 : pip install beatifulsoup4
import bs4                      # 웹 문서 (HTML, XML 등)을 html 로 분석하는 모듈임
import urllib.request           # 웹 상의 데이터를 가져오는 모듈
import urllib.request, bs4

# 1. url 로 웹페이지 접속
web_page = urllib.request.urlopen('https://www.naver.com')
print(web_page)  # 웹페이지 접속 결과 출력 # response 객체가 반환됨 (16진수 주소)

# 2. 접속한 페이지 소스를 읽어옴
# html_code = web_page.read()
# print(html_code)  # 웹페이지 소스코드 출력

# 3. 읽어온 인코딩된 소스를 html 태그 구문으로 바꿈
decoding_code = bs4.BeautifulSoup(web_page, 'html.parser')
print(decoding_code)
