---
name: ocr-workspace-hygiene
description: OCR 폴더 정리 후 유지 규약. 새 파일/로그/백업/산출물을 어디에 두어야 하는지. 2026-05-21 대규모 정리 후 확정.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c63e45b4-2887-4282-8ac0-40829e956791
---

OCR 프로젝트(d:/Free_Vue/OCR/)는 2026-05-21에 대규모 정리를 거쳐 깨끗한 상태로 확정됨. 향후 작업에서 이 상태를 유지하기 위한 위치 규약.

**현재 깨끗한 루트 구조:**
- `OCR/` 루트: `.gitignore`, `CLAUDE.md` 만
- `ocr-server/` 루트: 운영 9개 (amount_extractor.py, document_classifier.py, main.py, preprocess.py, preprocessing_policy.py, signal_lists.py, requirements.txt, verify_t28k.py, verify_t28k_live.py)
- `mysuit-ocr/` 루트: Next.js config + README 만 (백업 28개는 `mysuit-ocr/backup/` 으로 이동 완료)

**파일 종류별 위치 규약:**
- 백업 파일 (`*_YYYYMMDD_*_before_*`): 해당 프로젝트의 `backup/` 폴더 (`ocr-server/backup/`, `mysuit-ocr/backup/`). 루트나 `src/`, `extractors/` 같은 운영 코드 폴더에 직접 두지 말 것 — Next.js / Python 빌드/컴파일에 영향.
- 실행 로그 (`*.log`): `ocr-server/logs/` 폴더. 루트나 다른 폴더에 두지 말 것.
- **Codex 실행 산출물 (`codex_*.log`, `codex_*.out`, `codex_*.err`, `codex_*.json`)**: 반드시 `ocr-server/logs/codex_<작업명>.{out,err}.log` 형식으로 저장. Codex 호출 시 프롬프트에 출력 경로를 명시하거나, uvicorn redirect 를 `logs/` 절대경로로 지정할 것. `ocr-server/` 루트에 직접 떨구지 말 것. `.gitignore` 의 `codex_*.{log,out,err,json}` 룰로 git 추적은 자동 차단됨.
- 임시 작업 파일 (`tmp_*`): 작업 직후 즉시 삭제. 보존 필요하면 `/tmp/` 폴더.
- 일회성 검증 산출물 (`verify_*_codex.py`, `runall_diff_*.json`, `test-before/after.json`, `ocr_*_result.json`, `d4_*_result.json`): 작업 완료 즉시 삭제.
- 작업 보고서/분석 문서 (`.md`, `.json` 분석 결과): `OCR/docs/` 단일 위치 권장 (mysuit-ocr/docs/ 는 향후 통합 권고 상태).
- Chrome 테스트 프로필 (`chrome-test-profile-*`): 절대 git 추적 금지. OCR 폴더 안에 두지 말 것.
- archive 성격 (옛 일회성 스크립트 모음): `<project>/backup/scripts_archive/`.

**Why:**
2026-05-21 대규모 정리에서 다음 문제들이 한꺼번에 발견됨.
- Chrome 프로필 4세트(4,720 파일)가 public GitHub repo에 노출 — 비밀번호 DB / 쿠키 / 인증 토큰 / 방문 기록 포함
- 루트에 일회성 산출물 200+ 산재 (`ocr_*.json`, `d4_*.json`, `tmp_*`, `verify_*_codex.py`)
- `mysuit-ocr/src/` 안 백업 28개가 Next.js build 에 컴파일 부담
- `ocr-server/scripts/` 52개 일회성 검증 스크립트 dead code
- `ocr-server/` 루트 128개 .log 산재
- 정리 후 git ls-files 5,765 → 약 900 으로 감소.

**How to apply:**
- 새 파일/산출물 생성 시 위 위치 규약에 맞춰 즉시 적절한 폴더로.
- 작업 마무리 시 `git status` 로 루트가 어수선해지지 않았는지 확인.
- `.gitignore` 룰을 위반하는 새 산출물 패턴이 발견되면 즉시 보강.
- `backup/` 폴더는 그대로 보존 (CLAUDE.md 백업 룰 정신과 일관).
- Codex 프롬프트 작성 시 백업 위치, 로그 위치(`logs/`), 산출물 삭제 정책 명시.
- 새 검증 스크립트 작성 시 작업 완료 즉시 정리 또는 `backup/scripts_archive/` 로 이동.

관련: [[project-ocr-servers]] (서버 실행 위치), [[feedback-focus-ocr]] (OCR 범위 제한).
