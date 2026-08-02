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

**비정형 거래명세서(invoice_statement) free parser — env 불요 (2026-05-29 검증):** 4F 패치로 `main.py`에서
`USE_INVOICE_STATEMENT_FREE` 게이트가 **제거됨**. free path 진입 조건은 이제 `not region_list and
_is_unstructured_template`(요청 form `templateMode=unstructured` 또는 `isUnstructuredTemplate=Y`)뿐.
**env 없이** 비정형 1.jpg가 used=True / source=invoice_statement_free / 28행으로 정상 동작함을 0단계
close-out에서 확인(envPresentInProcess 둘 다 false인 fresh 서버 + 재기동 9099 양쪽 일치). 남은 env는
`USE_INVOICE_STATEMENT_FREE_CONTROLLED_SUCCESS`(기본 OFF, 켜면 가짜 CONTROLLED_TEST_ITEM 1행 반환 — 테스트용,
운영/확인 시 절대 켜지 말 것).

**Stale 서버 함정(중요):** free parser 코드(`extractors/invoice_statement_free.py`)를 고친 뒤 9099가
이전 코드로 떠 있으면 옛 결과가 나온다. 실제로 4K(소계 footer 필터) 적용 후에도 기존 9099는 **29행 + 소계 row
잔존**이었고, **재기동(.venv uvicorn, full restart)** 후에야 28행/소계 없음이 됨. `--reload`가 extractors
하위나 시스템 python 기동 시 변경을 못 잡을 수 있으니, free parser 변경 검증 전엔 9099를 full restart 할 것.
