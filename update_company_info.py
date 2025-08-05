#!/usr/bin/env python3
"""
회사 정보를 업데이트하는 스크립트
"""

import sqlite3
import os

def update_company_info():
    # 데이터베이스 파일 경로
    db_path = 'instance/vacation_permanent.db'
    
    if not os.path.exists(db_path):
        print(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    try:
        # SQLite 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 기존 회사 정보 확인
        cursor.execute("SELECT * FROM company_info")
        rows = cursor.fetchall()
        print("기존 회사 정보:")
        for row in rows:
            print(row)
        
        # 회사 정보 업데이트
        cursor.execute("""
            UPDATE company_info 
            SET name = '에스에스전력 인사관리시스템',
                address = '강원도 원주시 하초구길60'
            WHERE id = 1
        """)
        
        # 회사 정보가 없는 경우 새로 생성
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO company_info (name, address, ceo_name, registration_number, phone, fax, website, stamp_image)
                VALUES ('에스에스전력 인사관리시스템', '강원도 원주시 하초구길60', '', '', '', '', '', '')
            """)
            print("새로운 회사 정보를 생성했습니다.")
        else:
            print("회사 정보를 업데이트했습니다.")
        
        # 변경사항 저장
        conn.commit()
        
        # 업데이트된 정보 확인
        cursor.execute("SELECT * FROM company_info")
        rows = cursor.fetchall()
        print("\n업데이트된 회사 정보:")
        for row in rows:
            print(row)
            
    except sqlite3.Error as e:
        print(f"데이터베이스 오류: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_company_info()