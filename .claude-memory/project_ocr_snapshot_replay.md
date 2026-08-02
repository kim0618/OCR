---
name: project_ocr_snapshot_replay
description: GPU→로컬 round-trip용 OCR 스냅샷 캡처 + replay_free 재생 하네스 (재-OCR 없이 파서 분석/검증)
metadata: 
  node_type: memory
  type: project
  originSessionId: 2760a9ad-7e14-435b-b20f-db7b97d95547
---

2026-06-16 구현·검증 완료. GPU(프로덕션)에서 eval 돌리고 로컬에서 파서 고치는 round-trip을 위해, run이 이미지별 **free 추출기 입력 envelope**를 저장하고 로컬에서 재-OCR 없이 재실행하는 인프라.

**캡처 (main.py — 보호파일, 사용자 승인받음):**
- Form 파라미터 `captureOcrSnapshot`(eval만 "1" 전송, 프로덕션 미전송→무영향).
- free 호출부를 `_free_full_text`/`_free_context` 단일소스로 리팩터(동작 보존) 후, 플래그 시 `response["ocr_snapshot"]`에 5개 입력(ocr_lines_raw 직렬화 + full_text + image_size + doc_type + context) 캡처. 헬퍼 `_serialize_ocr_lines_for_snapshot`.
- `_try_invoice_free` 분기 안에서 잡으므로 **fallback으로 떨어진 샘플도 free 입력은 캡처됨**.

