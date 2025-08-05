# Render 배포 오류 수정

## 문제점
Build Command에서 `requirements-railway.txt` 파일을 찾지 못함
Render에서는 `requirements-render.txt` 파일을 사용해야 함

## 수정된 Build Command (복사해서 사용):

```bash
apt-get update -y && apt-get install -y build-essential fonts-nanum fonts-noto-cjk libpango-1.0-0 libpangoft2-1.0-0 && pip install --upgrade pip && pip install -r requirements-render.txt && python3 create_admin.py && python3 add_holidays.py
```

## Render Settings에서 수정 방법:

1. Render 대시보드에서 서비스 선택
2. "Settings" 탭 클릭
3. "Build & Deploy" 섹션에서 "Build Command" 수정
4. 위의 수정된 명령어로 교체
5. "Save Changes" 클릭
6. "Manual Deploy" → "Deploy latest commit" 클릭하여 재배포

## 또는 간단한 Build Command:

만약 위 명령어가 너무 길다면, 더 간단한 버전:

```bash
pip install -r requirements-render.txt && python3 create_admin.py && python3 add_holidays.py
```

한글 PDF 생성이 필요 없다면 폰트 설치 부분을 제거할 수 있습니다.