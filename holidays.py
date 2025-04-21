from app import db
from models import Holiday
from datetime import date

def add_korean_holidays(year):
    """한국 공휴일 추가"""
    holidays = [
        # 신정
        (date(year, 1, 1), "신정"),
        # 설날
        (date(year, 1, 1), "설날 연휴"),  # 실제 날짜는 음력으로 변경 필요
        # 삼일절
        (date(year, 3, 1), "삼일절"),
        # 어린이날
        (date(year, 5, 5), "어린이날"),
        # 석가탄신일 (음력으로 변경 필요)
        (date(year, 5, 8), "석가탄신일"),  # 실제 날짜는 음력으로 변경 필요
        # 현충일
        (date(year, 6, 6), "현충일"),
        # 광복절
        (date(year, 8, 15), "광복절"),
        # 추석
        (date(year, 9, 15), "추석 연휴"),  # 실제 날짜는 음력으로 변경 필요
        # 개천절
        (date(year, 10, 3), "개천절"),
        # 한글날
        (date(year, 10, 9), "한글날"),
        # 크리스마스
        (date(year, 12, 25), "크리스마스")
    ]
    
    # 이미 등록된 공휴일 제외
    existing_holidays = Holiday.query.filter(
        db.extract('year', Holiday.date) == year
    ).all()
    existing_dates = [h.date for h in existing_holidays]
    
    for holiday_date, holiday_name in holidays:
        if holiday_date not in existing_dates:
            holiday = Holiday(date=holiday_date, name=holiday_name)
            db.session.add(holiday)
    
    db.session.commit()
