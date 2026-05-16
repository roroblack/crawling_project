# path: crawling\\dynamic_crawling.py
# 동적 웹 크롤링 구동하는 스크립트

# 동적 웹 크롤링 : selenium 모듈 사용함 => 외부 패키지이므로 설치 필요함
'''
selenium 모듈(브라우저를 실행시키는 모듈임)은 웹브라우저와 연동해서,
브라우저에 준비된 웹사이트와 이 사이트의 html 태그 구조를 이용해서
원격 검색을 가능하게 함 <= 파이썬을 통해 검색 키워드를 전송해서 대상 앨리먼트(태그)에 검색 값(키워드)을 적용함
=> 검색 결과 페이지가 브라우저에 출력되면, 파이썬에서 읽어와서 분석함  

동적 웹 크롤링의 동작: 
브라우저 구동 > 사이트 접속 > 검색 필드(tag) 찾음 > 검색 키워드 전송함
 > 브라우저 웹페이지에 검색 작동시킴 > 검색 실행 > 잠시 대기
 > 브라우저에 검색 결과 페이지 출력 > 파이썬에서 읽어옴 > 소스코드 분석
 
[첫번째 단계] selenium 과 연결할 브라우저 선택: 크롬(chrome)
1. 현재 설치 사용중인 크롬 브라우저의 버전 확인함: 
  브라우저 우측 상단 점3개 클릭 > 도움말 > Chrome 정보 > 버전 정보 확인: 버전 143.0.7499.170(공식 빌드) (64비트)
  (최신 버전으로)
2. 웹에서 '크롬 드라이버' 검색 > 확인된 버전과 일치하는 드라이버 zip 을 다운받음
3. 압축 풀어서 압축 푼 폴더 안에 exe 파일을 현재 프로젝트 폴더로 복사함  
'''

# import 방법:
# import 모듈명 [as 줄임말]  => 모듈이 가진 전체 내용이 임포트됨
# 모듈이 가진 일부 항목만 선택해서 임포트할 수 있음
# from 모듈명 import 선택항목명[, 선택항목, 하위모듈, 함수명, 클래스명, ...... ]

from selenium import webdriver as wd   # 하위모듈 [as 줄임말]
from selenium.webdriver.chrome.service import Service  # 클래스 [as 줄임말]
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as bs   # 클래스 [as 줄임말]
from selenium.webdriver.common.by import By  # 클래스
# 명시적 대기 waiting 을 명시하기 위해
from selenium.webdriver.support.ui import WebDriverWait  # 클래스
from selenium.webdriver.support import expected_conditions as EC  # 하위모듈 [as 줄임말]
import time
from unicodedata import category
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 프로젝트 루트 경로 추가

from model.tour_model import TourModel
from model.tour import TourInfo


