from app import db
from models import Holiday
from datetime import date

def add_korean_holidays(year):
    """한국 공휴일 추가"""
    holidays = []
    
    if year == 2025:
        holidays = [
            # 2025년 공휴일
            # 신정
            (date(2025, 1, 1), "신정"),
            # 설날
            (date(2025, 1, 29), "설날 연휴 (첫째날)"),
            (date(2025, 1, 30), "설날"),
            (date(2025, 1, 31), "설날 연휴 (마지막날)"),
            # 삼일절
            (date(2025, 3, 1), "삼일절"),
            # 어린이날
            (date(2025, 5, 5), "어린이날 (대체공휴일)"),
            # 석가탄신일
            (date(2025, 5, 6), "석가탄신일"),
            # 현충일
            (date(2025, 6, 6), "현충일"),
            # 광복절
            (date(2025, 8, 15), "광복절"),
            # 추석
            (date(2025, 9, 8), "추석 연휴 (첫째날)"),
            (date(2025, 9, 9), "추석"),
            (date(2025, 9, 10), "추석 연휴 (마지막날)"),
            # 개천절
            (date(2025, 10, 3), "개천절"),
            # 한글날
            (date(2025, 10, 9), "한글날"),
            # 크리스마스
            (date(2025, 12, 25), "성탄절")
        ]
    elif year == 2026:
        holidays = [
            # 2026년 공휴일
            # 신정
            (date(2026, 1, 1), "신정"),
            # 설날
            (date(2026, 2, 17), "설날 연휴 (첫째날)"),
            (date(2026, 2, 18), "설날"),
            (date(2026, 2, 19), "설날 연휴 (마지막날)"),
            # 삼일절
            (date(2026, 3, 1), "삼일절"),
            # 어린이날
            (date(2026, 5, 5), "어린이날"),
            # 석가탄신일
            (date(2026, 5, 24), "석가탄신일"),
            # 현충일
            (date(2026, 6, 6), "현충일"),
            # 광복절
            (date(2026, 8, 15), "광복절"),
            # 추석
            (date(2026, 9, 25), "추석 연휴 (첫째날)"),
            (date(2026, 9, 26), "추석"),
            (date(2026, 9, 27), "추석 연휴 (마지막날)"),
            # 개천절
            (date(2026, 10, 3), "개천절"),
            # 한글날
            (date(2026, 10, 9), "한글날"),
            # 크리스마스
            (date(2026, 12, 25), "성탄절")
        ]
    else:
        # 기본 공휴일 (년도 별 정확한 날짜가 없을 경우)
        holidays = [
            # 신정
            (date(year, 1, 1), "신정"),
            # 삼일절
            (date(year, 3, 1), "삼일절"),
            # 어린이날
            (date(year, 5, 5), "어린이날"),
            # 현충일
            (date(year, 6, 6), "현충일"),
            # 광복절
            (date(year, 8, 15), "광복절"),
            # 개천절
            (date(year, 10, 3), "개천절"),
            # 한글날
            (date(year, 10, 9), "한글날"),
            # 크리스마스
            (date(year, 12, 25), "성탄절")
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
