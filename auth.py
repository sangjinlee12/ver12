from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Role, VacationDays
from forms import LoginForm, RegisterForm
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
    
    return render_template('login.html', form=form)

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
            return render_template('register.html', form=form)
        
        # 이메일 중복 확인
        if User.query.filter_by(email=form.email.data).first():
            flash('이미 사용 중인 이메일입니다.', 'danger')
            return render_template('register.html', form=form)
        
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
    
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """로그아웃"""
    logout_user()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login'))
