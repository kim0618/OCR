---
name: 서버 재시작 방법
description: OCR 서버는 .venv uvicorn.exe로 실행 - 직접 실행 가능
type: feedback
originSessionId: 2c7967a2-b6da-4b5f-8315-a61a41098505
---
OCR 서버 시작 명령어:
```
d:\Free_Vue\OCR\ocr-server\.venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 9099 --reload
```

PowerShell에서 백그라운드 실행:
```powershell
Start-Process -FilePath "d:\Free_Vue\OCR\ocr-server\.venv\Scripts\uvicorn.exe" -ArgumentList "main:app","--host","0.0.0.0","--port","9099","--reload" -WorkingDirectory "d:\Free_Vue\OCR\ocr-server" -WindowStyle Hidden
```

**Why:** .venv 안에 uvicorn.exe, python.exe, paddleocr 등 모든 패키지가 설치되어 있음. bash나 WSL의 python3는 Windows 앱 별칭이라 작동 안 함.

**How to apply:** 서버 재시작 필요할 때 위 PowerShell 명령으로 직접 시작 가능.