**저장 (eval/run_batch.py):** 응답 스냅샷을 `runs/<ts>/snapshots/<src>.json` 사이드카로 기록. rec(`samples/*.json`) 스키마는 **무수정**(`_ocrSnapshot` 키를 dump 전에 pop) → checker `manifest<->run`(samples/*.json glob)·phase2/3/4·metrics·trend 전부 무관. report/compare/metrics가 run_dir 하위를 통째 순회 안 하고 명시경로(samples/·compare/·metrics)만 봐서 새 폴더 안전.

**재생 (eval/replay_free.py, 신규):** 스냅샷→`extract_invoice_statement_free(**envelope)`→후처리(`sanitize_document_scalar_fields`, **방어적 import**: 사용자가 파서 함수명 자주 바꿔서 try/except로 없으면 identity)→기록값 대비 FAITHFUL/DIFFERS. `../.venv/Scripts/python.exe eval/replay_free.py --testset invoice_study`.

**검증(run 034):** checker 2/2 PASS, 점수 63.1% 기준 그대로(회귀 0), 스냅샷 24개, **FAITHFUL 6/24 = free 경로 6개(1.jpg계열·4-1·5.pdf)와 정확히 일치**. DIFFERS 18개는 fallback(기록값이 fallback 추출기 출력이라 정상) — 동시에 "free가 왜 깨졌나" 진단 표면.

**운용 원칙:** eval은 AWS GPU에서만, 로컬은 분석/재생만(metrics_timeseries.sqlite 바이너리 충돌 회피). 파서 수정=로컬에서 replay로 1차검증→push, 최종확정=AWS run. 전처리(deskew)/OCR모델 수정은 로컬 검증 불가→AWS 재run. [[project_learn_loop_infra_plan]] [[project_preprocess_image_deskew_gap]] [[feedback_local_cpu_vs_gpu_prod]] 참조.

**2026-06-17 로컬 루프 완전 폐쇄 + 파서-drop 분류기 추가.** replay_free는 free 출력을 기록값과 FAITHFUL/DIFFERS만 비교(채점 안 함)→로컬 루프 끊겨 있었음. 두 신규 사이드카로 닫음(둘 다 읽기전용, checker 경로 samples/·compare/·metrics 무수정):
- `eval/replay_compare.py` = **빠졌던 "재채점" 단계.** 스냅샷에 수정파서 재실행→GT와 compare_fields/compare_table/buckets(=AWS와 동일 채점)→사이드카 `runs/<ts>/replay_compare/`에 compare스키마로 기록. **충실 디스패치**: 서버 free→`_is_valid_invoice_statement_free_result` 게이트→fallback `extract_invoice_statement_fields(ocr_lines_raw, tableExpectedColumns/tableBounds/columnGuides)` 분기를 그대로 재현(셋 다 extractors서 import, main.py 안 거쳐 OCR모델 로드 없음). **fallback도 스냅샷 입력만으로 재현 가능**(같은 ocr_lines+context). 미재현=FREE_HIRES_TABLE_REOCR(재OCR필요, 기본OFF)뿐. run053서 **24/24 FAITHFUL(6 free/18 fallback)**, 분류 defect 351건 baseline과 identical→채점 신뢰.
- `eval/parser_drop_classify.py` = compare×snapshots 교차로 결함셀마다 **"GT값이 OCR출력에 실재하나"** 직접판정(buckets는 글자유사도 추정뿐). present=parser_drop(회수가능)/absent=recognition(OCR바운드). 패턴 drop(통째누락)/mislocate(엉뚱컬럼)/wrongpick(정답라인있는데 다른거선택). `--compare-dir replay_compare`로 수정후 재분류, clean/변형 분리. 출력 `PARSER_DROP_CLASSIFY[_<dir>].{md,json,html}` — **html=전체 field%/cell%(KPI)+샘플별점수표(free/fallback색)+부류×패턴표 한 파일, 브라우저로 봄(AWS SUMMARY/report.html의 로컬 대체).** metrics.json/timeseries sqlite 안 건드림(읽기전용). ⚠️로컬서 metrics.py/report.py 직접 돌리면 sqlite 시계열 오염되니 금지—이 html로 대체.
- **루프:** 파서수정→`python eval/replay_compare.py`→`python eval/parser_drop_classify.py --compare-dir replay_compare`→`PARSER_DROP_CLASSIFY_replay_compare.html` 열어 수정전(`..._.html`/`PARSER_DROP_CLASSIFY.html`)과 부류·점수 비교. AWS/재OCR 불요. 최종확정만 AWS.
- **위치 = run폴더의 testset 하위(study/), report.html 옆**(데이터 compare/snapshots와 같은 곳). batch레벨 SUMMARY.html(study+thin 합산)과 다른 레벨 — 내 classifier는 report.html 짝(testset별 상세).
- **[완료 2026-06-22] 배치레벨 로컬 합산뷰 구축:** `eval/local_summary.py`(신규) = 배치(runs/<batch>/study,thin)의 testset별 parser-drop 분류를 합쳐 `LOCAL_SUMMARY[_replay_compare].html` 렌더(AWS `SUMMARY.html`의 로컬 등가, 이름 분리). 합산 KPI카드 + 데이터셋별 micro/macro + 분류상세/report.html/compare.html 링크 + testset별 컬럼×패턴 + replay_history 누적이력 = SUMMARY 미러. **자동 wiring**: `parser_drop_classify.py`가 끝에 merge-only(refresh=False, 재귀無)로 local_summary 호출 → 기존 루프(replay_compare→parser_drop_classify --compare-dir replay_compare)만 돌리면 자동 생성. parser_drop_classify JSON에 per-sample `scores` 추가(합산뷰 KPI용). 둘 다 checker-safe 사이드카, 로컬 전용(AWS run_all 안 돌림). thin은 목업이라 "스냅샷 없음" 표시→실데이터(invoice_war) 오면 자동 채움. 컴파일 검증만(실행=사용자). **미커밋 상태.**
- **DEFERRED(원래 계획, 위로 대체됨):** 배치레벨 parser-drop 합산뷰(study+thin 묶은 SUMMARY.html 등가) 추가. 지금 thin은 canned 목업(스냅샷 없어 parser_drop 판정 불가)이라 합쳐도 무의미 → 파서 우선 원칙대로 보류. classifier가 이미 `--testset`로 도니 그때 study/thin 두 결과 합치는 ~30분 얇은 작업. 사용자 2026-06-17 "나중에 추가하게 기억" 명시. [[project_learn_loop_infra_plan]] Phase 7.
- **run053 베이스라인 측정:** 결함351 = parser_drop200(57%, OCR읽음·회수가능) + recognition151(OCR바운드). parser_drop 경로분해 = **free 68**(itemName24·spec16·lotNo12) / **fallback 132**(quantity24·productCode21·lotNo18·expiryDate13). 18 fallback샘플이 회수가능 drop의 66% 보유. [[feedback_class_not_per_case]] [[feedback_systematic_report_analysis]]
- **⚠️ replay 숫자 = 디바이스 무관 "파서 진실" = GPU-프로덕션과 동일.** 스냅샷에 OCR(박스+글자)을 얼리고 파서만 재실행하니, parser-drop/recognition 분석은 GPU에 그대로 전이됨(파서는 어디서든 CPU코드, 한글 server rec 없음→인식도 디바이스 무관). 따라서 **파서 결함을 "GPU 가서 확인/고치자"로 미루지 말 것** — GPU 유일 레버 server_det는 이미 검증→死([[project_preprocess_complete_24base]]: "셀손실 98%=파서, server_det 死"). 053이 로컬 9099(serverUrl)서 떴어도 결론 동일. 2026-06-17 이 함정 1회 재발해 명문화. [[feedback_local_cpu_vs_gpu_prod]]
- **P1 완료(2026-06-17, 커밋·푸시):** fallback productCode 표면화 + spec/itemCode→productCode shape게이트 승격(`invoice_statement.py`: `_TABLE_ROW_COLUMNS`+`_empty_table_row`에 productCode, `_fb_looks_like_product_code`/`_fb_normalize_product_code`, `_build_canonical_table_rows` 승격블록). 원인=캐노니컬 빌더가 itemCode만 출력(legacy 재구성기만 productCode 채움)+각도변주 코드토큰 spec 오배정. replay 검증: 셀 779→791/1043, productCode drop 21→10, spec spurious 9→1, 회귀0·전샘플 FAITHFUL. **공급자5(단일 클린원인) 회수가 이 배치 마지막 클린 CPU win**. 잔여 productCode/lotNo drop은 6-1 각도 scatter(코드/품명/lot 다른 y밴드)·숫자코드(supplier3)로 분산 → per-case 두더지잡기·과적합 경계.
