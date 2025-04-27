from app import app, db
from holidays import add_korean_holidays

# 앱 컨텍스트 내에서 실행
with app.app_context():
    print("2025년 공휴일 등록 중...")
    add_korean_holidays(2025)
    print("2025년 공휴일 등록 완료")
    
    print("2026년 공휴일 등록 중...")
    add_korean_holidays(2026)
    print("2026년 공휴일 등록 완료")
    
    print("공휴일 등록이 완료되었습니다.")