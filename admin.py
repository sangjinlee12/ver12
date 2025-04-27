from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, make_response
from flask_login import login_required, current_user
from app import db
from models import User, VacationDays, VacationRequest, VacationStatus, Holiday, Role, EmploymentCertificate, CertificateStatus, CompanyInfo
from forms import EmployeeVacationDaysForm, VacationApprovalForm, HolidayForm, CertificateApprovalForm, CompanyInfoForm, EmployeeHireDateForm, BulkUploadForm
from functools import wraps
from datetime import datetime
import csv
import io
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
    upload_form = BulkUploadForm()
    
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
    
    return render_template(
        'admin/manage_certificates.html',
        certificates=certificates,
        status_filter=status_filter
    )


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
