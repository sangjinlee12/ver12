from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from models import VacationDays, VacationRequest, VacationStatus, EmploymentCertificate, CertificateStatus, CompanyInfo
from forms import VacationRequestForm, EmploymentCertificateRequestForm
from datetime import datetime
from utils import get_vacation_days_count, check_overlapping_vacation
import tempfile
import os
import urllib.parse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/dashboard')
@login_required
def dashboard():
    """직원 대시보드"""
    # 현재 연도의 휴가 정보 가져오기
    current_year = datetime.now().year
    vacation_days = VacationDays.query.filter_by(
        user_id=current_user.id,
        year=current_year
    ).first()
    
    # 없으면 생성
    if not vacation_days:
        vacation_days = VacationDays(
            user_id=current_user.id,
            year=current_year,
            total_days=15,  # 기본값
            used_days=0
        )
        db.session.add(vacation_days)
        db.session.commit()
    
    # 최근 휴가 신청 내역 (5개)
    recent_requests = VacationRequest.query.filter_by(
        user_id=current_user.id
    ).order_by(VacationRequest.created_at.desc()).limit(5).all()
    
    # 대기중인 휴가 신청 수
    pending_count = VacationRequest.query.filter_by(
        user_id=current_user.id,
        status=VacationStatus.PENDING
    ).count()
    
    # 승인된 휴가 신청 수
    approved_count = VacationRequest.query.filter_by(
        user_id=current_user.id,
        status=VacationStatus.APPROVED
    ).count()
    
    return render_template(
        'employee/dashboard.html',
        vacation_days=vacation_days,
        recent_requests=recent_requests,
        pending_count=pending_count,
        approved_count=approved_count,
        current_year=current_year
    )

@employee_bp.route('/request-vacation', methods=['GET', 'POST'])
@login_required
def request_vacation():
    """휴가 신청 페이지"""
    form = VacationRequestForm()
    
    if form.validate_on_submit():
        # 현재 연도의 휴가 정보 가져오기
        year = form.start_date.data.year
        vacation_days = VacationDays.query.filter_by(
            user_id=current_user.id,
            year=year
        ).first()
        
        # 없으면 생성
        if not vacation_days:
            vacation_days = VacationDays(
                user_id=current_user.id,
                year=year,
                total_days=15,  # 기본값
                used_days=0
            )
            db.session.add(vacation_days)
            db.session.commit()
        
        # 휴가 일수 계산
        type_days = {
            '연차': float(form.days.data),
            '반차(오전)': 0.5,
            '반차(오후)': 0.5,
            '특별휴가': float(form.days.data)
        }
        days = type_days.get(form.type.data, float(form.days.data))
        
        # 남은 휴가 일수 확인 (특별휴가는 연차 차감 없음)
        if form.type.data != '특별휴가' and days > vacation_days.remaining_days():
            flash('남은 휴가 일수가 부족합니다.', 'danger')
            return render_template('employee/request_vacation.html', form=form)
        
        # 같은 기간에 이미 신청한 휴가가 있는지 확인
        if check_overlapping_vacation(current_user.id, form.start_date.data, form.end_date.data):
            flash('이미 해당 기간에 신청한 휴가가 있습니다.', 'danger')
            return render_template('employee/request_vacation.html', form=form)
        
        # 휴가 신청 저장
        vacation_request = VacationRequest(
            user_id=current_user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            days=days,
            reason=form.reason.data,
            type=form.type.data,
            status=VacationStatus.PENDING
        )
        
        db.session.add(vacation_request)
        db.session.commit()
        
        flash('휴가 신청이 완료되었습니다.', 'success')
        return redirect(url_for('employee.my_vacations'))
    
    return render_template('employee/request_vacation.html', form=form)

