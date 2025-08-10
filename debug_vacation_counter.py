#!/usr/bin/env python3
"""휴가 카운터 문제 디버깅 스크립트"""

import os
import sys
from datetime import datetime

# Flask 앱 컨텍스트 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models import User, VacationDays, VacationRequest, VacationStatus

def debug_vacation_counter():
    """휴가 카운터 문제를 디버깅합니다."""
    
    with app.app_context():
        print("=== 휴가 카운터 디버깅 ===")
        
        # test_emp1 사용자 정보 확인
        user = User.query.filter_by(username='test_emp1').first()
        if not user:
            print("❌ test_emp1 사용자를 찾을 수 없습니다.")
            return
        
        print(f"👤 사용자: {user.name} ({user.username})")
        print(f"📧 이메일: {user.email}")
        print(f"🏢 부서: {user.department} {user.position}")
        
        # 휴가 일수 데이터 확인
        vacation_days_records = VacationDays.query.filter_by(user_id=user.id).all()
        print(f"\n📊 휴가 일수 레코드: {len(vacation_days_records)}개")
        
        for vd in vacation_days_records:
            print(f"  - {vd.year}년: 총 {vd.total_days}일, 사용 {vd.used_days}일, 남은 {vd.remaining_days()}일")
        
        # 휴가 신청 내역 확인
        vacation_requests = VacationRequest.query.filter_by(user_id=user.id).all()
        print(f"\n📋 휴가 신청 내역: {len(vacation_requests)}개")
        
        for vr in vacation_requests:
            print(f"  - {vr.start_date} ~ {vr.end_date}: {vr.days}일 ({vr.type}) - {vr.status}")
        
        # 2025년 데이터 특별 확인
        vacation_2025 = VacationDays.query.filter_by(user_id=user.id, year=2025).first()
        if vacation_2025:
            print(f"\n📅 2025년 휴가 현황:")
            print(f"  총 휴가: {vacation_2025.total_days}일")
            print(f"  사용: {vacation_2025.used_days}일")
            print(f"  남은: {vacation_2025.remaining_days()}일")
        else:
            print(f"\n❌ 2025년 휴가 데이터가 없습니다.")
            
            # 2025년 휴가 데이터 생성
            new_vacation_2025 = VacationDays(
                user_id=user.id,
                year=2025,
                total_days=15,
                used_days=0
            )
            db.session.add(new_vacation_2025)
            db.session.commit()
            print("✓ 2025년 휴가 데이터 생성 완료")
        
        # 승인된 휴가의 합계 계산
        approved_vacations = VacationRequest.query.filter_by(
            user_id=user.id, 
            status=VacationStatus.APPROVED
        ).all()
        
        total_used_days = sum(vr.days for vr in approved_vacations)
        print(f"\n📈 승인된 휴가 총합: {total_used_days}일")
        
        # 휴가 일수 동기화
        if vacation_2025:
            if vacation_2025.used_days != total_used_days:
                print(f"⚠️  불일치 발견: DB에는 {vacation_2025.used_days}일, 실제는 {total_used_days}일")
                vacation_2025.used_days = total_used_days
                db.session.commit()
                print("✓ 휴가 일수 동기화 완료")
            else:
                print("✅ 휴가 일수가 정확합니다.")

def fix_all_users_vacation_counter():
    """모든 사용자의 휴가 카운터를 수정합니다."""
    
    with app.app_context():
        print("\n=== 전체 사용자 휴가 카운터 수정 ===")
        
        users = User.query.all()
        
        for user in users:
            if user.role == 'employee':  # 직원만 처리
                # 2025년 승인된 휴가 총합 계산
                approved_vacations_2025 = VacationRequest.query.filter(
                    VacationRequest.user_id == user.id,
                    VacationRequest.status == VacationStatus.APPROVED,
                    db.extract('year', VacationRequest.start_date) == 2025
                ).all()
                
                total_used_2025 = sum(vr.days for vr in approved_vacations_2025)
                
                # 2025년 휴가 데이터 확인/생성
                vacation_2025 = VacationDays.query.filter_by(user_id=user.id, year=2025).first()
                if not vacation_2025:
                    vacation_2025 = VacationDays(
                        user_id=user.id,
                        year=2025,
                        total_days=15,
                        used_days=total_used_2025
                    )
                    db.session.add(vacation_2025)
                    print(f"✓ {user.name}: 2025년 휴가 데이터 생성 (사용: {total_used_2025}일)")
                else:
                    if vacation_2025.used_days != total_used_2025:
                        vacation_2025.used_days = total_used_2025
                        print(f"✓ {user.name}: 휴가 카운터 수정 ({vacation_2025.used_days} → {total_used_2025}일)")
        
        db.session.commit()
        print("📊 모든 사용자 휴가 카운터 동기화 완료")

if __name__ == '__main__':
    debug_vacation_counter()
    fix_all_users_vacation_counter()