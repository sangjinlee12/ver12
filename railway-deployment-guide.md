# Railway 배포 가이드 - 에스에스전력 휴가관리시스템

## 배포 준비사항

### 1. 필요한 파일들
- `railway.json` - Railway 배포 설정
- `requirements-railway.txt` - Python 패키지 의존성
- `Procfile` - 애플리케이션 시작 명령어
- `start.sh` - 초기화 스크립트
- `nixpacks.toml` - Nixpacks 빌드 설정

### 2. 환경변수 설정
Railway 대시보드에서 다음 환경변수들을 설정하세요:

#### 필수 환경변수
```
DATABASE_URL=postgresql://username:password@host:port/database
SESSION_SECRET=your-secure-session-secret-key
```

#### 선택적 환경변수
```
FLASK_ENV=production
PYTHONPATH=/app
```

## Railway 배포 단계

### 1. GitHub Repository 연결
1. Railway 대시보드에서 "New Project" 클릭
2. "Deploy from GitHub repo" 선택
3. 프로젝트 저장소 선택

### 2. PostgreSQL 데이터베이스 추가
1. Railway 프로젝트에서 "Add Service" 클릭
2. "Database" → "PostgreSQL" 선택
3. 데이터베이스가 생성되면 `DATABASE_URL` 환경변수가 자동으로 설정됨

### 3. 환경변수 설정
1. Railway 대시보드에서 Variables 탭 이동
2. `SESSION_SECRET` 환경변수 추가:
   ```
   SESSION_SECRET=super-secure-secret-key-for-production
   ```

### 4. 도메인 설정
1. Settings 탭에서 "Generate Domain" 클릭
2. 커스텀 도메인 설정 (선택사항)

## 배포 후 확인사항

### 1. 애플리케이션 상태 확인
- Railway 로그에서 시작 메시지 확인
- 데이터베이스 연결 상태 확인
- 관리자 계정 생성 확인

### 2. 관리자 계정 로그인
- 사용자명: `admin`
- 비밀번호: `admin123`

### 3. 기능 테스트
- 직원 등록 기능
- 휴가 신청/승인 기능
- 재직증명서 발급 기능

## 배포 설정 파일들

### railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "./start.sh",
    "healthcheckPath": "/",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Procfile
```
web: ./start.sh
```

## 트러블슈팅

### 데이터베이스 연결 오류
- `DATABASE_URL` 환경변수가 올바르게 설정되었는지 확인
- PostgreSQL 서비스가 실행 중인지 확인

### 세션 오류
- `SESSION_SECRET` 환경변수가 설정되었는지 확인
- 충분히 복잡한 시크릿 키를 사용

### 빌드 오류
- `requirements-railway.txt`의 패키지 버전 확인
- Python 버전 호환성 확인

## 유지보수

### 로그 모니터링
Railway 대시보드의 Logs 탭에서 애플리케이션 로그 확인

### 데이터베이스 백업
Railway PostgreSQL 서비스의 자동 백업 기능 활용

### 업데이트 배포
GitHub에 코드 푸시 시 자동으로 재배포됨