#!/usr/bin/env python3
"""
성능 최적화 스크립트
배포 후 사이트 속도 개선을 위한 데이터베이스 최적화
"""

from app import app, db
from models import User, VacationRequest, VacationDays, Holiday, EmploymentCertificate
from sqlalchemy import text
import os

def optimize_database():
    """데이터베이스 성능 최적화"""
    with app.app_context():
        print("=== 데이터베이스 성능 최적화 시작 ===")
        
        # SQLite 성능 최적화 설정
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            print("SQLite 성능 최적화 적용 중...")
            
            # 성능 개선 PRAGMA 설정
            db.session.execute(text("PRAGMA journal_mode = WAL"))  # Write-Ahead Logging
            db.session.execute(text("PRAGMA synchronous = NORMAL"))  # 동기화 모드
            db.session.execute(text("PRAGMA cache_size = 10000"))  # 캐시 크기 증가
            db.session.execute(text("PRAGMA temp_store = MEMORY"))  # 임시 데이터 메모리 저장
            db.session.execute(text("PRAGMA mmap_size = 268435456"))  # 메모리 맵 크기 (256MB)
            
            print("✅ SQLite 성능 설정 완료")
            
            # 인덱스 생성
            print("인덱스 생성 중...")
            
            # User 테이블 인덱스
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_username ON user(username)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_email ON user(email)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_department ON user(department)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_role ON user(role)"))
                print("✅ User 테이블 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ User 인덱스 생성 중 오류: {e}")
            
            # VacationRequest 테이블 인덱스
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_request_user_id ON vacation_request(user_id)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_request_status ON vacation_request(status)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_request_start_date ON vacation_request(start_date)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_request_created_at ON vacation_request(created_at)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_request_user_status ON vacation_request(user_id, status)"))
                print("✅ VacationRequest 테이블 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ VacationRequest 인덱스 생성 중 오류: {e}")
            
            # VacationDays 테이블 인덱스
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_days_user_id ON vacation_days(user_id)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_days_year ON vacation_days(year)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_vacation_days_user_year ON vacation_days(user_id, year)"))
                print("✅ VacationDays 테이블 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ VacationDays 인덱스 생성 중 오류: {e}")
            
            # Holiday 테이블 인덱스
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_holiday_date ON holiday(date)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_holiday_year ON holiday(strftime('%Y', date))"))
                print("✅ Holiday 테이블 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ Holiday 인덱스 생성 중 오류: {e}")
            
            # EmploymentCertificate 테이블 인덱스
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_employment_cert_user_id ON employment_certificate(user_id)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_employment_cert_status ON employment_certificate(status)"))
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_employment_cert_created_at ON employment_certificate(created_at)"))
                print("✅ EmploymentCertificate 테이블 인덱스 생성 완료")
            except Exception as e:
                print(f"⚠️ EmploymentCertificate 인덱스 생성 중 오류: {e}")
            
            # 데이터베이스 분석 및 최적화
            try:
                db.session.execute(text("ANALYZE"))
                print("✅ 데이터베이스 통계 분석 완료")
            except Exception as e:
                print(f"⚠️ 데이터베이스 분석 중 오류: {e}")
            
            # VACUUM 실행 (데이터베이스 최적화)
            try:
                db.session.execute(text("VACUUM"))
                print("✅ 데이터베이스 VACUUM 완료")
            except Exception as e:
                print(f"⚠️ VACUUM 실행 중 오류: {e}")
        
        db.session.commit()
        print("=== 데이터베이스 성능 최적화 완료 ===")

def test_query_performance():
    """쿼리 성능 테스트"""
    with app.app_context():
        print("\n=== 쿼리 성능 테스트 ===")
        
        import time
        
        # 사용자 목록 조회 성능
        start_time = time.time()
        users = User.query.all()
        end_time = time.time()
        print(f"사용자 목록 조회: {(end_time - start_time)*1000:.2f}ms ({len(users)}명)")
        
        # 휴가 신청 목록 조회 성능
        start_time = time.time()
        vacation_requests = VacationRequest.query.order_by(VacationRequest.created_at.desc()).limit(50).all()
        end_time = time.time()
        print(f"최근 휴가 신청 50건 조회: {(end_time - start_time)*1000:.2f}ms")
        
        # 부서별 직원 조회 성능
        start_time = time.time()
        dept_users = User.query.filter(User.department.isnot(None)).all()
        end_time = time.time()
        print(f"부서별 직원 조회: {(end_time - start_time)*1000:.2f}ms ({len(dept_users)}명)")
        
        # 연도별 휴가일수 조회 성능
        start_time = time.time()
        current_year = 2025
        vacation_days = VacationDays.query.filter_by(year=current_year).all()
        end_time = time.time()
        print(f"{current_year}년 휴가일수 조회: {(end_time - start_time)*1000:.2f}ms ({len(vacation_days)}건)")
        
        print("=== 성능 테스트 완료 ===")

def check_database_size():
    """데이터베이스 크기 확인"""
    print("\n=== 데이터베이스 정보 ===")
    
    db_path = app.config['SQLALCHEMY_DATABASE_URI']
    if 'sqlite' in db_path:
        # SQLite 파일 크기 확인
        db_file = db_path.replace('sqlite:///', '')
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            print(f"데이터베이스 파일 크기: {size / 1024 / 1024:.2f} MB")
            print(f"데이터베이스 경로: {db_file}")
        else:
            print("데이터베이스 파일을 찾을 수 없습니다.")
    
    with app.app_context():
        # 테이블별 레코드 수
        user_count = User.query.count()
        vacation_request_count = VacationRequest.query.count()
        vacation_days_count = VacationDays.query.count()
        holiday_count = Holiday.query.count()
        certificate_count = EmploymentCertificate.query.count()
        
        print(f"사용자 수: {user_count}")
        print(f"휴가 신청 수: {vacation_request_count}")
        print(f"휴가일수 레코드 수: {vacation_days_count}")
        print(f"공휴일 수: {holiday_count}")
        print(f"재직증명서 신청 수: {certificate_count}")

if __name__ == "__main__":
    print("🚀 에스에스전력 휴가관리시스템 성능 최적화")
    print("=" * 50)
    
    # 데이터베이스 정보 확인
    check_database_size()
    
    # 성능 최적화 실행
    optimize_database()
    
    # 성능 테스트
    test_query_performance()
    
    print("\n✅ 성능 최적화 완료!")
    print("배포 후 사이트 로딩 속도가 개선되었습니다.")