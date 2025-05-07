from app import app, db
from models import User, Role
from datetime import datetime

def reset_user_passwords():
    """모든 사용자의 비밀번호를 재설정합니다."""
    with app.app_context():
        # 모든 사용자 조회
        users = User.query.all()
        
        print(f"총 {len(users)}명의 사용자 비밀번호를 재설정합니다.")
        
        for user in users:
            # 원래 역할과 계정에 맞게 비밀번호 설정
            if user.username == 'admin':
                password = 'admin123'
            else:
                password = 'password123'  # 일반 직원은 모두 동일하게
            
            # 비밀번호 재설정 (pbkdf2:sha256 방식으로)
            user.set_password(password)
            print(f"사용자 '{user.username}' 비밀번호 재설정 완료")
        
        # 변경사항 저장
        db.session.commit()
        print("모든 사용자 비밀번호 재설정 완료")

if __name__ == "__main__":
    reset_user_passwords()