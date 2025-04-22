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
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT

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


def create_docx_certificate(certificate, current_user, company_info):
    """워드 파일로 재직증명서 생성"""
    company_name = company_info.name if company_info else '주식회사 에스에스전력'
    ceo_name = company_info.ceo_name if company_info else '대표이사'
    
    today = datetime.now().date()
    today_str = f"{today.year}년 {today.month}월 {today.day}일"
    
    hire_date_str = ""
    if current_user.hire_date:
        hire_date_str = current_user.hire_date.strftime('20%y년 %m월 %d일')
    else:
        hire_date_str = current_user.created_at.strftime('20%y년 %m월 %d일')
    
    # 워드 문서 생성
    doc = docx.Document()
    
    # 페이지 여백 설정 (단위: cm)
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)
    
    # 스타일 설정
    style = doc.styles['Normal']
    style.font.name = '맑은 고딕'
    style.font.size = Pt(12)
    
    # 제목 추가 - 가운데 정렬, 큰 글씨
    title = doc.add_heading('', level=0)
    title_run = title.add_run('재 직 증 명 서')
    title_run.font.name = '맑은 고딕'
    title_run.font.size = Pt(18)
    title_run.font.bold = True
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # 여백 추가
    doc.add_paragraph()
    
    # 표 생성 - 샘플 양식과 동일하게 4x3 표로 구성
    table = doc.add_table(rows=4, cols=4)
    table.style = 'Table Grid'
    
    # 표 너비 설정
    table.autofit = False
    table.width = Cm(16)  # A4 너비는 약 21cm, 여백 제외하면 약 16cm
    
    # 1행: 성명, 주민등록번호
    row = table.rows[0]
    row.cells[0].text = '성 명'
    row.cells[0].width = Cm(2)
    row.cells[1].text = current_user.name
    row.cells[1].width = Cm(5)
    row.cells[1].paragraphs[0].runs[0].font.color.rgb = docx.shared.RGBColor(255, 0, 0)
    row.cells[1].paragraphs[0].runs[0].font.bold = True
    row.cells[2].text = '주민등록번호'
    row.cells[2].width = Cm(3)
    row.cells[3].text = '9xxxxx-1xxxxxx'
    row.cells[3].width = Cm(6)
    row.cells[3].paragraphs[0].runs[0].font.color.rgb = docx.shared.RGBColor(255, 0, 0)
    row.cells[3].paragraphs[0].runs[0].font.bold = True
    
    # 2행: 주소 (병합 셀)
    row = table.rows[1]
    row.cells[0].text = '주 소'
    row.cells[0].width = Cm(2)
    # 주소 셀 병합 (2, 3, 4번 셀)
    cell = row.cells[1]
    cell.merge(row.cells[2])
    cell.merge(row.cells[3])
    cell.text = ""  # 주소는 비워둠
    
    # 3행: 소속, 직위, 팀장
    row = table.rows[2]
    row.cells[0].text = '소 속'
    row.cells[0].width = Cm(2)
    row.cells[1].text = company_info.name if company_info and company_info.name else current_user.department or '영업팀'
    row.cells[1].width = Cm(5)
    row.cells[1].paragraphs[0].runs[0].font.color.rgb = docx.shared.RGBColor(255, 0, 0)
    row.cells[1].paragraphs[0].runs[0].font.bold = True
    row.cells[2].text = '직 위'
    row.cells[2].width = Cm(3)
    row.cells[3].text = current_user.position or '팀장'
    row.cells[3].width = Cm(6)
    row.cells[3].paragraphs[0].runs[0].font.color.rgb = docx.shared.RGBColor(255, 0, 0)
    row.cells[3].paragraphs[0].runs[0].font.bold = True
    
    # 4행: 기간 (병합 셀)
    row = table.rows[3]
    row.cells[0].text = '기 간'
    row.cells[0].width = Cm(2)
    # 기간 셀 병합 (2, 3, 4번 셀)
    cell = row.cells[1]
    cell.merge(row.cells[2])
    cell.merge(row.cells[3])
    duration_text = f"{hire_date_str}~현재"
    cell.text = duration_text
    cell.paragraphs[0].runs[0].font.color.rgb = docx.shared.RGBColor(255, 0, 0)
    cell.paragraphs[0].runs[0].font.bold = True
    
    # 모든 셀 가운데 정렬(수평, 수직 모두)과 여백 설정
    for row in table.rows:
        # 행 높이 설정 - 더 넓은 여백을 위해
        row.height = Cm(1.2)
        row.height_rule = 2  # WD_ROW_HEIGHT.EXACTLY = 2
        
        for cell in row.cells:
            # 셀 수직 정렬 - 중앙
            cell.vertical_alignment = 1  # WD_ALIGN_VERTICAL.CENTER = 1
            
            for paragraph in cell.paragraphs:
                # 단락 수평 정렬 - 중앙
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                # 단락 간격 설정
                paragraph.space_before = Pt(0)
                paragraph.space_after = Pt(0)
                
                for run in paragraph.runs:
                    run.font.name = '맑은 고딕'
    
    # 여백 추가
    doc.add_paragraph()
    doc.add_paragraph()
    
    # 본문 텍스트
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('상기와 같이 재직 중임을 증명함')
    run.font.name = '맑은 고딕'
    
    # 날짜 부분을 위한 여백
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph()
    
    # 용도
    usage_p = doc.add_paragraph()
    usage_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    usage_p.paragraph_format.left_indent = Cm(2)
    usage_run = usage_p.add_run(f"용도 : {certificate.purpose}")
    usage_run.font.name = '맑은 고딕'
    usage_run.font.color.rgb = docx.shared.RGBColor(255, 0, 0)
    
    # 여백 추가
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph()
    
    # 회사명
    company_p = doc.add_paragraph()
    company_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    company_name_run = company_p.add_run(f"회사명 :    {company_name}")
    company_name_run.font.name = '맑은 고딕'
    
    # 대표자 및 도장 이미지
    ceo_p = doc.add_paragraph()
    ceo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ceo_run = ceo_p.add_run(f"대표이사 :    {ceo_name}       ")
    ceo_run.font.name = '맑은 고딕'
    
    # 도장 이미지 삽입
    if company_info and company_info.stamp_image:
        try:
            # 도장 이미지가 있으면 사용
            stamp_data = base64.b64decode(company_info.stamp_image.split(',')[-1])
            stamp_io = io.BytesIO(stamp_data)
            ceo_p.add_run().add_picture(stamp_io, width=Cm(1.5), height=Cm(1.5))
        except Exception as e:
            print(f"도장 이미지 삽입 오류: {str(e)}")
            # 오류 시 (인) 텍스트로 대체
            ceo_p.add_run("(인)").font.name = '맑은 고딕'
    else:
        # 도장 이미지가 없으면 (인) 텍스트 표시
        ceo_p.add_run("(인)").font.name = '맑은 고딕'
    
    # 문서를 메모리에 저장
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
    
    # 파일 형식 결정 (기본: PDF)
    file_format = request.args.get('format', 'pdf').lower()
    
    try:
        if file_format == 'docx':
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
        else:
            # 로컬 폰트 파일 읽기
            font_path = './static/fonts/NanumGothic.ttf'
            font_data = ""
            try:
                with open(font_path, 'rb') as f:
                    font_data = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"폰트 로드 오류: {str(e)}")
                font_data = ""
            
            # PDF 생성
            today = datetime.now().date()
            today_str = f"{today.year}년 {today.month}월 {today.day}일"
            
            hire_date_str = ""
            if current_user.hire_date:
                hire_date_str = current_user.hire_date.strftime('20%y년 %m월 %d일')
            else:
                hire_date_str = current_user.created_at.strftime('20%y년 %m월 %d일')
            
            # 직접 HTML 문자열 구성
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>재직증명서</title>
                <style>
                    @font-face {{
                        font-family: 'NanumGothicCustom';
                        src: url('data:application/font-woff;charset=utf-8;base64,{font_data}') format('truetype');
                        font-weight: normal;
                        font-style: normal;
                    }}
                    body {{
                        font-family: 'NanumGothicCustom', Arial, sans-serif;
                        margin: 40px;
                        padding: 0;
                        line-height: 1.5;
                    }}
                    h1 {{
                        text-align: center;
                        font-size: 24px;
                        margin-bottom: 40px;
                        letter-spacing: 5px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 30px;
                    }}
                    table, th, td {{
                        border: 1px solid black;
                    }}
                    th {{
                        width: 15%;
                        padding: 15px 8px;
                        text-align: center;
                        font-weight: normal;
                        height: 25px;
                        line-height: 25px;
                    }}
                    td {{
                        padding: 15px 8px;
                        text-align: center;
                        height: 25px;
                        line-height: 25px;
                    }}
                    .text-black {{
                        color: #000000;
                        font-weight: bold;
                    }}
                    .center-text {{
                        text-align: center;
                        margin: 30px 0;
                    }}
                    .purpose {{
                        text-align: left;
                        margin-top: 100px;
                        margin-left: 80px;
                    }}
                    .company-info {{
                        text-align: center;
                        margin-top: 80px;
                    }}
                </style>
            </head>
            <body>
                <h1>재직증명서</h1>
                
                <table>
                    <tr>
                        <th>성 명</th>
                        <td style="width: 25%"><span class="text-black">{current_user.name}</span></td>
                        <th>주민등록번호</th>
                        <td><span class="text-black">9xxxxx-1xxxxxx</span></td>
                    </tr>
                    <tr>
                        <th>주 소</th>
                        <td colspan="3"></td>
                    </tr>
                    <tr>
                        <th>소 속</th>
                        <td><span class="text-black">{current_user.department or '영업팀'}</span></td>
                        <th>직 위</th>
                        <td><span class="text-black">{current_user.position or '팀장'}</span></td>
                    </tr>
                    <tr>
                        <th>기 간</th>
                        <td colspan="3"><span class="text-black">{hire_date_str.replace('년', '년 ').replace('월', '월 ').replace('일', '일')}~현재</span></td>
                    </tr>
                </table>
                
                <p class="center-text">상기와 같이 재직 중임을 증명함</p>
                
                <p class="purpose">용도 : <span class="text-black">{certificate.purpose}</span></p>
                
                <div class="company-info">
                    <p>회사명 : {company_name}</p>
                    <p>대표이사 : {ceo_name} <img src="data:image/png;base64,{company_info.stamp_image.split(',')[-1] if company_info and company_info.stamp_image else ''}" style="width: 50px; height: 50px; vertical-align: middle;" onerror="this.style.display='none';this.nextSibling.style.display='inline';" /><span style="display:none;">(인)</span></p>
                </div>
            </body>
            </html>
            """
            
            # HTML을 PDF로 변환 (WeasyPrint 사용)
            pdf = HTML(string=html).write_pdf()
            
            # PDF 응답 생성
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            
            # 파일명 생성 및 인코딩
            filename = f'재직증명서_{current_user.name}_{datetime.now().strftime("%Y%m%d")}.pdf'
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
