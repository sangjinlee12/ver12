from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from models import User, VacationDays, VacationRequest, VacationStatus, Holiday, Role
from forms import EmployeeVacationDaysForm, VacationApprovalForm, HolidayForm
from functools import wraps
from datetime import datetime
import csv
import io
from utils import get_vacation_days_count

admin_bp = Blueprint('admin', __name__)

# 관리자 권한 확인용 데코레이터
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('관리자 권한이 필요합니다.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """관리자 대시보드"""
    # 통계 데이터 준비
    total_employees = User.query.filter_by(role=Role.EMPLOYEE).count()
    pending_requests = VacationRequest.query.filter_by(status=VacationStatus.PENDING).count()
    approved_requests = VacationRequest.query.filter_by(status=VacationStatus.APPROVED).count()
    rejected_requests = VacationRequest.query.filter_by(status=VacationStatus.REJECTED).count()
    
    # 최근 신청된 휴가 목록 (10개)
    recent_requests = VacationRequest.query.order_by(VacationRequest.created_at.desc()).limit(10).all()
    
    # 부서별 휴가 사용 통계
    dept_stats = db.session.query(
        User.department,
        db.func.sum(VacationDays.used_days).label('used'),
        db.func.sum(VacationDays.total_days).label('total')
    ).join(VacationDays, User.id == VacationDays.user_id)\
    .filter(User.department != None)\
    .group_by(User.department).all()
    
    current_year = datetime.now().year
    
    return render_template(
        'admin/dashboard.html',
        total_employees=total_employees,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        rejected_requests=rejected_requests,
        recent_requests=recent_requests,
        dept_stats=dept_stats,
        current_year=current_year
    )

@admin_bp.route('/employees')
@login_required
@admin_required
def manage_employees():
    """직원 관리 페이지"""
    employees = User.query.filter_by(role=Role.EMPLOYEE).all()
    current_year = datetime.now().year
    
    return render_template(
        'admin/manage_employees.html',
        employees=employees,
        current_year=current_year
    )

@admin_bp.route('/employees/vacation-days', methods=['GET', 'POST'])
@login_required
@admin_required
def set_vacation_days():
    """직원 연간 휴가일수 설정"""
    form = EmployeeVacationDaysForm()
    
    if form.validate_on_submit():
        user_id = form.user_id.data
        year = form.year.data
        total_days = form.total_days.data
        
        # 해당 직원의 해당 연도 휴가 정보 검색
        vacation_days = VacationDays.query.filter_by(user_id=user_id, year=year).first()
        
        if vacation_days:
            # 기존 레코드 업데이트
            vacation_days.total_days = total_days
        else:
            # 새 레코드 생성
            vacation_days = VacationDays(
                user_id=user_id,
                year=year,
                total_days=total_days,
                used_days=0
            )
            db.session.add(vacation_days)
        
        db.session.commit()
        flash(f'직원 {User.query.get(user_id).name}의 {year}년 휴가일수가 설정되었습니다.', 'success')
        return redirect(url_for('admin.manage_employees'))
    
    # GET 요청 처리
    user_id = request.args.get('user_id', type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    if user_id:
        user = User.query.get_or_404(user_id)
        vacation_days = VacationDays.query.filter_by(user_id=user_id, year=year).first()
        
        if vacation_days:
            form.total_days.data = vacation_days.total_days
        
        form.user_id.data = user_id
        form.year.data = year
        
        return render_template(
            'admin/set_vacation_days.html',
            form=form,
            user=user,
            year=year
        )
    
    return redirect(url_for('admin.manage_employees'))

@admin_bp.route('/vacations')
@login_required
@admin_required
def manage_vacations():
    """휴가 관리 페이지"""
    status_filter = request.args.get('status', 'all')
    
    # 기본 쿼리
    query = VacationRequest.query
    
    # 상태 필터링
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # 정렬 (최신순)
    vacation_requests = query.order_by(VacationRequest.created_at.desc()).all()
    
    return render_template(
        'admin/manage_vacations.html',
        vacation_requests=vacation_requests,
        status_filter=status_filter
    )

@admin_bp.route('/vacations/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def process_vacation(request_id):
    """휴가 승인/반려 처리"""
    vacation_request = VacationRequest.query.get_or_404(request_id)
    form = VacationApprovalForm()
    
    if form.validate_on_submit():
        vacation_request.status = form.status.data
        vacation_request.comments = form.comments.data
        vacation_request.approved_by = current_user.id
        vacation_request.approval_date = datetime.now()
        
        # 승인될 경우 휴가 일수 업데이트
        if form.status.data == VacationStatus.APPROVED:
            year = vacation_request.start_date.year
            vacation_days = VacationDays.query.filter_by(user_id=vacation_request.user_id, year=year).first()
            
            if vacation_days:
                vacation_days.used_days += vacation_request.days
            
        db.session.commit()
        flash('휴가 요청이 처리되었습니다.', 'success')
        return redirect(url_for('admin.manage_vacations'))
    
    # GET 요청 처리
    form.request_id.data = request_id
    
    return render_template(
        'admin/process_vacation.html',
        form=form,
        vacation_request=vacation_request
    )

@admin_bp.route('/vacations/export')
@login_required
@admin_required
def export_vacations():
    """휴가 데이터 엑셀(CSV) 다운로드"""
    # 필터링 옵션
    year = request.args.get('year', datetime.now().year, type=int)
    status = request.args.get('status', 'all')
    
    # 쿼리 생성
    query = db.session.query(
        User.name,
        User.department,
        User.position,
        VacationRequest.start_date,
        VacationRequest.end_date,
        VacationRequest.days,
        VacationRequest.type,
        VacationRequest.reason,
        VacationRequest.status,
        VacationRequest.created_at
    ).join(User, User.id == VacationRequest.user_id)
    
    # 연도 필터
    query = query.filter(db.extract('year', VacationRequest.start_date) == year)
    
    # 상태 필터
    if status != 'all':
        query = query.filter(VacationRequest.status == status)
    
    # 정렬
    query = query.order_by(VacationRequest.created_at.desc())
    
    # 결과 가져오기
    results = query.all()
    
    # CSV 파일 생성
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 헤더 작성
    writer.writerow(['이름', '부서', '직급', '시작일', '종료일', '일수', '휴가유형', '사유', '상태', '신청일'])
    
    # 데이터 작성
    for row in results:
        writer.writerow([
            row.name,
            row.department or '',
            row.position or '',
            row.start_date.strftime('%Y-%m-%d'),
            row.end_date.strftime('%Y-%m-%d'),
            row.days,
            row.type,
            row.reason or '',
            row.status,
            row.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    # 파일 생성
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # 한글 인코딩 처리
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename=f'vacation_data_{year}.csv'
    )

@admin_bp.route('/holidays', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_holidays():
    """공휴일 관리 페이지"""
    form = HolidayForm()
    
    if form.validate_on_submit():
        # 중복 확인
        existing = Holiday.query.filter_by(date=form.date.data).first()
        if existing:
            flash(f'{form.date.data.strftime("%Y-%m-%d")}는 이미 {existing.name}으로 등록되어 있습니다.', 'warning')
        else:
            holiday = Holiday(
                date=form.date.data,
                name=form.name.data
            )
            db.session.add(holiday)
            db.session.commit()
            flash('공휴일이 등록되었습니다.', 'success')
            return redirect(url_for('admin.manage_holidays'))
    
    # 연도별 공휴일 목록
    year = request.args.get('year', datetime.now().year, type=int)
    holidays = Holiday.query.filter(
        db.extract('year', Holiday.date) == year
    ).order_by(Holiday.date).all()
    
    return render_template(
        'admin/manage_holidays.html',
        form=form,
        holidays=holidays,
        year=year
    )

@admin_bp.route('/holidays/delete/<int:holiday_id>', methods=['POST'])
@login_required
@admin_required
def delete_holiday(holiday_id):
    """공휴일 삭제"""
    holiday = Holiday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    flash('공휴일이 삭제되었습니다.', 'success')
    return redirect(url_for('admin.manage_holidays'))
