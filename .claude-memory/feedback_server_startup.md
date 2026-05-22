---
name: 서버 실행 시 .venv 자동 사용
description: OCR 서버 실행 시 질문 없이 .venv를 찾아서 바로 실행해야 함
type: feedback
originSessionId: 50789bc8-8abf-4eae-8236-c819a58a8c3d
---
서버 실행 요청 시 패키지가 없다고 묻거나 pip install을 제안하지 말 것. 먼저 프로젝트 내 .venv를 찾아서 그걸로 바로 실행할 것.

**Why:** 사용자가 "물어보지 말고 알아서 찾아서 진행하라"고 명시적으로 요청함. .venv가 ocr-server 디렉토리 안에 이미 존재함.

**How to apply:** 서버 실행 전 find로 pyvenv.cfg 또는 .venv 탐색 → 해당 Python으로 실행. 시스템 Python 먼저 쓰지 말 것.
