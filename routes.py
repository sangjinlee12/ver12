from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, VacationDays, VacationRequest
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """홈 페이지 - 로그인 상태에 따라 대시보드 또는 로그인 페이지로 리디렉션"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    else:
        return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """대시보드 라우트 - 사용자 역할에 따라 적절한 대시보드로 리디렉션"""
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('employee.dashboard'))

@main_bp.app_errorhandler(404)
def page_not_found(e):
    """404 에러 핸들러"""
    return render_template('error.html', error_code=404, error_message='페이지를 찾을 수 없습니다.'), 404

@main_bp.app_errorhandler(500)
def internal_server_error(e):
    """500 에러 핸들러"""
    return render_template('error.html', error_code=500, error_message='서버 내부 오류가 발생했습니다.'), 500

@main_bp.app_context_processor
def inject_today():
    """템플릿에서 사용할 전역 변수"""
    return {'now': datetime.now()}
