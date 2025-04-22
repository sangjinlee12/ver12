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
# Render에서는 postgres:// URL을 postgresql://로 변환해야 합니다
database_url = os.environ.get("DATABASE_URL", "sqlite:///vacation.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
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
