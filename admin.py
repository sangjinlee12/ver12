from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, make_response
import pandas as pd
import tempfile
import os
import tempfile
from flask_login import login_required, current_user
from app import db
from models import User, VacationDays, VacationRequest, VacationStatus, Holiday, Role, EmploymentCertificate, CertificateStatus, CompanyInfo
from forms import EmployeeVacationDaysForm, VacationApprovalForm, HolidayForm, CertificateApprovalForm, CompanyInfoForm, EmployeeHireDateForm, BulkUploadForm, VacationSearchForm, AdminVacationForm, EmployeeRegistrationForm, AdminCertificateIssueForm
from functools import wraps
from datetime import datetime, date
import csv
import io
from weasyprint import HTML, CSS
from flask import render_template_string
import os
import tempfile
import pandas as pd
from werkzeug.utils import secure_filename
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
    
    # 추가 통계 데이터
    pending_vacations = VacationRequest.query.filter_by(status=VacationStatus.PENDING).count()
    pending_certificates = EmploymentCertificate.query.filter_by(status=CertificateStatus.PENDING).count()
    total_holidays = Holiday.query.count()
    
    # 최근 휴가 신청 (5개)
    recent_vacations = VacationRequest.query.order_by(VacationRequest.created_at.desc()).limit(5).all()
    
    # 최근 증명서 신청 (5개)
    recent_certificates = EmploymentCertificate.query.order_by(EmploymentCertificate.created_at.desc()).limit(5).all()
    
    # 부서별 인원 통계
    department_stats = {}
    departments = db.session.query(User.department, db.func.count(User.id)).filter(User.department != None).group_by(User.department).all()
    for dept, count in departments:
        department_stats[dept] = count

    return render_template(
        'admin/dashboard_gov.html',
        total_employees=total_employees,
        pending_vacations=pending_vacations,
        pending_certificates=pending_certificates,
        total_holidays=total_holidays,
        recent_vacations=recent_vacations,
        recent_certificates=recent_certificates,
        department_stats=department_stats,
        current_year=current_year
    )

@admin_bp.route('/employees')
@login_required
@admin_required
def manage_employees():
    """직원 관리 페이지"""
    current_year = datetime.now().year
    upload_form = BulkUploadForm()
    
    # 직원과 현재 연도 휴가 데이터 조인하여 가져오기
    employees_query = db.session.query(User, VacationDays).outerjoin(
        VacationDays, 
        (User.id == VacationDays.user_id) & (VacationDays.year == current_year)
    ).filter(User.role == Role.EMPLOYEE).all()
    
    # 직원 목록을 위한 데이터 구조 생성
    from utils import calculate_remaining_vacation_days
    employees = []
    for user, vacation_days in employees_query:
        # 실시간 휴가 잔여일수 계산 및 업데이트
        remaining_days = calculate_remaining_vacation_days(user.id, current_year)
        
        # 사용자 객체에 현재 연도 휴가 데이터 추가
        user.current_vacation_days = vacation_days
        user.remaining_vacation_days = remaining_days  # 실시간 계산된 잔여일수
        employees.append(user)
    
    return render_template(
        'admin/manage_employees.html',
        employees=employees,
        current_year=current_year,
        upload_form=upload_form
    )


