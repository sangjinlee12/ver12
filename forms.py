from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, DateField, IntegerField, HiddenField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError
from datetime import date

class LoginForm(FlaskForm):
    """로그인 폼"""
    username = StringField('아이디', validators=[DataRequired('아이디를 입력하세요.')])
    password = PasswordField('비밀번호', validators=[DataRequired('비밀번호를 입력하세요.')])
    submit = SubmitField('로그인')


class RegisterForm(FlaskForm):
    """회원가입 폼"""
    username = StringField('아이디', validators=[DataRequired('아이디를 입력하세요.'), Length(min=4, max=20, message='아이디는 4-20자 사이여야 합니다.')])
    email = StringField('이메일', validators=[DataRequired('이메일을 입력하세요.'), Email('올바른 이메일 형식이 아닙니다.')])
    name = StringField('이름', validators=[DataRequired('이름을 입력하세요.')])
    password = PasswordField('비밀번호', validators=[
        DataRequired('비밀번호를 입력하세요.'),
        Length(min=6, message='비밀번호는 최소 6자 이상이어야 합니다.')
    ])
    password_confirm = PasswordField('비밀번호 확인', validators=[
        DataRequired('비밀번호 확인을 입력하세요.'),
        EqualTo('password', message='비밀번호가 일치하지 않습니다.')
    ])
    department = SelectField('부서', choices=[
        ('', '선택해주세요'),
        ('공사팀', '공사팀'),
        ('공무팀', '공무팀'),
        ('경리부', '경리부'),
        ('인사팀', '인사팀'),
        ('총무팀', '총무팀'),
        ('영업팀', '영업팀'),
        ('안전팀', '안전팀'),
        ('품질팀', '품질팀')
    ])
    position = SelectField('직급', choices=[
        ('', '선택해주세요'),
        ('대표', '대표'),
        ('이사', '이사'),
        ('소장', '소장'),
        ('부장', '부장'),
        ('차장', '차장'),
        ('과장', '과장'),
        ('대리', '대리'),
        ('사원', '사원')
    ])
    submit = SubmitField('회원가입')


class VacationRequestForm(FlaskForm):
    """휴가 신청 폼"""
    start_date = DateField('시작일', validators=[DataRequired('시작일을 선택하세요.')], format='%Y-%m-%d')
    end_date = DateField('종료일', validators=[DataRequired('종료일을 선택하세요.')], format='%Y-%m-%d')
    type = SelectField('휴가 유형', choices=[
        ('연차', '연차'),
        ('반차(오전)', '반차(오전)'),
        ('반차(오후)', '반차(오후)'),
        ('특별휴가', '특별휴가')
    ], validators=[DataRequired('휴가 유형을 선택하세요.')])
    reason = TextAreaField('휴가 사유')
    days = HiddenField('휴가 일수')  # 자동 계산되는 필드
    submit = SubmitField('휴가 신청')

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError('종료일은 시작일보다 빠를 수 없습니다.')
        if self.start_date.data < date.today():
            raise ValidationError('과거 날짜로는 휴가를 신청할 수 없습니다.')


class VacationApprovalForm(FlaskForm):
    """휴가 승인/반려 폼"""
    request_id = HiddenField('요청 ID')
    status = SelectField('상태', choices=[
        ('승인됨', '승인'),
        ('반려됨', '반려')
    ], validators=[DataRequired('상태를 선택하세요.')])
    comments = TextAreaField('코멘트')
    submit = SubmitField('처리')


class EmployeeVacationDaysForm(FlaskForm):
    """직원 연간 휴가일수 설정 폼"""
    user_id = HiddenField('사용자 ID')
    year = IntegerField('연도', validators=[DataRequired('연도를 입력하세요.')])
    total_days = FloatField('총 휴가일수', validators=[
        DataRequired('휴가일수를 입력하세요.'),
        NumberRange(min=0, message='휴가일수는 0 이상이어야 합니다.')
    ])
    submit = SubmitField('설정')


class HolidayForm(FlaskForm):
    """공휴일 등록 폼"""
    date = DateField('날짜', validators=[DataRequired('날짜를 선택하세요.')], format='%Y-%m-%d')
    name = StringField('공휴일명', validators=[DataRequired('공휴일명을 입력하세요.')])
    submit = SubmitField('등록')


class EmploymentCertificateRequestForm(FlaskForm):
    """재직증명서 신청 폼"""
    purpose = StringField('사용 목적', validators=[
        DataRequired('사용 목적을 입력하세요.'), 
        Length(max=200, message='사용 목적은 200자를 초과할 수 없습니다.')
    ])
    submit = SubmitField('재직증명서 신청')


class CertificateApprovalForm(FlaskForm):
    """재직증명서 승인/반려 폼"""
    certificate_id = HiddenField('요청 ID')
    status = SelectField('상태', choices=[
        ('발급완료', '발급'),
        ('반려됨', '반려')
    ], validators=[DataRequired('상태를 선택하세요.')])
    comments = TextAreaField('코멘트')
    submit = SubmitField('처리')


class CompanyInfoForm(FlaskForm):
    """회사 정보 관리 폼"""
    name = StringField('회사명', validators=[DataRequired('회사명을 입력하세요.')])
    ceo_name = StringField('대표자명', validators=[DataRequired('대표자명을 입력하세요.')])
    registration_number = StringField('사업자등록번호')
    address = StringField('회사 주소')
    phone = StringField('전화번호')
    fax = StringField('팩스번호')
    website = StringField('웹사이트')
    stamp_image = TextAreaField('직인 이미지')
    submit = SubmitField('저장')


class EmployeeHireDateForm(FlaskForm):
    """직원 입사일 설정 폼"""
    user_id = HiddenField('사용자 ID')
    hire_date = DateField('입사일', validators=[DataRequired('입사일을 선택하세요.')], format='%Y-%m-%d')
    submit = SubmitField('저장')
