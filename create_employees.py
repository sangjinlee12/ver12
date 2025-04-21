from app import app, db
from models import User, Role, VacationDays
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_employee_accounts():
    """여러 부서의 직원 계정 생성"""
    with app.app_context():
        # 직원 데이터 - (이름, 아이디, 이메일, 부서, 직급, 휴가일수)
        employees = [
            ("김영희", "younghee", "younghee@example.com", "개발팀", "선임연구원", 15),
            ("이철수", "chulsoo", "chulsoo@example.com", "개발팀", "주임연구원", 12),
            ("박민지", "minji", "minji@example.com", "마케팅팀", "팀장", 20),
            ("정준호", "junho", "junho@example.com", "인사팀", "과장", 17),
            ("송지원", "jiwon", "jiwon@example.com", "재무팀", "대리", 15),
            ("강현우", "hyunwoo", "hyunwoo@example.com", "영업팀", "사원", 10),
            ("황미영", "miyoung", "miyoung@example.com", "고객지원팀", "주임", 13),
            ("조민수", "minsoo", "minsoo@example.com", "개발팀", "사원", 10),
            ("윤서연", "seoyeon", "seoyeon@example.com", "디자인팀", "선임디자이너", 15),
            ("한지훈", "jihoon", "jihoon@example.com", "영업팀", "차장", 18)
        ]
        
        created_count = 0
        current_year = datetime.now().year
        
        # 직원 계정 생성
        for name, username, email, department, position, vacation_days in employees:
            # 이미 존재하는 아이디인지 확인
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"'{username}' 계정이 이미 존재합니다.")
                continue
            
            # 새 직원 계정 생성
            employee = User(
                username=username,
                email=email,
                name=name,
                role=Role.EMPLOYEE,
                department=department,
                position=position,
                created_at=datetime.now()
            )
            
            # 비밀번호 설정 (기본 비밀번호: password123)
            employee.set_password('password123')
            
            # DB에 추가
            db.session.add(employee)
            db.session.commit()
            
            # 휴가일수 설정
            vacation_days_entry = VacationDays(
                user_id=employee.id,
                year=current_year,
                total_days=vacation_days,
                used_days=0
            )
            
            db.session.add(vacation_days_entry)
            db.session.commit()
            
            created_count += 1
            print(f"직원 계정 생성: {name} ({username}) - {department} {position}")
        
        print(f"\n총 {created_count}개의 직원 계정이 생성되었습니다.")
        print("모든 직원의 초기 비밀번호는 'password123' 입니다.")

if __name__ == "__main__":
    create_employee_accounts()