@employee_bp.route('/my-vacations')
@login_required
def my_vacations():
    """내 휴가 내역 페이지"""
    # 필터링 옵션
    year = request.args.get('year', datetime.now().year, type=int)
    status = request.args.get('status', 'all')
    
    # 쿼리 생성
    query = VacationRequest.query.filter_by(user_id=current_user.id)
    
    # 연도 필터
    query = query.filter(db.extract('year', VacationRequest.start_date) == year)
    
    # 상태 필터
    if status != 'all':
        query = query.filter_by(status=status)
    
    # 정렬 (최신순)
    vacation_requests = query.order_by(VacationRequest.created_at.desc()).all()
    
    # 연도별 휴가 정보
    vacation_days = VacationDays.query.filter_by(
        user_id=current_user.id,
        year=year
    ).first()
    
    if not vacation_days:
        vacation_days = VacationDays(
            user_id=current_user.id,
            year=year,
            total_days=15,  # 기본값
            used_days=0
        )
        db.session.add(vacation_days)
        db.session.commit()
    
    return render_template(
        'employee/my_vacations.html',
        vacation_requests=vacation_requests,
        vacation_days=vacation_days,
        year=year,
        status_filter=status
    )

@employee_bp.route('/cancel-vacation/<int:request_id>', methods=['POST'])
@login_required
def cancel_vacation(request_id):
    """휴가 신청 취소"""
    vacation_request = VacationRequest.query.get_or_404(request_id)
    
    # 권한 확인
    if vacation_request.user_id != current_user.id:
        flash('권한이 없습니다.', 'danger')
        return redirect(url_for('employee.my_vacations'))
    
    # 대기 중인 신청만 취소 가능
    if vacation_request.status != VacationStatus.PENDING:
        flash('대기 중인 휴가 신청만 취소할 수 있습니다.', 'danger')
        return redirect(url_for('employee.my_vacations'))
    
    # 취소 처리
    db.session.delete(vacation_request)
    db.session.commit()
    
    flash('휴가 신청이 취소되었습니다.', 'success')
    return redirect(url_for('employee.my_vacations'))

@employee_bp.route('/calculate-vacation-days', methods=['POST'])
@login_required
def calculate_vacation_days():
    """휴가 일수 계산 API"""
    data = request.json
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    vacation_type = data.get('type', '연차')
    
    if vacation_type in ['반차(오전)', '반차(오후)']:
        days = 0.5
    else:
        days = get_vacation_days_count(start_date, end_date)
    
    return jsonify({'days': days})


@employee_bp.route('/request-certificate', methods=['GET', 'POST'])
@login_required
def request_certificate():
    """재직증명서 신청 페이지"""
    form = EmploymentCertificateRequestForm()
    
    if form.validate_on_submit():
        # 재직증명서 신청 저장
        certificate = EmploymentCertificate(
            user_id=current_user.id,
            purpose=form.purpose.data,
            status=CertificateStatus.PENDING
        )
        
        db.session.add(certificate)
        db.session.commit()
        
        flash('재직증명서 신청이 완료되었습니다.', 'success')
        return redirect(url_for('employee.my_certificates'))
    
    return render_template('employee/request_certificate.html', form=form)


@employee_bp.route('/my-certificates')
@login_required
def my_certificates():
    """내 재직증명서 신청 내역 페이지"""
    # 재직증명서 신청 내역 (최신순)
    certificates = EmploymentCertificate.query.filter_by(
        user_id=current_user.id
    ).order_by(EmploymentCertificate.created_at.desc()).all()
    
    return render_template('employee/my_certificates.html', certificates=certificates)


