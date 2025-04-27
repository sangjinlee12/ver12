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
from weasyprint import HTML
from PIL import Image, ImageDraw, ImageFont
import base64
import docx
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
# qrcode 모듈은 더 이상 사용하지 않습니다
import PIL
from PIL import Image, ImageDraw, ImageFont

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


def text_to_image(text, font_size=24, width=None, text_color=(0, 0, 0), bg_color=(255, 255, 255)):
    """텍스트를 이미지로 변환하는 함수"""
    # 기본 폰트 (Arial)
    try:
        # 시스템에 설치된 폰트 사용
        font = ImageFont.truetype("Arial", font_size)
    except:
        # 기본 폰트 사용
        font = ImageFont.load_default()
    
    # 텍스트 크기 계산
    test_img = Image.new('RGB', (1, 1))
    test_draw = ImageDraw.Draw(test_img)
    text_width, text_height = test_draw.textsize(text, font=font) if hasattr(test_draw, 'textsize') else font.getbbox(text)[2:4]
    
    # 이미지 크기 설정
    if width:
        img_width = width
    else:
        img_width = text_width + 20  # 여백 추가
    img_height = text_height + 20  # 여백 추가
    
    # 이미지 생성
    img = Image.new('RGB', (img_width, img_height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # 텍스트 추가 (가운데 정렬)
    x = (img_width - text_width) // 2
    y = (img_height - text_height) // 2
    draw.text((x, y), text, font=font, fill=text_color)
    
    # 이미지를 바이트로 변환
    img_byte = io.BytesIO()
    img.save(img_byte, format='PNG')
    img_byte.seek(0)
    
    return img_byte.getvalue()

def create_qrcode(data, size=200):
    """QR 코드 생성 함수 (간단한 격자무늬 이미지로 대체)"""
    # 이미지 크기와 색상 설정
    img_size = size
    background_color = (255, 255, 255)  # 흰색
    qrcode_color = (0, 0, 0)  # 검은색
    
    # 새 이미지 생성
    img = Image.new('RGB', (img_size, img_size), color=background_color)
    draw = ImageDraw.Draw(img)
    
    # 격자 크기 계산
    grid_size = img_size // 25
    
    # 데이터를 이용한 패턴 생성
    data_hash = sum([ord(c) for c in data])
    
    # 격자 그리기
    for x in range(0, img_size, grid_size):
        for y in range(0, img_size, grid_size):
            # 데이터 기반 패턴 생성
            if ((x // grid_size) * 5 + (y // grid_size) + data_hash) % 3 == 0:
                draw.rectangle(
                    (x, y, x + grid_size - 1, y + grid_size - 1),
                    fill=qrcode_color
                )
    
    # 테두리 추가
    draw.rectangle((0, 0, img_size-1, img_size-1), outline=qrcode_color, width=2)
    
    # QR 코드 영역 표시 (코너 사각형)
    corner_size = grid_size * 3
    
    # 왼쪽 상단
    draw.rectangle((0, 0, corner_size, corner_size), fill=qrcode_color)
    draw.rectangle((grid_size, grid_size, corner_size-grid_size, corner_size-grid_size), fill=background_color)
    
    # 오른쪽 상단
    draw.rectangle((img_size-corner_size-1, 0, img_size-1, corner_size), fill=qrcode_color)
    draw.rectangle((img_size-corner_size+grid_size-1, grid_size, img_size-grid_size-1, corner_size-grid_size), fill=background_color)
    
    # 왼쪽 하단
    draw.rectangle((0, img_size-corner_size-1, corner_size, img_size-1), fill=qrcode_color)
    draw.rectangle((grid_size, img_size-corner_size+grid_size-1, corner_size-grid_size, img_size-grid_size-1), fill=background_color)
    
    # 이미지를 바이트로 변환
    img_byte = io.BytesIO()
    img.save(img_byte, format='PNG')
    img_byte.seek(0)
    
    return img_byte

def create_barcode(data, width=400, height=100):
    """바코드 생성 함수 (간단한 이미지 생성 방식으로 대체)"""
    # 간단한 이미지 생성 (바코드 모양의 이미지)
    img_width = width
    img_height = height
    background_color = (255, 255, 255)  # 흰색
    barcode_color = (0, 0, 0)  # 검은색
    
    # 새 이미지 생성
    img = Image.new('RGB', (img_width, img_height), color=background_color)
    draw = ImageDraw.Draw(img)
    
    # 바코드 패턴을 직접 그리기 (임의의 간격으로 세로선 그리기)
    bar_width = 3  # 바코드 선 너비
    max_bars = 30  # 최대 바 개수
    position = 20  # 시작 위치
    
    # 데이터를 이용해 일관된 패턴 생성
    data_hash = sum([ord(c) for c in data])
    
    for i in range(max_bars):
        # 데이터 기반 간격 계산 (일관성 유지)
        offset = (i * 17 + data_hash) % 13 + 5
        if i % 3 != 0:  # 2/3의 바만 그림
            # 세로선 그리기
            draw.rectangle(
                (position, 10, position + bar_width, img_height - 30),
                fill=barcode_color
            )
        position += bar_width + offset
    
    # 바코드 번호 추가
    try:
        font = ImageFont.truetype("Arial", 12)
    except:
        font = ImageFont.load_default()
    
    # 바코드 번호 텍스트 추가
    text_width = draw.textbbox((0, 0), data, font=font)[2]
    text_x = (img_width - text_width) // 2
    draw.text((text_x, img_height - 25), data, font=font, fill=barcode_color)
    
    # 이미지를 바이트로 변환
    img_byte = io.BytesIO()
    img.save(img_byte, format='PNG')
    img_byte.seek(0)
    
    return img_byte


def create_docx_certificate(certificate, current_user, company_info):
    """워드 파일로 재직증명서 생성 - 이미지와 정확히 동일한 형식"""
    company_name = company_info.name if company_info else '주식회사 에스에스전력'
    ceo_name = company_info.ceo_name if company_info else '김세인'
    
    today = datetime.now().date()
    today_str = f"{today.year}년 {today.month}월 {today.day}일"
    
    hire_date_str = ""
    if current_user.hire_date:
        hire_date_str = current_user.hire_date.strftime('%Y년 %m월 %d일')
    else:
        hire_date_str = "2024년 12월 20일"  # 기본값 설정
    
    # 워드 문서 생성
    doc = docx.Document()
    
    # A4 사이즈 설정 (단위: cm)
    sections = doc.sections
    for section in sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        # 여백을 이미지와 유사하게 설정
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
    
    # 스타일 설정
    style = doc.styles['Normal']
    style.font.name = '맑은 고딕'
    style.font.size = Pt(10)
    
    # 발급일 추가 (이미지와 동일하게 오른쪽 정렬)
    issue_date_p = doc.add_paragraph()
    issue_date_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    issue_date_run = issue_date_p.add_run(f'발급일: {today_str}')
    issue_date_run.font.name = '맑은 고딕'
    issue_date_run.font.size = Pt(10)
    
    # 제목 추가 - 중앙 정렬
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title.add_run('재직증명서')
    title_run.font.name = '맑은 고딕'
    title_run.font.size = Pt(14)
    title_run.font.bold = True
    title.space_after = Pt(12)  # 제목 아래 약간의 여백
    
    # 가로선 추가 (테이블 방식으로 구현)
    line_table = doc.add_table(rows=1, cols=1)
    line_table.style = 'Table Grid'
    line_table.autofit = False
    line_table.width = Cm(16)
    line_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 테이블 높이를 아주 작게 설정해서 선으로 보이게 함
    line_table.rows[0].height = Cm(0.05)
    line_table.rows[0].height_rule = 2  # WD_ROW_HEIGHT.EXACTLY = 2
    # 여백 추가
    p_after_line = doc.add_paragraph()
    p_after_line.space_after = Pt(12)
    
    # 표 생성
    table = doc.add_table(rows=4, cols=4)
    table.style = 'Table Grid'
    table.autofit = False
    table.width = Cm(16)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # 표 내용 채우기 (이미지와 정확히 동일하게)
    # 1행: 성명, 주민등록번호
    row = table.rows[0]
    row.cells[0].text = '성명'
    row.cells[1].text = current_user.name if current_user.name else '김영희'  # 기본값
    row.cells[2].text = '주민등록번호'
    row.cells[3].text = '******-*******'
    
    # 2행: 소속, 직위
    row = table.rows[1]
    row.cells[0].text = '소속'
    row.cells[1].text = current_user.department or '개발팀'
    row.cells[2].text = '직위'
    row.cells[3].text = current_user.position or '과장'
    
    # 3행: 재직기간
    row = table.rows[2]
    row.cells[0].text = '재직기간'
    cell = row.cells[1]
    cell.merge(row.cells[2])
    cell.merge(row.cells[3])
    cell.text = f"{hire_date_str} ~ 현재"
    
    # 4행: 용도
    row = table.rows[3]
    row.cells[0].text = '용도'
    cell = row.cells[1]
    cell.merge(row.cells[2])
    cell.merge(row.cells[3])
    cell.text = certificate.purpose if certificate and certificate.purpose else '개인'
    
    # 표 셀 스타일 설정
    for row in table.rows:
        row.height = Cm(0.9)  # 행 높이 설정
        row.height_rule = 2  # WD_ROW_HEIGHT.EXACTLY = 2
        
        for cell in row.cells:
            cell._element.tcPr.append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
            
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.space_before = Pt(0)
                paragraph.space_after = Pt(0)
                
                for run in paragraph.runs:
                    run.font.name = '맑은 고딕'
                    run.font.size = Pt(10)
    
    # 증명 문구
    p_confirm = doc.add_paragraph()
    p_confirm.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_confirm.space_before = Pt(15)
    confirm_run = p_confirm.add_run("상기인은 위와 같이 재직하고 있음을 증명합니다.")
    confirm_run.font.name = '맑은 고딕'
    confirm_run.font.size = Pt(11)
    
    # 날짜
    date_p = doc.add_paragraph()
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_p.space_before = Pt(20)
    date_run = date_p.add_run(today_str)
    date_run.font.name = '맑은 고딕'
    date_run.font.size = Pt(11)
    
    # 중앙 여백 (이미지처럼 더 많은 간격 추가)
    for i in range(6):
        empty_p = doc.add_paragraph()
        empty_p.space_before = Pt(10)
        empty_p.space_after = Pt(0)
    
    # 회사명
    company_p = doc.add_paragraph()
    company_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    company_p.space_before = Pt(0)
    company_p.space_after = Pt(0)
    company_run = company_p.add_run(company_name)
    company_run.font.name = '맑은 고딕'
    company_run.font.size = Pt(12)
    company_run.font.bold = True
    
    # 대표이사 및 직인 생략
    ceo_p = doc.add_paragraph()
    ceo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ceo_p.space_before = Pt(2)
    ceo_p.space_after = Pt(2)
    ceo_run = ceo_p.add_run(f"대표이사 {ceo_name}")
    ceo_run.font.name = '맑은 고딕'
    ceo_run.font.size = Pt(11)
    ceo_run.font.bold = True
    
    ceo_p.add_run(" ")  # 간격 추가
    
    seal_run = ceo_p.add_run("(직인 생략)")
    seal_run.font.name = '맑은 고딕'
    seal_run.font.size = Pt(8)
    
    # 문서 확인번호 생성 (이미지와 동일한 형식)
    doc_verification_code = f"CERT-2-2-{datetime.now().strftime('%Y%m%d')}"
    
    # 바코드 생성 및 삽입
    try:
        barcode_img_io = create_barcode(doc_verification_code, width=400, height=40)
        
        barcode_p = doc.add_paragraph()
        barcode_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        barcode_p.space_before = Pt(6)
        barcode_p.space_after = Pt(6)
        
        barcode_run = barcode_p.add_run()
        barcode_run.add_picture(barcode_img_io, width=Cm(12))
    except Exception as e:
        print(f"바코드 생성 오류: {str(e)}")
    
    # 문서확인번호
    code_p = doc.add_paragraph()
    code_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    code_p.space_before = Pt(0)
    code_p.space_after = Pt(0)
    code_run = code_p.add_run(f"문서확인번호: {doc_verification_code}")
    code_run.font.name = '맑은 고딕'
    code_run.font.size = Pt(8)
    
    # 문서확인 사이트
    guide_p = doc.add_paragraph()
    guide_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    guide_p.space_before = Pt(0)
    guide_p.space_after = Pt(0)
    guide_run = guide_p.add_run(f"문서확인 사이트: {company_info.website if company_info and company_info.website else 'https://ss-electric.co.kr'}")
    guide_run.font.name = '맑은 고딕'
    guide_run.font.size = Pt(8)
    
    # 문서 저장
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer


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
    company_name = company_info.name if company_info else '주식회사 에스에스전력'
    ceo_name = company_info.ceo_name if company_info else '대표이사'
    
    try:
        # 워드 문서 생성
        buffer = create_docx_certificate(certificate, current_user, company_info)
        
        # 응답 생성
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        # 파일명 생성 및 인코딩
        filename = f'재직증명서_{current_user.name}_{datetime.now().strftime("%Y%m%d")}.docx'
        encoded_filename = urllib.parse.quote(filename)
        response.headers['Content-Disposition'] = f'attachment; filename={encoded_filename}'
        
        return response
    except Exception as e:
        # 오류 발생 시 로그 출력 및 처리
        print(f"파일 생성 오류: {str(e)}")
        flash('파일 생성 중 오류가 발생했습니다.', 'danger')
        return redirect(url_for('employee.my_certificates'))


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
