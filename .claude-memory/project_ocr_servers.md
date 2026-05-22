---
name: OCR 프로젝트 서버 실행 방법
description: MySuit OCR 프로젝트의 프론트엔드/백엔드 서버 실행 명령어 및 경로
type: project
originSessionId: 50789bc8-8abf-4eae-8236-c819a58a8c3d
---
FastAPI 백엔드 서버는 d:/Free_Vue/OCR/ocr-server/ 안의 .venv를 사용해야 한다. 시스템 Python이 아니라 반드시 .venv/Scripts/python.exe로 실행할 것.

백엔드 실행:
```
cd d:/Free_Vue/OCR/ocr-server && .venv/Scripts/python.exe main.py > server.log 2>&1 &
```
- 포트: 9099

프론트엔드 실행:
```
cd d:/Free_Vue/OCR/mysuit-ocr && npm run dev > dev.log 2>&1 &
```
- 포트: 8089

**Why:** 사용자가 명시적으로 물어보지 말고 알아서 찾아서 실행하라고 요청함. .venv가 ocr-server 디렉토리 안에 있음.

**How to apply:** 서버 실행 요청 시 패키지 설치 여부 묻지 말고 바로 .venv로 실행. 서버 확인은 server.log로.
