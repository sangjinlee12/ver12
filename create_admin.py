from app import app, db
from models import User, Role, VacationDays
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin_account():
    """관리자 계정 생성"""
    with app.app_context():
        # 이미 admin 계정이 있는지 확인
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("'admin' 계정이 이미 존재합니다.")
            return
        
        # 관리자 계정 생성
        admin = User(
            username='admin',
            email='admin@example.com',
            name='관리자',
            role=Role.ADMIN,
            department='경영지원팀',
            position='관리자',
            created_at=datetime.now()
        )
        
        # 비밀번호 설정 (기본 비밀번호: admin123)
        admin.set_password('admin123')
        
        # DB에 추가
        db.session.add(admin)
        db.session.commit()
        
        # 휴가일수 설정 (관리자용 15일)
        vacation_days = VacationDays(
            user_id=admin.id,
            year=datetime.now().year,
            total_days=15,
            used_days=0
        )
        
        db.session.add(vacation_days)
        db.session.commit()
        
        print(f"관리자 계정 생성 완료:")
        print(f"- 사용자명: admin")
        print(f"- 비밀번호: admin123")
        print(f"- 역할: {Role.ADMIN}")
        print(f"- 연도: {datetime.now().year}")
        print(f"- 총 휴가일수: 15일")
        print("\n이 계정으로, 로그인 후 다른 사용자의 휴가를 관리할 수 있습니다.")

if __name__ == "__main__":
    create_admin_account()