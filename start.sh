#!/bin/bash

# 데이터베이스 마이그레이션 실행
python -c "from app import app, db; db.create_all()"

# 관리자 계정 생성 (존재하지 않을 경우에만)
python -c "from create_admin import create_admin_account; create_admin_account()"

# 공휴일 데이터 추가 (현재 연도)
python -c "from holidays import add_korean_holidays; from datetime import datetime; add_korean_holidays(datetime.now().year)"

# 회사 정보 설정 (기본 정보)
python -c "from app import app, db; from models import CompanyInfo; with app.app_context(): if not CompanyInfo.query.first(): info = CompanyInfo(name='주식회사 에스에스전력', ceo_name='김대표'); db.session.add(info); db.session.commit()"

# 서버 시작
exec gunicorn --bind 0.0.0.0:$PORT --reuse-port main:app