def run():
  # 크롬 드라이버 등록
  # Mac 용:
  # driver = wd.Chrome('../chromedriver.exe')
  # 윈도우용 (./ : 현재 폴더, ../ : 상위 폴더)
  # [개선 1] ChromeDriver 버전 불일치 문제 해결
  # 이전 코드: 수동으로 다운받은 chromedriver.exe 직접 지정 => Chrome 업데이트 시 버전 불일치 오류 발생
  #   driver = wd.Chrome(service=Service('./chromedriver.exe'))
  # 개선 후: webdriver-manager 가 현재 Chrome 버전에 맞는 드라이버를 자동으로 다운로드/관리
  #          => Chrome 이 업데이트돼도 자동 호환
  driver = wd.Chrome(service=Service(ChromeDriverManager().install()))  # 크롬브라우저 실행
  
  # 접속할 테스트 사이트 url 지정해서 연결 확인
  main_url = 'https://www.naver.com/'
  # 실행시 키보드로 url 입력받아서 연결되게 해도 됨
  # main_url = input('연결할 사이트 url : ')
  
  # 브라우저 열고, 사이트에 접속 처리
  driver.get(main_url)  # 실행 확인
  # time.sleep(3)  # 3초 멈춤
  
  # 해당 페이지의 검색 태그에 전달할 검색 키워드 정하기 (입력을 통해서 정해도 됨)
  keyword = '로마여행'     # keyword = input('검색할 키워드 : ')
  # 검색 결과 저장할 리스트 준비
  tour_list = []
  
  '''
  접속한 네이버 페이지의 검색 입력필드를 찾아서 검색 키워드를 입력되게 해서 검색을 실행되게 처리함
  검색 입력필드 태그(element)는 브라우저 '개발자도구' > 'elements' 탭에서 찾음
  찾은 앨리먼트 태그에서 마우스 우클릭 > copy > copy selector 선택함
   => input 태그 id명 : #query 복사됨
  '''
  input_tag = driver.find_element(By.ID, 'query')
  print(input_tag)
  input_tag.send_keys(keyword)
  # 해당 웹페이지 검색 input 에 '로마여행' 자동 입력됨
  
  # 검색 버튼 찾아서 클릭을 작동
  # button 태그 : copy selector 해 옴 => #sform > fieldset > button
  driver.find_element(By.CSS_SELECTOR, '#sform > fieldset > button').click()
  
  # 잠시 대기 => 검색 결과 페이지가 브라우저에 출력되고 나서 바로 데이터를 획득할 수 없음
  # 대기 방법 : 명시적 대기(코드로 표기)와 암묵적 대기 2가지임
  # 획득할 데이터가 발견될 때까지 대기시킴
  
  # 절대적 대기 설정
  # time.sleep(10)  # 10초 대기
  
  # 명시적 대기 : 요구한 앨리먼트를 찾을 때까지 대기시킴
  # 로마, 가볼만한 곳 글자 출력될 때까지 기다리게 설정한다면
  # 로마 글자 : copy selector => #nxTsOv > div > div.MainContainer._travel_header.MainContainer-vjtko > div.PanelHeader-vpb6F > div.titles-DAXq1 > div.TitleWrap-Kjk_o > h2 > a > span
  # 로마 글자 찾을 때까지로 명시적 대기 처리를 한다면
  # [개선 2] 명시적 대기 선택자 안정화
  # 이전 코드: 네이버 배포마다 자동 변경되는 해시 클래스명을 포함한 긴 CSS 선택자 사용
  #   element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR,
  #     '#nxTsOv > div > div.MainContainer._travel_header.MainContainer-vjtko > div.PanelHeader-vpb6F > ...')))
  # 개선 후: _travel_header 는 해시 없는 안정적인 클래스명만 사용 => 배포 후에도 동작 보장
  try:
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '._travel_header')))
    # 지정한 앨리먼트 위치를 확인하면 대기 종료됨
  except Exception as e:
    print('대기 요청 타임아웃: ', e)
    
  # 암묵적 대기: 
  '''
  DOM(Document Object Model : 태그 사용 계층 구조)이 전부 다 브라우저에 로드될 때까지
  (웹페이지 소스 코드 모두 읽어 들일때까지) 대기함
  먼저 로드되면 바로 태그 앨리먼트 찾도록 진행시킴
  앨리먼트 찾을 타임아웃(초)을 지정하면, 지정 시간동안 DOM 풀링 지시할 수 있음
  '''    
  driver.implicitly_wait(10)
  
  # [개선 3] 탭 클릭 선택자 안정화
  # 이전 코드: 해시 클래스명(TabList-Erooo, scroll-D9KKR 등)을 포함한 전체 경로 사용
  #   driver.find_element(By.CSS_SELECTOR,
  #     '#nxTsOv > div > div.MainContainer._travel_header.MainContainer-vjtko > div.PanelHeader-vpb6F
  #      > div.TabList-Erooo._scroll_wrapper > div.scroll-D9KKR._scroller > ul > li:nth-child(5) > a > span').click()
  # 개선 후: 안정적인 _scroll_wrapper 클래스만 사용, 해시 부분 제거
  driver.find_element(By.CSS_SELECTOR, '._scroll_wrapper ul > li:nth-child(5) > a > span').click()
  time.sleep(3)
  
  # 만약, 해당 페이지 영역에서 데이터를 가져올 때, 혹시 로그인이 필요한 경우에는 로그인 세션 관리 필요함
  # 데이터가 많으면 세션 타임아웃에 의해 자동 로그아웃될 수 있으므로, 특정 단위별로 로그아웃하고,
  # 다시 로그인하는 처리가 필요함 => loop 문 돌려서 접근 처리 필요함: 메타 장보 획득
  
  # 현재 페이지 소스를 파일로 저장 (클래스명 확인용 디버그)
  with open('page_source.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
  print('page_source.html 저장 완료 - 브라우저로 열어서 클래스명 확인 필요')

  # [개선 4] 항목 선택자 - 해시 클래스 → data 속성으로 변경
  # 이전 코드: 네이버 CSS 모듈 해시 클래스명(TopPoiItem-MgXeO 등) 사용 => 배포마다 값이 바뀌어 항목 0개 반환
  #   item_list = driver.find_elements(By.CLASS_NAME, 'TopPoiItem-MgXeO')
  # 이후 부분매칭 시도: [class*="TopPoiItem-"] 로 변경했으나 네이버가 pui__ 체계로 구조 자체를 교체하여 여전히 0개
  #   item_list = driver.find_elements(By.CSS_SELECTOR, '[class*="TopPoiItem-"]')
  # 개선 후: data-otb_lsra-doc-id 는 데이터 식별용 속성이므로 CSS 클래스 변경에 무관하게 안정적으로 동작
  item_list = driver.find_elements(By.CSS_SELECTOR, 'li[data-otb_lsra-doc-id]')
  print(len(item_list))
  print(item_list)
  
  # 가볼만한 곳 항목에서 데이터 추출하기
  # 추출할 값 : 장소이름(name), 장소설명(description), 장소구분(category), 별점(score)
  # db 저장 처리를 위한 객체 생성
  tm = TourModel()
  
  # 기존 db 테이블에 저장된 정보 모두 지우기
  tm.delete_all()
  
  # [개선 5] 각 항목 내부 데이터 추출 방식 전면 변경
  # 이전 코드: selenium find_element 로 각 항목마다 개별 DOM 접근 + 해시 클래스명 직접 지정
  #   => 네이버가 pui__ 체계로 변경하면서 아래 선택자들이 전부 NoSuchElementException 발생
  #   rank        = item.find_element(By.CSS_SELECTOR, 'a > figure > span').text
  # #\38 279201513 > div:nth-child(1) > a > div.pui__zDbfhP.pui__SjK6bN > div > span.pui__rnHuVa
  #   name        = item.find_element(By.CSS_SELECTOR, 'span.pui__rnHuVa').text
  #   description = item.find_element(By.CSS_SELECTOR, 'span.desc-tw973').text
  #   category    = item.find_element(By.CSS_SELECTOR, 'span.text-Y6pAX').text
  #   score       = round(float(item.find_element(By.CSS_SELECTOR, 'span.score-ea24I').text), 1)
  #   tp_info = (int(rank[0]), name, description, category, score)  # rank[0] 는 10위 이상에서 '1'만 추출되는 버그도 있었음
  #
  # 개선 후:
  #   - BeautifulSoup 으로 페이지를 한 번만 파싱 (selenium 다중 DOM 접근보다 빠름)
  #   - 클래스명 대신 태그 구조(div 위치, span 순서) 기반으로 추출 => 클래스 해시 변경에 무관
  #   - '별점' 텍스트를 가진 span 의 부모에서 정규식으로 숫자 추출 => 별점 클래스명 무관
  #   - rank 는 enumerate 순번 사용 => figure > span 선택자 불필요, 10위 이상 버그도 해소
  import re
  # BeautifulSoup 으로 전체 페이지 한 번만 파싱
  page_soup = bs(driver.page_source, 'html.parser')
  item_soups = page_soup.find_all('li', attrs={'data-otb_lsra-doc-id': True})

  for rank, item_soup in enumerate(item_soups, 1):
    main_a = item_soup.find('a', attrs={'role': 'button'})
    if not main_a:
      continue
    child_divs = main_a.find_all('div', recursive=False)
    # 첫 번째 자식 div 안의 span : name(0번째), category(1번째)
    name_cat_spans = child_divs[0].find_all('span') if child_divs else []
    name        = name_cat_spans[0].text.strip() if len(name_cat_spans) > 0 else ''
    cat         = name_cat_spans[1].text.strip() if len(name_cat_spans) > 1 else ''
    # 두 번째 자식 div : description
    description = child_divs[1].get_text(strip=True) if len(child_divs) > 1 else ''
    # '별점' span 의 부모 텍스트에서 정규식으로 숫자 추출 (예: "별점4.7점" => 4.7)
    score = 0.0
    byeoljum_span = item_soup.find('span', string='별점')
    if byeoljum_span:
      raw = byeoljum_span.parent.get_text()          # "별점4.7점"
      m = re.search(r'(\d+\.?\d*)', raw.replace('별점','').replace('점',''))
      score = round(float(m.group(1)), 1) if m else 0.0

    print('추출한 정보 : ', rank, name, description, cat, score)
    tp_info = (rank, name, description, cat, score)
    tm.insert_tour(tp_info)
  # for ----------------------------------
 
  # db 에 저장된 정보 조회 출력 확인
  resultset = tm.select_all()
  # 리턴된 조회결과를 한 행씩 TourInfo 객체에 저장 처리하고, 리스트에 추가
  for row in resultset:
    tourinfo = TourInfo(row[0], row[1], row[2], row[3], row[4])
    print(tourinfo)
    tour_list.append(tourinfo)
  # for ------------------------
  
  print(tour_list)
  
  # 브라우저 종료
  driver.close()  # 크롬 브라우저 닫기
  driver.quit()   # 드라이버 종료
  
  return  # main 으로 리턴 => 프로세스 종료
# run() -----------------------------------------    
