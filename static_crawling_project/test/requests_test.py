# path : .\\test\\requests_test.py
# requests 모듈 테스트

import requests

url = 'https://www.naver.com'
response = requests.get(url)
print(response.status_code)  # HTTP 상태 코드 출력
print(response.text[:500])  # 응답 본문의 처음 500자 출력
