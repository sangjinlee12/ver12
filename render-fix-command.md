# Render 배포 오류 해결 - apt-get 문제

## 문제점
Render 빌드 환경에서는 `apt-get` 명령어 사용이 제한됨
읽기 전용 파일 시스템으로 인해 시스템 패키지 설치 불가

## 해결책: 간단한 Build Command 사용

### 수정된 Build Command (복사해서 사용):
```bash
pip install --upgrade pip && pip install -r requirements-render.txt && python3 create_admin.py && python3 add_holidays.py
```

## Render Settings에서 수정 방법:

1. Render 대시보드에서 서비스 선택
2. **Settings** 탭 클릭
3. **Build & Deploy** 섹션에서 **Build Command** 수정
4. 위의 간단한 명령어로 교체
5. **Save Changes** 클릭
6. **Manual Deploy** → **Deploy latest commit** 클릭

## 주의사항:
- 한글 폰트가 설치되지 않아 PDF 생성시 한글이 깨질 수 있음
- 하지만 웹 애플리케이션 자체는 정상 작동
- 필요시 PDF 생성 기능은 weasyprint 대신 reportlab 사용