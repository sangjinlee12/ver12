#!/usr/bin/env python3
"""데이터베이스 백업 및 복구 스크립트"""

import os
import shutil
import sqlite3
from datetime import datetime
import sys

# Flask 앱 컨텍스트 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app, db

def backup_database():
    """현재 데이터베이스를 백업합니다."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 현재 데이터베이스 파일 경로
    db_path = "instance/vacation_permanent.db"
    backup_path = f"instance/backup_vacation_{timestamp}.db"
    
    if os.path.exists(db_path):
        try:
            shutil.copy2(db_path, backup_path)
            print(f"✓ 데이터베이스 백업 완료: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ 백업 실패: {e}")
            return None
    else:
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return None

def verify_database_integrity():
    """데이터베이스 무결성을 검사합니다."""
    db_path = "instance/vacation_permanent.db"
    
    try:
        # SQLite 연결 테스트
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        required_tables = ['users', 'vacation_days', 'vacation_request', 'holidays', 'company_info']
        existing_tables = [table[0] for table in tables]
        
        print("=== 데이터베이스 무결성 검사 ===")
        print(f"📊 데이터베이스 경로: {db_path}")
        print(f"📋 기존 테이블: {existing_tables}")
        
        # 데이터 개수 확인
        for table in required_tables:
            if table in existing_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"📈 {table}: {count}개 레코드")
            else:
                print(f"⚠️  {table}: 테이블 없음")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 오류: {e}")
        return False

def optimize_database():
    """데이터베이스를 최적화합니다."""
    db_path = "instance/vacation_permanent.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # VACUUM으로 데이터베이스 최적화
        cursor.execute("VACUUM;")
        
        # 인덱스 재구성
        cursor.execute("REINDEX;")
        
        conn.commit()
        conn.close()
        
        print("✓ 데이터베이스 최적화 완료")
        return True
        
    except Exception as e:
        print(f"❌ 최적화 실패: {e}")
        return False

def setup_persistent_storage():
    """영구 저장을 위한 설정을 확인하고 개선합니다."""
    
    print("=== 영구 저장 설정 확인 ===")
    
    # instance 디렉토리 생성 및 권한 설정
    instance_dir = "instance"
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir, mode=0o755)
        print(f"✓ {instance_dir} 디렉토리 생성")
    
    # 데이터베이스 파일 권한 확인
    db_path = "instance/vacation_permanent.db"
    if os.path.exists(db_path):
        # 파일 권한을 읽기/쓰기로 설정
        os.chmod(db_path, 0o644)
        print(f"✓ 데이터베이스 파일 권한 설정: {db_path}")
    
    # 백업 생성
    backup_path = backup_database()
    if backup_path:
        print(f"✓ 백업 파일 생성: {backup_path}")
    
    # 무결성 검사
    if verify_database_integrity():
        print("✓ 데이터베이스 무결성 확인")
    
    # 최적화
    if optimize_database():
        print("✓ 데이터베이스 최적화 완료")
    
    # 환경 변수 확인
    print("\n=== 환경 설정 확인 ===")
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"📊 DATABASE_URL: {database_url}")
    else:
        print("⚠️  DATABASE_URL 환경 변수가 설정되지 않음")
    
    print("\n=== 권장사항 ===")
    print("1. 정기적으로 데이터베이스 백업을 수행하세요")
    print("2. 배포 전에 데이터베이스 무결성을 확인하세요")
    print("3. 중요한 데이터는 외부 저장소에도 백업하세요")
    
    return True

if __name__ == '__main__':
    setup_persistent_storage()