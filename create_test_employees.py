#!/usr/bin/env python3
"""테스트용 직원 등록 스크립트"""

import os
import sys
from datetime import datetime, date
from werkzeug.security import generate_password_hash

# Flask 앱 컨텍스트 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models import User, Role, VacationDays

def create_test_employees():
    """테스트용 직원들을 생성합니다."""
    
    with app.app_context():
        # 기존 테스트 직원들 삭제 (중복 방지)
        existing_test_users = User.query.filter(User.username.like('test_%')).all()
        for user in existing_test_users:
            # 관련 휴가 데이터도 삭제
            vacation_days = VacationDays.query.filter_by(user_id=user.id).all()
            for vd in vacation_days:
                db.session.delete(vd)
            db.session.delete(user)
        
        # 테스트 직원 데이터
        test_employees = [
            {
                'username': 'test_emp1',
                'email': 'test1@sspower.com',
                'name': '김테스트',
                'password': 'test123',
                'resident_id_first': '920315',
                'resident_id_last_digit': '1',
                'department': '공사팀',
                'position': '사원',
                'hire_date': date(2024, 1, 15)
            },
            {
                'username': 'test_emp2',
                'email': 'test2@sspower.com',
                'name': '이테스트',
                'password': 'test123',
                'resident_id_first': '910520',
                'resident_id_last_digit': '2',
                'department': '영업팀',
                'position': '대리',
                'hire_date': date(2023, 3, 10)
            },
            {
                'username': 'test_emp3',
                'email': 'test3@sspower.com',
                'name': '박테스트',
                'password': 'test123',
                'resident_id_first': '880712',
                'resident_id_last_digit': '1',
                'department': '경리부',
                'position': '과장',
                'hire_date': date(2022, 5, 20)
            },
            {
                'username': 'test_emp4',
                'email': 'test4@sspower.com',
                'name': '최테스트',
                'password': 'test123',
                'resident_id_first': '851225',
                'resident_id_last_digit': '2',
                'department': '안전팀',
                'position': '차장',
                'hire_date': date(2021, 8, 1)
            },
            {
                'username': 'test_emp5',
                'email': 'test5@sspower.com',
                'name': '정테스트',
                'password': 'test123',
                'resident_id_first': '930810',
                'resident_id_last_digit': '1',
                'department': '인사팀',
                'position': '주임',
                'hire_date': date(2024, 6, 1)
            }
        ]
        
        print("테스트 직원 등록을 시작합니다...")
        
        for emp_data in test_employees:
            # 새 직원 생성
            new_employee = User(
                username=emp_data['username'],
                email=emp_data['email'],
                name=emp_data['name'],
                resident_id_first=emp_data['resident_id_first'],
                resident_id_last_digit=emp_data['resident_id_last_digit'],
                department=emp_data['department'],
                position=emp_data['position'],
                role=Role.EMPLOYEE,
                hire_date=emp_data['hire_date']
            )
            new_employee.set_password(emp_data['password'])
            db.session.add(new_employee)
            db.session.flush()  # ID를 얻기 위해 flush
            
            # 2024년과 2025년 휴가 일수 설정
            for year in [2024, 2025]:
                vacation_days = VacationDays(
                    user_id=new_employee.id,
                    year=year,
                    total_days=15,  # 기본 15일
                    used_days=0
                )
                db.session.add(vacation_days)
            
            print(f"✓ {emp_data['name']} ({emp_data['username']}) - {emp_data['department']} {emp_data['position']}")
        
        # 변경사항 저장
        db.session.commit()
        print(f"\n총 {len(test_employees)}명의 테스트 직원이 성공적으로 등록되었습니다!")
        print("\n로그인 정보:")
        print("아이디: test_emp1, test_emp2, test_emp3, test_emp4, test_emp5")
        print("비밀번호: test123 (모든 테스트 계정 공통)")
        print("\n이제 관리자가 이 직원들에게 휴가를 등록할 수 있습니다.")

if __name__ == '__main__':
    create_test_employees()