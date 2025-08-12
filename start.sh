#!/bin/bash

# Railway 배포용 시작 스크립트
echo "🚀 에스에스전력 휴가관리시스템 시작 중..."

# 환경변수 확인
echo "📊 환경변수 확인 중..."
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL이 설정되지 않았습니다."
else
    echo "✅ DATABASE_URL 설정됨"
fi

if [ -z "$SESSION_SECRET" ]; then
    echo "⚠️  SESSION_SECRET이 설정되지 않았습니다."
    export SESSION_SECRET="railway-production-secret-key-$(date +%s)"
    echo "🔑 임시 SESSION_SECRET 생성됨"
else
    echo "✅ SESSION_SECRET 설정됨"
fi

# 필요한 디렉토리 생성
echo "📁 디렉토리 구조 생성 중..."
mkdir -p instance
mkdir -p static/uploads

# 데이터베이스 초기화 (관리자 계정 및 공휴일)
echo "🗄️  데이터베이스 초기 설정 중..."
python3 create_admin.py
python3 add_holidays.py

echo "🎯 성능 최적화된 애플리케이션 시작..."
# 성능 최적화된 Gunicorn 설정
exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 30 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    main:app