@admin_bp.route('/employees/upload', methods=['POST'])
@login_required
@admin_required
def upload_employees():
    """직원 대량 업로드 처리"""
    form = BulkUploadForm()
    
    if form.validate_on_submit():
        try:
            # 업로드된 파일 처리
            file = form.file.data
            filename = secure_filename(file.filename)
            file_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(file_path)
            
            # 파일 확장자에 따라 적절한 pandas 함수 선택
            if filename.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:  # .xls 파일
                df = pd.read_excel(file_path, engine='xlrd')
            
            # 필수 열 확인
            required_columns = ['username', 'name', 'password', 'email', 'resident_id_first', 'resident_id_last_digit', 'department', 'position']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                flash(f'엑셀 파일에 다음 열이 누락되었습니다: {", ".join(missing_columns)}', 'danger')
                return redirect(url_for('admin.manage_employees'))
            
            # 성공 및 오류 카운트
            success_count = 0
            error_count = 0
            error_messages = []
            
            # 각 행 처리
            for idx, row in df.iterrows():
                try:
                    username = str(row['username']).strip()
                    name = str(row['name']).strip()
                    password = str(row['password']).strip()
                    email = str(row['email']).strip()
                    resident_id_first = str(row['resident_id_first']).strip()
                    resident_id_last_digit = str(row['resident_id_last_digit']).strip()
                    department = str(row['department']).strip()
                    position = str(row['position']).strip()
                    
                    # hire_date가 있으면 처리
                    hire_date = None
                    if 'hire_date' in df.columns and pd.notna(row['hire_date']):
                        try:
                            hire_date = pd.to_datetime(row['hire_date']).date()
                        except:
                            hire_date = None
                    
                    # 이미 존재하는 사용자인지 확인
                    existing_user = User.query.filter(
                        (User.username == username) | (User.email == email)
                    ).first()
                    
                    if existing_user:
                        error_count += 1
                        error_messages.append(f"행 {idx+1}: 사용자명({username}) 또는 이메일({email})이 이미 존재합니다.")
                        continue
                    
                    # 새 사용자 생성
                    new_user = User(
                        username=username,
                        email=email,
                        name=name,
                        resident_id_first=resident_id_first,
                        resident_id_last_digit=resident_id_last_digit,
                        department=department,
                        position=position,
                        hire_date=hire_date,
                        role=Role.EMPLOYEE
                    )
                    new_user.set_password(password)
                    db.session.add(new_user)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"행 {idx+1}: {str(e)}")
            
            # 트랜잭션 완료
            db.session.commit()
            
            # 결과 메시지
            if success_count > 0:
                flash(f'{success_count}명의 직원이 성공적으로 등록되었습니다.', 'success')
            if error_count > 0:
                flash(f'{error_count}명의 직원 등록에 실패했습니다.', 'warning')
                for msg in error_messages[:10]:  # 처음 10개의 오류만 표시
                    flash(msg, 'warning')
                if len(error_messages) > 10:
                    flash(f'그 외 {len(error_messages) - 10}개의 오류가 더 있습니다.', 'warning')
            
            # 임시 파일 삭제
            os.remove(file_path)
            
        except Exception as e:
            flash(f'파일 처리 중 오류가 발생했습니다: {str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('admin.manage_employees'))


@admin_bp.route('/employees/template')
@login_required
@admin_required
def download_employee_template():
    """직원 대량 등록 샘플 엑셀 파일 다운로드"""
    # 엑셀 파일 생성
    df = pd.DataFrame(columns=[
        'username', 'name', 'password', 'email', 'resident_id_first', 'resident_id_last_digit', 'department', 'position', 'hire_date'
    ])
    
    # 샘플 데이터 추가
    df.loc[0] = ['employee1', '홍길동', 'password123', 'employee1@example.com', '900101', '1', '영업팀', '사원', '2025-01-02']
    df.loc[1] = ['employee2', '김철수', 'password123', 'employee2@example.com', '910215', '2', '공사팀', '대리', '2024-09-15']
    df.loc[2] = ['employee3', '이영희', 'password123', 'employee3@example.com', '920315', '2', '공무부', '과장', '2023-05-10']
    df.loc[3] = ['employee4', '박민수', 'password123', 'employee4@example.com', '880620', '1', '경리부', '차장', '2022-03-01']
    
    # BytesIO 객체에 엑셀 파일 저장
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    # 응답 생성
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=employee_template.xlsx'
    
    return response

@admin_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    """직원 등록 페이지"""
    form = EmployeeRegistrationForm()
    
    if form.validate_on_submit():
        try:
            # 새 직원 생성
            new_employee = User(
                username=form.username.data,
                email=form.email.data,
                name=form.name.data,
                resident_id_first=form.resident_id_first.data,
                resident_id_last_digit=form.resident_id_last_digit.data,
                department=form.department.data,
                position=form.position.data,
                hire_date=form.hire_date.data,
                role=Role.EMPLOYEE
            )
            new_employee.set_password(form.password.data)
            db.session.add(new_employee)
            db.session.flush()  # ID를 얻기 위해 flush
            
            # 현재 연도와 내년 휴가 일수 설정
            current_year = datetime.now().year
            for year in [current_year, current_year + 1]:
                vacation_days = VacationDays(
                    user_id=new_employee.id,
                    year=year,
                    total_days=15,  # 기본 15일
                    used_days=0
                )
                db.session.add(vacation_days)
            
            db.session.commit()
            flash(f'{form.name.data}님이 성공적으로 등록되었습니다.', 'success')
            return redirect(url_for('admin.manage_employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'직원 등록 중 오류가 발생했습니다: {str(e)}', 'danger')
    
    return render_template('admin/add_employee.html', form=form)

@admin_bp.route('/add_vacation', methods=['GET', 'POST'])
@login_required
@admin_required
def add_vacation():
    """관리자가 직원에게 휴가 등록"""
    form = AdminVacationForm()
    
    # 직원 목록을 폼에 설정
    employees = User.query.filter_by(role=Role.EMPLOYEE).all()
    form.user_id.choices = [(emp.id, f"{emp.name} ({emp.department})") for emp in employees]
    
    if form.validate_on_submit():
        try:
            # 휴가 일수 계산
            vacation_days = get_vacation_days_count(
                form.start_date.data, 
                form.end_date.data, 
                form.type.data
            )
            
            # 직원의 남은 휴가 일수 확인 (특별휴가 제외)
            if form.type.data != '특별휴가':
                year = form.start_date.data.year
                user_vacation_days = VacationDays.query.filter_by(
                    user_id=form.user_id.data, 
                    year=year
                ).first()
                
                if user_vacation_days:
                    remaining_days = user_vacation_days.total_days - user_vacation_days.used_days
                    if vacation_days > remaining_days:
                        flash(f'해당 직원의 남은 휴가 일수가 부족합니다. (남은 일수: {remaining_days}일)', 'danger')
                        return render_template('admin/add_vacation.html', form=form)
            
            # 중복 휴가 신청 확인
            existing_vacation = VacationRequest.query.filter(
                VacationRequest.user_id == form.user_id.data,
                VacationRequest.status.in_([VacationStatus.PENDING, VacationStatus.APPROVED]),
                ((VacationRequest.start_date <= form.start_date.data) & (VacationRequest.end_date >= form.start_date.data)) |
                ((VacationRequest.start_date <= form.end_date.data) & (VacationRequest.end_date >= form.end_date.data))
            ).first()
            
            if existing_vacation:
                flash('해당 기간에 이미 휴가가 등록되어 있습니다.', 'danger')
                return render_template('admin/add_vacation.html', form=form)
            
            # 새로운 휴가 신청 생성 (자동 승인 상태)
            new_vacation = VacationRequest(
                user_id=form.user_id.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                days=vacation_days,
                type=form.type.data,
                reason=form.reason.data,
                status=VacationStatus.APPROVED,  # 관리자가 등록하므로 자동 승인
                approved_by=current_user.id,
                approval_date=datetime.now()
            )
            
            db.session.add(new_vacation)
            
            # 특별휴가가 아닌 경우 휴가 일수 차감
            if form.type.data != '특별휴가':
                year = form.start_date.data.year
                user_vacation_days = VacationDays.query.filter_by(
                    user_id=form.user_id.data, 
                    year=year
                ).first()
                
                if user_vacation_days:
                    user_vacation_days.used_days = (user_vacation_days.used_days or 0) + vacation_days
                else:
                    # 휴가 일수 레코드가 없으면 생성
                    new_vacation_days = VacationDays(
                        user_id=form.user_id.data,
                        year=year,
                        total_days=15,  # 기본 15일
                        used_days=vacation_days
                    )
                    db.session.add(new_vacation_days)
            
            db.session.commit()
            
            user = User.query.get(form.user_id.data)
            flash(f'{user.name}님의 휴가가 성공적으로 등록되었습니다.', 'success')
            return redirect(url_for('admin.manage_vacations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'휴가 등록 중 오류가 발생했습니다: {str(e)}', 'danger')
    
    return render_template('admin/add_vacation.html', form=form)

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

@admin_bp.route('/vacations', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_vacations():
    """휴가 관리 페이지 (기간 검색 및 엑셀 출력 지원)"""
    form = VacationSearchForm()
    
    # 기본 쿼리
    query = db.session.query(
        VacationRequest,
        User.name,
        User.department,
        User.position
    ).join(User, User.id == VacationRequest.user_id)
    
    # 폼 처리 (POST 요청 모두 처리)
    if request.method == 'POST':
        # 엑셀 다운로드 요청
        if form.export.data:
            return export_vacation_data(form)
        
        # 검색 필터 적용 (우선순위: 년도/월 > 기간 > 기타)
        
        # 1. 년도/월 검색 (우선순위 높음)
        if form.year.data and form.year.data != 0:
            # SQLite에서는 extract 대신 strftime 사용
            from sqlalchemy import func
            query = query.filter(func.strftime('%Y', VacationRequest.start_date) == str(form.year.data))
            
            # 월이 선택된 경우 해당 월만 검색
            if hasattr(form, 'month') and form.month.data and form.month.data != 0:
                month_str = f'{form.month.data:02d}'  # 01, 02, ..., 12 형식
                query = query.filter(func.strftime('%m', VacationRequest.start_date) == month_str)
        
        # 2. 기간 검색 (년도가 선택되지 않은 경우에만 적용)
        elif form.start_date.data or form.end_date.data:
            if form.start_date.data:
                query = query.filter(VacationRequest.start_date >= form.start_date.data)
            if form.end_date.data:
                query = query.filter(VacationRequest.end_date <= form.end_date.data)
        
        # 3. 직원명 검색 (선택사항)
        if form.employee_name.data and form.employee_name.data.strip():
            query = query.filter(User.name.contains(form.employee_name.data.strip()))
        
        # 4. 상태 검색
        if form.status.data != 'all':
            query = query.filter(VacationRequest.status == form.status.data)
        
        # 5. 부서 검색
        if form.department.data != 'all':
            query = query.filter(User.department == form.department.data)
    
    # URL 파라미터로부터 필터 적용 (기존 호환성)
    status_filter = request.args.get('status', 'all')
    if status_filter != 'all' and request.method != 'POST':
        query = query.filter(VacationRequest.status == status_filter)
        form.status.data = status_filter
    
    # 정렬 (최신순)
    results = query.order_by(VacationRequest.created_at.desc()).all()
    
    # 결과 정리
    vacation_requests = []
    for vacation_request, name, department, position in results:
        vacation_request.user_name = name
        vacation_request.user_department = department
        vacation_request.user_position = position
        vacation_requests.append(vacation_request)
    
    return render_template(
        'admin/manage_vacations.html',
        vacation_requests=vacation_requests,
        status_filter=status_filter,
        search_form=form
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

def export_vacation_data(form):
    """휴가 데이터 엑셀 다운로드 (검색 조건 적용)"""
    try:
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
            VacationRequest.created_at,
            VacationRequest.approval_date,
            User.username
        ).join(User, User.id == VacationRequest.user_id)
        
        # 검색 조건 적용 (엑셀 출력용)
        
        # 1. 년도/월 검색 (우선순위 높음)
        if hasattr(form, 'year') and form.year.data and form.year.data != 0:
            from sqlalchemy import func
            query = query.filter(func.strftime('%Y', VacationRequest.start_date) == str(form.year.data))
            
            # 월이 선택된 경우 해당 월만 검색
            if hasattr(form, 'month') and form.month.data and form.month.data != 0:
                month_str = f'{form.month.data:02d}'  # 01, 02, ..., 12 형식
                query = query.filter(func.strftime('%m', VacationRequest.start_date) == month_str)
        
        # 2. 기간 검색 (년도가 선택되지 않은 경우에만 적용)
        elif (hasattr(form, 'start_date') and form.start_date.data) or (hasattr(form, 'end_date') and form.end_date.data):
            if hasattr(form, 'start_date') and form.start_date.data:
                query = query.filter(VacationRequest.start_date >= form.start_date.data)
            if hasattr(form, 'end_date') and form.end_date.data:
                query = query.filter(VacationRequest.end_date <= form.end_date.data)
        
        # 3. 직원명 검색 (선택사항)
        if hasattr(form, 'employee_name') and form.employee_name.data and form.employee_name.data.strip():
            query = query.filter(User.name.contains(form.employee_name.data.strip()))
        
        # 4. 상태 검색
        if hasattr(form, 'status') and form.status.data != 'all':
            query = query.filter(VacationRequest.status == form.status.data)
        
        # 5. 부서 검색
        if hasattr(form, 'department') and form.department.data != 'all':
            query = query.filter(User.department == form.department.data)
        
        # 정렬
        query = query.order_by(VacationRequest.created_at.desc())
        
        # 결과 가져오기
        results = query.all()
        
        if not results:
            # 데이터가 없는 경우 빈 엑셀 파일 생성
            data = [{'메시지': '검색 조건에 맞는 휴가 데이터가 없습니다.'}]
        else:
            # 엑셀 파일 생성 (pandas 이용)
            data = []
            for row in results:
                data.append({
                    '이름': row.name,
                    '아이디': row.username,
                    '부서': row.department or '',
                    '직급': row.position or '',
                    '휴가시작일': row.start_date.strftime('%Y-%m-%d'),
                    '휴가종료일': row.end_date.strftime('%Y-%m-%d'),
                    '휴가일수': float(row.days),
                    '휴가유형': row.type,
                    '휴가사유': row.reason or '',
                    '상태': row.status,
                    '신청일시': row.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    '승인일시': row.approval_date.strftime('%Y-%m-%d %H:%M:%S') if row.approval_date else ''
                })
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 파일명 생성
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'vacation_data_{current_time}.xlsx'
        
        # BytesIO를 사용하여 메모리에서 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='휴가현황')
        
        output.seek(0)
        excel_data = output.getvalue()
        
        # 응답 생성
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        flash(f'엑셀 다운로드 중 오류가 발생했습니다: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_vacations'))


@admin_bp.route('/vacations/export')
@login_required
@admin_required
def export_vacations():
    """휴가 데이터 엑셀(CSV) 다운로드 (기존 호환성)"""
    # 필터링 옵션
    year = request.args.get('year', datetime.now().year, type=int)
    status = request.args.get('status', 'all')
    
    # 폼 생성 및 데이터 설정
    form = VacationSearchForm()
    if year != datetime.now().year:
        form.year.data = year
    if status != 'all':
        form.status.data = status
    
    return export_vacation_data(form)

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


@admin_bp.route('/certificates')
@login_required
@admin_required
def manage_certificates():
    """재직증명서 관리 페이지"""
    status_filter = request.args.get('status', 'all')
    
    # 기본 쿼리
    query = db.session.query(
        EmploymentCertificate,
        User.name,
        User.department,
        User.position
    ).join(User, User.id == EmploymentCertificate.user_id)
    
    # 상태 필터링
    if status_filter != 'all':
        query = query.filter(EmploymentCertificate.status == status_filter)
    
    # 정렬 (최신순)
    certificates = query.order_by(EmploymentCertificate.created_at.desc()).all()
    
    # 관리자 직접 발행 폼
    issue_form = AdminCertificateIssueForm()
    
    # 직원 목록 (관리자 제외)
    employees = User.query.filter_by(role=Role.EMPLOYEE).order_by(User.name).all()
    issue_form.user_id.choices = [(emp.id, f"{emp.name} ({emp.department or '미지정'})") for emp in employees]
    
    return render_template(
        'admin/manage_certificates.html',
        certificates=certificates,
        status_filter=status_filter,
        issue_form=issue_form
    )


@admin_bp.route('/certificates/direct-issue', methods=['POST'])
@login_required
@admin_required
def direct_issue_certificate():
    """관리자 직접 증명서 발행"""
    form = AdminCertificateIssueForm()
    
    # 직원 목록 설정
    employees = User.query.filter_by(role=Role.EMPLOYEE).order_by(User.name).all()
    form.user_id.choices = [(emp.id, f"{emp.name} ({emp.department or '미지정'})") for emp in employees]
    
    if form.validate_on_submit():
        # 직원 정보 확인
        employee = User.query.get(form.user_id.data)
        if not employee or employee.role != Role.EMPLOYEE:
            flash('유효하지 않은 직원입니다.', 'danger')
            return redirect(url_for('admin.manage_certificates'))
        
        # 증명서 즉시 발급
        certificate = EmploymentCertificate(
            user_id=employee.id,
            purpose=form.purpose.data,
            status=CertificateStatus.ISSUED,  # 즉시 발급완료 상태
            comments=form.comments.data or f"관리자({current_user.name})가 직접 발급",
            approved_by=current_user.id,
            approval_date=datetime.now(),
            issued_date=datetime.now().date()
        )
        
        db.session.add(certificate)
        db.session.commit()
        
        flash(f'{employee.name} 직원의 재직증명서가 즉시 발급되었습니다.', 'success')
        return redirect(url_for('admin.manage_certificates'))
    
    # 폼 에러가 있는 경우
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{form[field].label.text}: {error}', 'danger')
    
    return redirect(url_for('admin.manage_certificates'))


@admin_bp.route('/certificates/<int:certificate_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def process_certificate(certificate_id):
    """재직증명서 승인/반려 처리"""
    certificate = EmploymentCertificate.query.get_or_404(certificate_id)
    form = CertificateApprovalForm()
    
    if form.validate_on_submit():
        certificate.status = form.status.data
        certificate.comments = form.comments.data
        certificate.approved_by = current_user.id
        certificate.approval_date = datetime.now()
        
        # 발급완료일 경우 발급일 기록
        if form.status.data == CertificateStatus.ISSUED:
            certificate.issued_date = datetime.now().date()
        
        db.session.commit()
        flash('재직증명서 요청이 처리되었습니다.', 'success')
        return redirect(url_for('admin.manage_certificates'))
    
    # GET 요청 처리
    form.certificate_id.data = certificate_id
    
    # 신청자 정보 조회
    user = User.query.get(certificate.user_id)
    
    return render_template(
        'admin/process_certificate.html',
        form=form,
        certificate=certificate,
        user=user
    )


@admin_bp.route('/certificates/<int:certificate_id>/download')
@login_required
@admin_required
def download_certificate(certificate_id):
    """재직증명서 PDF 다운로드"""
    certificate = EmploymentCertificate.query.get_or_404(certificate_id)
    
    # 발급완료 상태만 다운로드 가능
    if certificate.status != CertificateStatus.ISSUED:
        flash('발급완료된 증명서만 다운로드할 수 있습니다.', 'warning')
        return redirect(url_for('admin.manage_certificates'))
    
    # 직원 정보 조회
    employee = User.query.get(certificate.user_id)
    if not employee:
        flash('직원 정보를 찾을 수 없습니다.', 'danger')
        return redirect(url_for('admin.manage_certificates'))
    
    # 회사 정보 조회
    company_info = CompanyInfo.query.first()
    if not company_info:
        # 기본 회사 정보 설정
        company_info = CompanyInfo(
            name="에스에스전력 주식회사",
            ceo_name="이상진",
            registration_number="123-45-67890",
            address="서울특별시 강남구 테헤란로 123",
            phone="02-1234-5678",
            fax="02-1234-5679"
        )
    
    try:
        # PDF 생성
        pdf_buffer = generate_certificate_pdf(certificate, employee, company_info)
        
        # 파일명 생성
        filename = f"재직증명서_{employee.name}_{certificate.issued_date.strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    
    except Exception as e:
        flash(f'PDF 생성 중 오류가 발생했습니다: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_certificates'))


def generate_certificate_pdf(certificate, employee, company_info):
    """재직증명서 PDF 생성 (WeasyPrint 사용)"""
    
    # HTML 템플릿 생성
    html_template = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>재직증명서</title>
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            
            body {
                font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
            }
            
            .certificate-container {
                max-width: 100%;
                margin: 0 auto;
                padding: 40px 20px;
            }
            
            .certificate-title {
                text-align: center;
                font-size: 32px;
                font-weight: bold;
                margin-bottom: 50px;
                letter-spacing: 8px;
                border-bottom: 3px solid #1a365d;
                padding-bottom: 20px;
            }
            
            .employee-info {
                width: 100%;
                border-collapse: collapse;
                margin: 40px 0;
                font-size: 16px;
            }
            
            .employee-info th,
            .employee-info td {
                border: 2px solid #333;
                padding: 15px 20px;
                text-align: left;
            }
            
            .employee-info th {
                background-color: #f8f9fa;
                font-weight: bold;
                width: 25%;
            }
            
            .certificate-content {
                font-size: 16px;
                line-height: 2;
                margin: 50px 0;
                text-align: justify;
            }
            
            .purpose-section {
                margin: 30px 0;
                padding: 20px;
                background-color: #f8f9fa;
                border-left: 5px solid #1a365d;
            }
            
            .issue-date {
                text-align: center;
                font-size: 18px;
                font-weight: bold;
                margin: 50px 0 30px 0;
            }
            
            .company-info {
                text-align: center;
                font-size: 18px;
                line-height: 1.8;
                margin: 40px 0;
            }
            
            .company-name {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            
            .ceo-name {
                font-size: 20px;
                margin: 15px 0;
            }
            
            .company-details {
                font-size: 14px;
                color: #666;
                margin-top: 20px;
            }
            
            .stamp {
                text-align: center;
                font-size: 16px;
                margin-top: 40px;
                border: 2px solid #333;
                width: 100px;
                height: 100px;
                line-height: 96px;
                margin: 40px auto;
                border-radius: 50%;
            }
        </style>
    </head>
    <body>
        <div class="certificate-container">
            <h1 class="certificate-title">재 직 증 명 서</h1>
            
            <table class="employee-info">
                <tr>
                    <th>성 명</th>
                    <td>{{ employee_name }}</td>
                </tr>
                <tr>
                    <th>부 서</th>
                    <td>{{ employee_department }}</td>
                </tr>
                <tr>
                    <th>직 급</th>
                    <td>{{ employee_position }}</td>
                </tr>
                <tr>
                    <th>입 사 일</th>
                    <td>{{ hire_date }}</td>
                </tr>
            </table>
            
            <div class="certificate-content">
                <p>위 사람은 본 회사의 직원으로 <strong>재직 중임을 증명</strong>합니다.</p>
                
                <div class="purpose-section">
                    <strong>사용목적:</strong> {{ purpose }}
                </div>
                
                <p>본 증명서는 {{ purpose }}에 한하여 사용되며, 다른 용도로 사용할 수 없습니다.</p>
            </div>
            
            <div class="issue-date">
                발급일: {{ issue_date }}
            </div>
            
            <div class="company-info">
                <div class="company-name">{{ company_name }}</div>
                <div class="ceo-name">대표이사: {{ ceo_name }}</div>
                
                <div class="company-details">
                    {% if company_address %}
                    <div>주소: {{ company_address }}</div>
                    {% endif %}
                    {% if company_phone %}
                    <div>전화: {{ company_phone }}</div>
                    {% endif %}
                </div>
            </div>
            
            <div class="stamp">(직인)</div>
        </div>
    </body>
    </html>
    """
    
    # 템플릿 데이터 준비
    template_data = {
        'employee_name': employee.name or '',
        'employee_department': employee.department or '미지정',
        'employee_position': employee.position or '미지정',
        'hire_date': employee.hire_date.strftime('%Y년 %m월 %d일') if employee.hire_date else '정보없음',
        'purpose': certificate.purpose,
        'issue_date': certificate.issued_date.strftime('%Y년 %m월 %d일'),
        'company_name': company_info.name,
        'ceo_name': company_info.ceo_name,
        'company_address': company_info.address,
        'company_phone': company_info.phone
    }
    
    # HTML 렌더링
    html_content = render_template_string(html_template, **template_data)
    
    # PDF 생성
    buffer = io.BytesIO()
    HTML(string=html_content).write_pdf(buffer)
    buffer.seek(0)
    
    return buffer


@admin_bp.route('/employees/<int:user_id>/vacation-report')
@login_required
@admin_required
def employee_vacation_report(user_id):
    """직원별 휴가 사용 보고서"""
    user = User.query.get_or_404(user_id)
    
    # 관리자는 보고서를 볼 수 없음
    if user.role == Role.ADMIN:
        flash('관리자 계정의 휴가 보고서는 조회할 수 없습니다.', 'danger')
        return redirect(url_for('admin.manage_employees'))
    
    # 연도별 휴가 데이터 조회 (최근 3년)
    current_year = datetime.now().year
    years_data = []
    
    for year in range(current_year - 2, current_year + 1):
        # VacationDays 데이터 조회
        vacation_days = VacationDays.query.filter_by(user_id=user.id, year=year).first()
        
        # 해당 연도 휴가 신청 내역
        from sqlalchemy import func
        vacation_requests = VacationRequest.query.filter(
            VacationRequest.user_id == user.id,
            func.strftime('%Y', VacationRequest.start_date) == str(year)
        ).order_by(VacationRequest.start_date).all()
        
        # 승인된 휴가 총 일수
        approved_days = sum(req.days for req in vacation_requests if req.status == '승인됨')
        
        # 실시간 잔여 휴가 계산
        from utils import calculate_remaining_vacation_days
        remaining_days = calculate_remaining_vacation_days(user.id, year)
        
        years_data.append({
            'year': year,
            'vacation_days': vacation_days,
            'vacation_requests': vacation_requests,
            'approved_days': approved_days,
            'remaining_days': remaining_days,
            'total_days': vacation_days.total_days if vacation_days else 15
        })
    
    return render_template(
        'admin/employee_vacation_report.html',
        user=user,
        years_data=years_data,
        current_year=current_year
    )


@admin_bp.route('/employees/<int:user_id>/vacation-report/export')
@login_required
@admin_required
def export_employee_vacation_report(user_id):
    """직원별 휴가 보고서 엑셀 출력"""
    user = User.query.get_or_404(user_id)
    
    if user.role == Role.ADMIN:
        flash('관리자 계정의 휴가 보고서는 출력할 수 없습니다.', 'danger')
        return redirect(url_for('admin.manage_employees'))
    
    # 데이터 준비
    current_year = datetime.now().year
    all_requests = []
    
    # 최근 3년간 휴가 신청 내역
    from sqlalchemy import func
    vacation_requests = VacationRequest.query.filter(
        VacationRequest.user_id == user.id,
        func.strftime('%Y', VacationRequest.start_date).between(str(current_year - 2), str(current_year))
    ).order_by(VacationRequest.start_date).all()
    
    for req in vacation_requests:
        all_requests.append({
            '연도': req.start_date.year,
            '신청일': req.created_at.strftime('%Y-%m-%d'),
            '시작일': req.start_date.strftime('%Y-%m-%d'),
            '종료일': req.end_date.strftime('%Y-%m-%d'),
            '일수': req.days,
            '휴가종류': req.type,
            '사유': req.reason or '-',
            '상태': req.status,
            '승인일': req.approval_date.strftime('%Y-%m-%d') if req.approval_date else '-',
            '승인자': req.approver.name if req.approver else '-'
        })
    
    # DataFrame 생성
    df = pd.DataFrame(all_requests)
    
    # 엑셀 파일 생성
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 상세 내역 시트
        df.to_excel(writer, sheet_name='휴가신청내역', index=False)
        
        # 연도별 요약 시트
        summary_data = []
        for year in range(current_year - 2, current_year + 1):
            vacation_days = VacationDays.query.filter_by(user_id=user.id, year=year).first()
            year_requests = [req for req in vacation_requests if req.start_date.year == year]
            approved_days = sum(req.days for req in year_requests if req.status == '승인됨')
            
            from utils import calculate_remaining_vacation_days
            remaining_days = calculate_remaining_vacation_days(user.id, year)
            
            summary_data.append({
                '연도': year,
                '총휴가일수': vacation_days.total_days if vacation_days else 15,
                '사용일수': approved_days,
                '잔여일수': remaining_days,
                '신청건수': len(year_requests),
                '승인건수': len([req for req in year_requests if req.status == '승인됨']),
                '대기건수': len([req for req in year_requests if req.status == '대기중']),
                '반려건수': len([req for req in year_requests if req.status == '반려됨'])
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='연도별요약', index=False)
    
    output.seek(0)
    
    # 파일명 생성
    filename = f"{user.name}_휴가보고서_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@admin_bp.route('/employees/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_employee(user_id):
    """직원 삭제"""
    user = User.query.get_or_404(user_id)
    
    # 관리자는 삭제할 수 없음
    if user.role == Role.ADMIN:
        flash('관리자 계정은 삭제할 수 없습니다.', 'danger')
        return redirect(url_for('admin.manage_employees'))
    
    # 사용자 정보 미리 저장
    user_name = user.name
    
    try:
        # 휴가 데이터 삭제
        VacationDays.query.filter_by(user_id=user.id).delete()
        # 휴가 신청 삭제
        VacationRequest.query.filter_by(user_id=user.id).delete()
        # 재직증명서 신청 삭제
        EmploymentCertificate.query.filter_by(user_id=user.id).delete()
        
        # 사용자 삭제
        db.session.delete(user)
        db.session.commit()
        
        flash(f'{user_name} 직원이 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'직원 삭제 중 오류가 발생했습니다: {str(e)}', 'danger')
        
    return redirect(url_for('admin.manage_employees'))


@admin_bp.route('/company-info', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_company_info():
    """회사 정보 관리 페이지"""
    # 회사 정보 가져오기 (없으면 빈 객체 생성)
    company_info = CompanyInfo.query.first()
    form = CompanyInfoForm()
    
    if form.validate_on_submit():
        # 회사 정보가 없으면 새로 생성
        if not company_info:
            company_info = CompanyInfo()
            db.session.add(company_info)
        
        # 폼 데이터 할당
        company_info.name = form.name.data
        company_info.ceo_name = form.ceo_name.data
        company_info.registration_number = form.registration_number.data
        company_info.address = form.address.data
        company_info.phone = form.phone.data
        company_info.fax = form.fax.data
        company_info.website = form.website.data
        company_info.stamp_image = form.stamp_image.data
        
        db.session.commit()
        flash('회사 정보가 성공적으로 저장되었습니다.', 'success')
        return redirect(url_for('admin.manage_company_info'))
    
    # GET 요청 처리 또는 폼 초기화
    if company_info:
        form.name.data = company_info.name
        form.ceo_name.data = company_info.ceo_name
        form.registration_number.data = company_info.registration_number
        form.address.data = company_info.address
        form.phone.data = company_info.phone
        form.fax.data = company_info.fax
        form.website.data = company_info.website
        form.stamp_image.data = company_info.stamp_image
    
    return render_template(
        'admin/manage_company_info.html',
        form=form,
        company_info=company_info
    )


@admin_bp.route('/employees/hire-date', methods=['GET', 'POST'])
@login_required
@admin_required
def set_hire_date():
    """직원 입사일 설정"""
    form = EmployeeHireDateForm()
    
    if form.validate_on_submit():
        user_id = form.user_id.data
        hire_date = form.hire_date.data
        
        # 해당 직원 정보 가져오기
        user = User.query.get_or_404(user_id)
        
        # 입사일 업데이트
        user.hire_date = hire_date
        db.session.commit()
        
        flash(f'직원 {user.name}의 입사일이 설정되었습니다.', 'success')
        return redirect(url_for('admin.manage_employees'))
    
    # GET 요청 처리
    user_id = request.args.get('user_id', type=int)
    
    if user_id:
        user = User.query.get_or_404(user_id)
        form.user_id.data = user_id
        
        # 기존 입사일 있으면 폼에 설정
        if user.hire_date:
            form.hire_date.data = user.hire_date
        
        return render_template(
            'admin/set_hire_date.html',
            form=form,
            user=user
        )
    
    return redirect(url_for('admin.manage_employees'))
