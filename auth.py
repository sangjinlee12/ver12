from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Role, VacationDays
from forms import LoginForm, RegisterForm, FindIdForm, FindPasswordForm, ResetPasswordForm
import secrets
import string
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    # 이미 로그인한 사용자는 대시보드로 리디렉션
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('로그인되었습니다.', 'success')
            
            # 요청한 페이지로 리디렉션, 없으면 대시보드로
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        
        flash('아이디 또는 비밀번호가 잘못되었습니다.', 'danger')
    
    return render_template('login_gov.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """회원가입 페이지"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # 아이디 중복 확인
        if User.query.filter_by(username=form.username.data).first():
            flash('이미 사용 중인 아이디입니다.', 'danger')
            return render_template('register_gov.html', form=form)
        
        # 이메일 중복 확인
        if User.query.filter_by(email=form.email.data).first():
            flash('이미 사용 중인 이메일입니다.', 'danger')
            return render_template('register_gov.html', form=form)
        
        # 첫 번째 사용자는 관리자로 설정
        role = Role.EMPLOYEE
        if User.query.count() == 0:
            role = Role.ADMIN
        
        # 사용자 생성
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            name=form.name.data,
            resident_id_first=form.resident_id_first.data,
            resident_id_last_digit=form.resident_id_last_digit.data,
            department=form.department.data,
            position=form.position.data,
            role=role
        )
        new_user.set_password(form.password.data)
        
        db.session.add(new_user)
        db.session.commit()
        
        # 현재 연도의 휴가 일수 생성
        current_year = datetime.now().year
        vacation_days = VacationDays(
            user_id=new_user.id,
            year=current_year,
            total_days=15,  # 기본 15일
            used_days=0
        )
        db.session.add(vacation_days)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register_gov.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """로그아웃"""
    logout_user()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login'))


def generate_temp_password(length=8):
    """임시 비밀번호 생성"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


@auth_bp.route('/find-id', methods=['GET', 'POST'])
def find_id():
    """아이디 찾기"""
    form = FindIdForm()
    found_username = None
    
    if form.validate_on_submit():
        user = User.query.filter_by(
            name=form.name.data, 
            email=form.email.data
        ).first()
        
        if user:
            found_username = user.username
            flash(f'회원님의 아이디는 "{found_username}" 입니다.', 'success')
        else:
            flash('입력하신 정보와 일치하는 계정을 찾을 수 없습니다.', 'danger')
    
    return render_template('auth/find_id.html', form=form, found_username=found_username)


@auth_bp.route('/find-password', methods=['GET', 'POST'])
def find_password():
    """비밀번호 찾기 (임시 비밀번호 발급)"""
    form = FindPasswordForm()
    temp_password = None
    
    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data,
            email=form.email.data
        ).first()
        
        if user:
            # 임시 비밀번호 생성 및 설정
            temp_password = generate_temp_password()
            user.set_password(temp_password)
            db.session.commit()
            
            flash(f'임시 비밀번호가 발급되었습니다: {temp_password}', 'success')
            flash('보안을 위해 로그인 후 반드시 비밀번호를 변경해주세요.', 'warning')
        else:
            flash('입력하신 정보와 일치하는 계정을 찾을 수 없습니다.', 'danger')
    
    return render_template('auth/find_password.html', form=form, temp_password=temp_password)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@login_required
def reset_password():
    """비밀번호 재설정"""
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('비밀번호가 성공적으로 변경되었습니다.', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/reset_password.html', form=form)
