from model.models import CarRegistrationItem, FaqItem, StationItem

# Repository.save_items() 에서 허용할 모델 클래스 목록이다.
# 순서가 중요하다: [0]=CarRegistrationItem, [1]=FaqItem, [2]=StationItem
ALLOWED_MODELS = (CarRegistrationItem, FaqItem, StationItem)

# 지역명 → regions.region_id 매핑이다.
REGIONS = {
    "서울": 1,  "부산": 2,  "대구": 3,  "인천": 4,  "광주": 5,
    "대전": 6,  "울산": 7,  "세종": 8,  "경기": 9,  "강원": 10,
    "충북": 11, "충남": 12, "전북": 13, "전남": 14, "경북": 15,
    "경남": 16, "제주": 17,
}
