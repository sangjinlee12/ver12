from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# 사용자 역할 정의
class Role:
    EMPLOYEE = 'employee'
    ADMIN = 'admin'

# 휴가 상태 정의
class VacationStatus:
    PENDING = '대기중'
    APPROVED = '승인됨'
    REJECTED = '반려됨'

class CompanyInfo(db.Model):
    """회사 정보 모델"""
    __tablename__ = 'company_info'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 회사명
    ceo_name = db.Column(db.String(50), nullable=False)  # 대표자명
    registration_number = db.Column(db.String(30))  # 사업자등록번호
    address = db.Column(db.String(200))  # 회사 주소
    phone = db.Column(db.String(20))  # 전화번호
    fax = db.Column(db.String(20))  # 팩스번호
    website = db.Column(db.String(100))  # 웹사이트
    stamp_image = db.Column(db.Text)  # 직인 이미지 (base64)
    
    def __repr__(self):
        return f'<CompanyInfo {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 사용자 실명
    role = db.Column(db.String(20), nullable=False, default=Role.EMPLOYEE)  # 역할 (직원/관리자)
    department = db.Column(db.String(50))  # 부서
    position = db.Column(db.String(50))  # 직급
    hire_date = db.Column(db.Date)  # 입사일
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 관계 설정
    vacation_days = db.relationship('VacationDays', backref='user', uselist=False)
    vacation_requests = db.relationship('VacationRequest', backref='user', foreign_keys='VacationRequest.user_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == Role.ADMIN

    def __repr__(self):
        return f'<User {self.username}>'


class VacationDays(db.Model):
    __tablename__ = 'vacation_days'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # 연도
    total_days = db.Column(db.Integer, nullable=False, default=15)  # 총 휴가 일수
    used_days = db.Column(db.Float, nullable=False, default=0)  # 사용한 휴가 일수 (반차 지원을 위해 Float 타입)
    
    def remaining_days(self):
        """남은 휴가 일수 계산"""
        return self.total_days - self.used_days
    
    def __repr__(self):
        return f'<VacationDays {self.user_id} {self.year}>'


class VacationRequest(db.Model):
    __tablename__ = 'vacation_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)  # 휴가 시작일
    end_date = db.Column(db.Date, nullable=False)  # 휴가 종료일
    days = db.Column(db.Float, nullable=False)  # 휴가 일수 (반차 지원을 위해 Float 타입)
    reason = db.Column(db.Text)  # 휴가 사유
    status = db.Column(db.String(20), nullable=False, default=VacationStatus.PENDING)  # 휴가 상태
    type = db.Column(db.String(20), nullable=False, default='연차')  # 휴가 종류 (연차, 반차, 특별휴가 등)
    
    # 관리자 승인/반려 정보
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # 승인/반려한 관리자
    approval_date = db.Column(db.DateTime)  # 승인/반려 날짜
    comments = db.Column(db.Text)  # 관리자 코멘트
    
    created_at = db.Column(db.DateTime, default=datetime.now)  # 신청 날짜
    
    # 관계 설정
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    def __repr__(self):
        return f'<VacationRequest {self.id} {self.user_id} {self.status}>'


# 재직증명서 상태 정의
class CertificateStatus:
    PENDING = '대기중'
    ISSUED = '발급완료'
    REJECTED = '반려됨'


class EmploymentCertificate(db.Model):
    """재직증명서 모델"""
    __tablename__ = 'employment_certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    purpose = db.Column(db.String(200), nullable=False)  # 사용 목적
    issued_date = db.Column(db.Date)  # 발급일
    status = db.Column(db.String(20), nullable=False, default=CertificateStatus.PENDING)  # 상태
    
    # 관리자 승인/반려 정보
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # 승인/반려한 관리자
    approval_date = db.Column(db.DateTime)  # 승인/반려 날짜
    comments = db.Column(db.Text)  # 관리자 코멘트
    
    created_at = db.Column(db.DateTime, default=datetime.now)  # 신청 날짜
    
    # 관계 설정
    user = db.relationship('User', foreign_keys=[user_id], backref='certificates')
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    def __repr__(self):
        return f'<EmploymentCertificate {self.id} {self.user_id} {self.status}>'


class Holiday(db.Model):
    """공휴일 관리 모델"""
    __tablename__ = 'holidays'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<Holiday {self.date} {self.name}>'
