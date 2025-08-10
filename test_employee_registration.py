#!/usr/bin/env python3
"""직원 등록 기능 테스트 스크립트"""

import os
import sys
from datetime import datetime, date

# Flask 앱 컨텍스트 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models import User, VacationDays, Role

def test_employee_registration():
    """직원 등록 기능을 테스트합니다."""
    
    with app.app_context():
        print("=== 직원 등록 기능 테스트 ===")
        
        # 테스트용 직원 데이터
        test_employee = {
            'username': 'new_emp_test',
            'email': 'newtest@sspower.com',
            'name': '신입직원',
            'password': 'test123456',
            'resident_id_first': '950815',
            'resident_id_last_digit': '1',
            'department': '기술팀',
            'position': '사원',
            'hire_date': date(2025, 8, 10)
        }
        
        # 기존 동일 사용자가 있는지 확인
        existing_user = User.query.filter_by(username=test_employee['username']).first()
        if existing_user:
            print(f"기존 테스트 직원 삭제: {existing_user.name}")
            # 관련 휴가 데이터도 삭제
            vacation_days = VacationDays.query.filter_by(user_id=existing_user.id).all()
            for vd in vacation_days:
                db.session.delete(vd)
            db.session.delete(existing_user)
            db.session.commit()
        
        try:
            # 새 직원 생성
            new_employee = User(
                username=test_employee['username'],
                email=test_employee['email'],
                name=test_employee['name'],
                resident_id_first=test_employee['resident_id_first'],
                resident_id_last_digit=test_employee['resident_id_last_digit'],
                department=test_employee['department'],
                position=test_employee['position'],
                hire_date=test_employee['hire_date'],
                role=Role.EMPLOYEE
            )
            new_employee.set_password(test_employee['password'])
            db.session.add(new_employee)
            db.session.flush()  # ID를 얻기 위해 flush
            
            print(f"✓ 직원 생성: {new_employee.name} (ID: {new_employee.id})")
            
            # 현재 연도와 내년 휴가 일수 설정
            current_year = datetime.now().year
            for year in [current_year, current_year + 1]:
                vacation_days = VacationDays(
                    user_id=new_employee.id,
                    year=year,
                    total_days=15,  # 기본 15일
                    used_days=0
                )
                db.session.add(vacation_days)
                print(f"✓ {year}년 휴가 일수 설정: {vacation_days.total_days}일")
            
            db.session.commit()
            print(f"🎉 {new_employee.name}님이 성공적으로 등록되었습니다!")
            
            # 등록 결과 확인
            print("\n=== 등록 결과 확인 ===")
            registered_user = User.query.filter_by(username=test_employee['username']).first()
            print(f"👤 이름: {registered_user.name}")
            print(f"📧 이메일: {registered_user.email}")
            print(f"🏢 부서/직급: {registered_user.department} {registered_user.position}")
            print(f"📅 입사일: {registered_user.hire_date}")
            print(f"🔐 로그인 테스트: ", "성공" if registered_user.check_password(test_employee['password']) else "실패")
            
            # 휴가 일수 확인
            vacation_records = VacationDays.query.filter_by(user_id=registered_user.id).all()
            print(f"📊 휴가 일수 레코드: {len(vacation_records)}개")
            for vd in vacation_records:
                print(f"  - {vd.year}년: 총 {vd.total_days}일, 사용 {vd.used_days}일, 남은 {vd.remaining_days()}일")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 직원 등록 실패: {str(e)}")
            return False

def show_all_employees():
    """모든 직원 목록을 출력합니다."""
    
    with app.app_context():
        print("\n=== 전체 직원 목록 ===")
        employees = User.query.filter_by(role=Role.EMPLOYEE).all()
        
        print(f"총 {len(employees)}명의 직원이 등록되어 있습니다.")
        print("-" * 80)
        print(f"{'이름':<10} {'아이디':<15} {'부서':<10} {'직급':<8} {'입사일':<12}")
        print("-" * 80)
        
        for emp in employees:
            hire_date_str = emp.hire_date.strftime('%Y-%m-%d') if emp.hire_date else '미설정'
            print(f"{emp.name:<10} {emp.username:<15} {emp.department or '미설정':<10} {emp.position or '미설정':<8} {hire_date_str:<12}")

if __name__ == '__main__':
    # 직원 등록 테스트
    if test_employee_registration():
        show_all_employees()
        print("\n✅ 직원 등록 기능 테스트 완료!")
        print("웹에서 테스트하기:")
        print("1. 관리자로 로그인 (admin / admin123)")
        print("2. 직원 관리 → 직원 등록 버튼 클릭")
        print("3. 새로운 직원 정보 입력 및 등록")
    else:
        print("\n❌ 직원 등록 기능 테스트 실패")