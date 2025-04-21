from app import db
from models import Holiday, VacationRequest
from datetime import datetime, timedelta

def is_weekend(date):
    """주말인지 확인 (토:5, 일:6)"""
    return date.weekday() >= 5

def is_holiday(date):
    """공휴일인지 확인"""
    holiday = Holiday.query.filter_by(date=date).first()
    return holiday is not None

def get_vacation_days_count(start_date, end_date):
    """휴가 일수 계산 (주말, 공휴일 제외)"""
    if start_date > end_date:
        return 0
    
    # 같은 날짜면 1일
    if start_date == end_date:
        if is_weekend(start_date) or is_holiday(start_date):
            return 0
        return 1
    
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        if not is_weekend(current_date) and not is_holiday(current_date):
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days

def check_overlapping_vacation(user_id, start_date, end_date):
    """같은 기간에 이미 신청한 휴가가 있는지 확인"""
    overlapping = VacationRequest.query.filter(
        VacationRequest.user_id == user_id,
        VacationRequest.start_date <= end_date,
        VacationRequest.end_date >= start_date
    ).first()
    
    return overlapping is not None

def get_current_year_vacations(year=None):
    """연도별 휴가 통계 조회"""
    if year is None:
        year = datetime.now().year
    
    # 연도별 휴가 통계 쿼리
    stats = db.session.query(
        db.func.sum(VacationRequest.days).label('total_used_days'),
        db.func.count(VacationRequest.id).label('total_requests')
    ).filter(
        db.extract('year', VacationRequest.start_date) == year
    ).first()
    
    return stats