@employee_bp.route('/download-certificate/<int:certificate_id>')
@login_required
def download_certificate(certificate_id):
    """재직증명서 다운로드"""
    certificate = EmploymentCertificate.query.get_or_404(certificate_id)
    
    # 권한 확인
    if certificate.user_id != current_user.id:
        flash('권한이 없습니다.', 'danger')
        return redirect(url_for('employee.my_certificates'))
    
    # 발급완료 상태인지 확인
    if certificate.status != CertificateStatus.ISSUED:
        flash('아직 발급되지 않은 재직증명서입니다.', 'warning')
        return redirect(url_for('employee.my_certificates'))
    
    # 회사 정보 가져오기
    company_info = CompanyInfo.query.first()
    company_name = company_info.name if company_info else '(Company Name)'
    ceo_name = company_info.ceo_name if company_info else '(CEO Name)'
    
    # PDF 생성 (Reportlab 사용)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4  # A4 크기
    
    # 제목
    p.setFont('Helvetica-Bold', 24)
    p.drawCentredString(width/2, height - 3*cm, 'CERTIFICATE OF EMPLOYMENT')
    
    # 인적사항
    p.setFont('Helvetica', 12)
    y_position = height - 6*cm
    
    # 테이블 시작
    p.setFont('Helvetica-Bold', 11)
    p.drawString(3*cm, y_position, 'Name:')
    p.setFont('Helvetica', 11)
    p.drawString(6*cm, y_position, current_user.name)
    y_position -= 1*cm
    
    p.setFont('Helvetica-Bold', 11)
    p.drawString(3*cm, y_position, 'Department:')
    p.setFont('Helvetica', 11)
    p.drawString(6*cm, y_position, f'{company_name} {current_user.department or ""}')
    y_position -= 1*cm
    
    p.setFont('Helvetica-Bold', 11)
    p.drawString(3*cm, y_position, 'Position:')
    p.setFont('Helvetica', 11)
    p.drawString(6*cm, y_position, current_user.position or "")
    y_position -= 1*cm
    
    hire_date_str = ""
    if current_user.hire_date:
        hire_date_str = current_user.hire_date.strftime('%Y-%m-%d')
    else:
        hire_date_str = current_user.created_at.strftime('%Y-%m-%d')
    
    p.setFont('Helvetica-Bold', 11)
    p.drawString(3*cm, y_position, 'Period:')
    p.setFont('Helvetica', 11)
    p.drawString(6*cm, y_position, f'{hire_date_str} ~ Present')
    y_position -= 1*cm
    
    p.setFont('Helvetica-Bold', 11)
    p.drawString(3*cm, y_position, 'Purpose:')
    p.setFont('Helvetica', 11)
    p.drawString(6*cm, y_position, certificate.purpose)
    y_position -= 2*cm
    
    # 증명문
    p.setFont('Helvetica', 12)
    p.drawString(3*cm, y_position, 'This is to certify that the above information is true and correct.')
    y_position -= 3*cm
    
    # 발급일
    today = datetime.now().date()
    p.drawCentredString(width/2, y_position, f'{today.year}-{today.month:02d}-{today.day:02d}')
    y_position -= 2*cm
    
    # 회사명 및 대표자
    p.setFont('Helvetica-Bold', 14)
    p.drawCentredString(width/2, y_position, company_name)
    y_position -= 1*cm
    
    p.setFont('Helvetica', 12)
    p.drawCentredString(width/2, y_position, f'CEO {ceo_name}')
    y_position -= 1.5*cm
    
    # 직인 위치 (원으로 표시)
    p.circle(width/2, y_position, 1*cm)
    p.setFont('Helvetica', 10)
    p.drawCentredString(width/2, y_position, '(Seal)')
    
    # PDF 완성
    p.showPage()
    p.save()
    
    # PDF 응답 생성
    pdf_data = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    
    # 파일명 생성 및 인코딩
    filename = f'certificate_{current_user.name}_{datetime.now().strftime("%Y%m%d")}.pdf'
    encoded_filename = urllib.parse.quote(filename)
    response.headers['Content-Disposition'] = f'attachment; filename={encoded_filename}'
    
    return response


@employee_bp.route('/cancel-certificate/<int:certificate_id>', methods=['POST'])
@login_required
def cancel_certificate(certificate_id):
    """재직증명서 신청 취소"""
    certificate = EmploymentCertificate.query.get_or_404(certificate_id)
    
    # 권한 확인
    if certificate.user_id != current_user.id:
        flash('권한이 없습니다.', 'danger')
        return redirect(url_for('employee.my_certificates'))
    
    # 대기 중인 신청만 취소 가능
    if certificate.status != CertificateStatus.PENDING:
        flash('대기 중인 재직증명서 신청만 취소할 수 있습니다.', 'danger')
        return redirect(url_for('employee.my_certificates'))
    
    # 취소 처리
    db.session.delete(certificate)
    db.session.commit()
    
    flash('재직증명서 신청이 취소되었습니다.', 'success')
    return redirect(url_for('employee.my_certificates'))
