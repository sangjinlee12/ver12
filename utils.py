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

def get_vacation_days_count(start_date, end_date, vacation_type=None):
    """휴가 일수 계산 (주말, 공휴일 제외)"""
    if start_date > end_date:
        return 0
    
    # 반차 처리
    if vacation_type and '반차' in vacation_type:
        return 0.5
    
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

def calculate_remaining_vacation_days(user_id, year=None):
    """사용자의 잔여 휴가일수 계산"""
    from models import User, VacationDays
    
    if year is None:
        year = datetime.now().year
    
    # 사용자 정보 조회
    user = User.query.get(user_id)
    if not user:
        return 0
    
    # 해당 연도의 휴가 일수 설정 조회
    vacation_days = VacationDays.query.filter_by(
        user_id=user_id,
        year=year
    ).first()
    
    # 없으면 기본값으로 생성
    if not vacation_days:
        vacation_days = VacationDays(
            user_id=user_id,
            year=year,
            total_days=15,  # 기본값
            used_days=0
        )
        db.session.add(vacation_days)
        db.session.commit()
    
    # 해당 연도의 승인된 휴가 총 일수 계산
    from sqlalchemy import func
    used_days = db.session.query(
        func.coalesce(func.sum(VacationRequest.days), 0)
    ).filter(
        VacationRequest.user_id == user_id,
        VacationRequest.status == '승인됨',
        func.strftime('%Y', VacationRequest.start_date) == str(year)
    ).scalar()
    
    # VacationDays 테이블의 used_days도 업데이트
    vacation_days.used_days = used_days or 0
    db.session.commit()
    
    # 잔여 휴가일수 = 총 휴가일수 - 사용한 휴가일수
    remaining = vacation_days.total_days - (used_days or 0)
    return max(0, remaining)  # 음수가 되지 않도록

def get_current_year_vacations(year=None):
    """연도별 휴가 통계 조회"""
    if year is None:
        year = datetime.now().year
    
    # SQLite 환경에서는 strftime 사용
    from sqlalchemy import func
    stats = db.session.query(
        func.coalesce(func.sum(VacationRequest.days), 0).label('total_used_days'),
        func.count(VacationRequest.id).label('total_requests')
    ).filter(
        func.strftime('%Y', VacationRequest.start_date) == str(year)
    ).first()
    
    return stats
