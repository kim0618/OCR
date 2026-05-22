---
name: OCR 프로젝트 집중
description: 항상 OCR 프로젝트 코드만 봐야 함 - 다른 시스템 탐색 금지
type: feedback
originSessionId: 2c7967a2-b6da-4b5f-8315-a61a41098505
---
OCR 프로젝트 파일만 수정/확인할 것. 서버 프로세스 관리, 시스템 PATH 탐색, bash history 조회 등 OCR 코드와 무관한 작업 하지 말 것.

**Why:** 사용자가 OCR 코드 작업 중인데 Python 경로 탐색, bash history, 시스템 디렉토리 등 관련 없는 곳을 뒤져서 불필요한 작업이 반복됨.

**How to apply:** 작업 범위를 `d:\Free_Vue\OCR\` 하위 파일로 제한. 서버 재시작은 사용자에게 맡기고 명령어만 알려줄 것. 시스템 탐색 도구 호출 자제.
