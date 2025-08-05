import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# Flask 앱 생성
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # url_for가 https를 생성하도록 필요

# 데이터베이스 설정
# PostgreSQL 우선, 연결 실패 시 영구 SQLite 폴백
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # PostgreSQL URL 변환
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # PostgreSQL 연결 테스트
    if "postgresql://" in database_url:
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            result = urlparse(database_url)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            conn.close()
            print("✅ PostgreSQL 데이터베이스 연결 성공")
        except Exception as e:
            print(f"❌ PostgreSQL 연결 실패: {e}")
            print("📁 영구 SQLite 데이터베이스로 폴백합니다")
            # 영구 저장을 위해 절대 경로 사용
            import os
            db_dir = os.path.abspath("instance")
            os.makedirs(db_dir, exist_ok=True)
            database_url = f"sqlite:///{db_dir}/vacation_permanent.db"
else:
    # 개발환경: 영구 SQLite 사용
    print("🔧 개발 환경: 영구 SQLite 데이터베이스 사용")
    import os
    db_dir = os.path.abspath("instance")
    os.makedirs(db_dir, exist_ok=True)
    database_url = f"sqlite:///{db_dir}/vacation_permanent.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
print(f"🗄️  데이터베이스: {database_url}")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 데이터베이스 초기화
db.init_app(app)

# 로그인 매니저 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '이 페이지에 접근하려면 로그인이 필요합니다.'
login_manager.login_message_category = 'warning'

with app.app_context():
    # 모델 임포트
    import models  # noqa: F401
    
    # 데이터베이스 테이블 생성
    db.create_all()
    
    # 라우트 등록
    from auth import auth_bp
    from admin import admin_bp
    from employee import employee_bp
    from routes import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(employee_bp, url_prefix='/employee')
    app.register_blueprint(main_bp)
    
    # User 로더 설정
    from models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
