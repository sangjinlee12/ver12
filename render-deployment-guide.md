# Render 배포 가이드 - 에스에스전력 휴가관리시스템

## Render 배포 설정 정보

### Build Command
```bash
apt-get update -y && apt-get install -y build-essential fonts-nanum fonts-noto-cjk libpango-1.0-0 libpangoft2-1.0-0 && pip install --upgrade pip && pip install -r requirements-render.txt && python3 create_admin.py && python3 add_holidays.py
```

### Start Command
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 main:app
```

### Publish Directory
```
. (현재 디렉토리 - 루트)
```

## 수동 배포 단계별 설정

### 1. New Web Service 생성
1. [Render](https://render.com)에서 계정 생성/로그인
2. "New" → "Web Service" 클릭
3. GitHub 저장소 연결

### 2. 기본 설정
- **Name**: `sselectric-vacation-system`
- **Region**: `Oregon (US West)`
- **Branch**: `main`
- **Runtime**: `Python 3`

### 3. Build & Deploy 설정
**Build Command**:
```bash
apt-get update -y && apt-get install -y build-essential fonts-nanum fonts-noto-cjk libpango-1.0-0 libpangoft2-1.0-0 && pip install --upgrade pip && pip install -r requirements-render.txt && python3 create_admin.py && python3 add_holidays.py
```

**Start Command**:
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 main:app
```

**Publish Directory**: `. (비워두거나 점 입력)`

### 4. 환경변수 설정
Environment 탭에서 다음 변수들 추가:

#### 필수 환경변수
- `SESSION_SECRET`: `강력한-세션-비밀키-입력`
- `PYTHON_VERSION`: `3.11.0`
- `PYTHONUNBUFFERED`: `true`
- `PYTHONIOENCODING`: `utf-8`

#### PostgreSQL 데이터베이스 (선택사항)
- `DATABASE_URL`: PostgreSQL 연결 URL (없으면 SQLite 사용)

### 5. PostgreSQL 데이터베이스 추가 (선택사항)
1. "New" → "PostgreSQL" 클릭
2. 데이터베이스 생성 후 Internal Database URL 복사
3. Web Service 환경변수에 `DATABASE_URL` 추가

## 자동 배포 설정 (render.yaml 사용)

프로젝트에 이미 `render.yaml` 파일이 포함되어 있습니다:

### 1. GitHub에서 직접 배포
1. Render 대시보드에서 "New" → "Blueprint" 선택
2. GitHub 저장소 연결
3. `render.yaml` 파일이 자동으로 감지됨

### 2. 환경변수만 설정
- `SESSION_SECRET`: 자동 생성됨
- `DATABASE_URL`: PostgreSQL 서비스와 자동 연결

## 시스템 특징

### 자동 초기화
- 관리자 계정 (admin/admin123) 자동 생성
- 2025-2026년 공휴일 자동 등록
- PostgreSQL 우선, SQLite 폴백

### 한글 폰트 지원
- Nanum 폰트 패키지 설치
- PDF 문서 생성 지원
- 한글 텍스트 완전 지원

### 성능 최적화
- Gunicorn WSGI 서버
- 단일 워커 프로세스
- 120초 타임아웃 설정

## 배포 후 확인사항

### 1. 애플리케이션 접속
생성된 Render URL로 접속하여 로그인 페이지 확인

### 2. 관리자 로그인
- 사용자명: `admin`
- 비밀번호: `admin123`

### 3. 기능 테스트
- 직원 등록
- 휴가 신청/승인
- 재직증명서 발급

## 트러블슈팅

### 빌드 실패 시
- Build Command가 정확히 입력되었는지 확인
- 한 줄로 입력 (줄바꿈 없이)

### 실행 오류 시
- Start Command 확인: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 main:app`
- 환경변수 `SESSION_SECRET` 설정 확인

### 데이터베이스 연결 오류
- PostgreSQL 서비스가 생성되었는지 확인
- `DATABASE_URL` 환경변수가 올바른지 확인
- SQLite 폴백 메시지 확인 (정상 동작)

## 비용 정보

### Free Plan 제한
- 월 750시간 실행 (31일 기준 744시간)
- 15분 비활성 후 슬립 모드
- PostgreSQL 90일 후 만료

### Starter Plan ($7/월)
- 무제한 실행 시간
- 슬립 모드 없음
- 영구 PostgreSQL

Render는 무료 플랜으로도 충분히 테스트 및 소규모 운영이 가능합니다.