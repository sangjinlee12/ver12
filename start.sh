#!/bin/bash

# 데이터베이스 마이그레이션 실행
python -c "from app import app, db; db.create_all()"

# 관리자 계정 생성 (존재하지 않을 경우에만)
python -c "from app import app, db; from models import User, Role, VacationDays; from datetime import datetime; with app.app_context(): existing_admin = User.query.filter_by(username='admin').first(); if not existing_admin: admin = User(username='admin', email='admin@example.com', name='관리자', role=Role.ADMIN, department='경영지원팀', position='관리자', created_at=datetime.now()); admin.password_hash = 'pbkdf2:sha256:260000$LTEWYfcYiIXyUQqR$b5c8dda043bfbd5b3a404ef00bc370a5f00a81c7fc59fb2d0d4f0f3fa36d2be8'; db.session.add(admin); db.session.commit(); vacation_days = VacationDays(user_id=admin.id, year=datetime.now().year, total_days=15, used_days=0); db.session.add(vacation_days); db.session.commit(); print('관리자 계정이 생성되었습니다.')"

# 백업 방법으로 create_admin 스크립트도 실행
python -c "from create_admin import create_admin_account; create_admin_account()"

# 공휴일 데이터 추가 (현재 연도)
python -c "from holidays import add_korean_holidays; from datetime import datetime; add_korean_holidays(datetime.now().year)"

# 회사 정보 설정 (기본 정보)
python -c "from app import app, db; from models import CompanyInfo; with app.app_context(): if not CompanyInfo.query.first(): info = CompanyInfo(name='주식회사 에스에스전력', ceo_name='김대표'); db.session.add(info); db.session.commit()"

# 서버 시작
exec gunicorn --bind 0.0.0.0:$PORT --reuse-port main:app