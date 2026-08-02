---
name: project_invoice_war_gt_reshape
description: war GT를 로더 호환 thin 집계 형식으로 재작성 완료 + 필드 4계층 발견 + enrich 필드 추가. 재발행 커맨드.
metadata: 
  node_type: memory
  type: project
  originSessionId: b0952ab4-a664-4a13-9b66-86ff4c04873c
---

2026-06-24. war GT(ground_truth_2606.json)를 우리 harness 계약(contract.py thin)에 맞게 **재작성·검증 완료**. [[project_invoice_war_db_restored]] 후속.

**필드 4계층 발견 (war가 값을 어디 두나):**
1. 구조화 컬럼(직접 SELECT): totals, 사업자번호 양쪽, issueDate, taxAmount, taxType(tax_yn), discountAmount(total_dc_price, 10%만 비0), supplierCompany/Address(cust_cd→master_buycust).
2. 유도/조인: **supplyAmount = total_amount−total_vat_price**(=순매출액, 99.4% 숫자정합), **buyerCompany/buyerAddress = brch_cd→master_brch.brch_nm/addr**(buyer=백제 지점).
3. 원문 ori_ocr_text에만 비정형: supplierRep/buyerRep(종이엔 있으나 컬럼 없음 → 파싱하면 순환, GT 제외).
4. 진짜 부재: documentNumber(invoice_num 전량"0"), productCode(전량 빈값), cumulativeAmount.
※ war 최종 산출 = OCR 숫자 + **매칭 코드 item_cd**(품목)/cust_cd(거래처). item_cd만 있으면 약품명·단가·보험코드 다 마스터 조회. 우린 코드개념 없음 → 마스터매칭이 이 item_cd를 채우는 일 = 백제ERP 통합의 핵심.

**한 일(검증됨):**
- `eval/data/invoice_war/build_gt.sql` v2: 출력형식을 `{schemaVersion,profile:"thin",month,documents:{<imgKey>:{sourceFile,normalizedResult:{fields[],tableRows[]},_source}}}`로. documentFields(객체)→fields[]({labelEn,value}). row키는 **계약 THIN_ROW_KEYS 준수**(manufacturingNo 유지, rowIndex 없음=내용정렬). enrich 추가: supplyAmount/buyerCompany/buyerAddress(doc), **itemCode=body.item_cd**(row).
- **itemName 3분리(워크플로 정합 핵심)**: `itemName`=원문 description(범용파서 채점=글자읽었나) / `itemNameMaster`=마스터 정식명 / `itemCode`=item_cd. 이유: 원문≠마스터 86.4%라 itemName을 마스터로 두면 범용파서가 정상이어도 감점→측정 거짓말. GT는 셋 다 정답데이터로 보유.
- **★itemCode는 "어댑터 전용"이 아님(2026-06-24 정정)**: 한때 공용 채점기에서 itemCode/itemNameMaster를 전역 제외(ROW_REFERENCE_KEYS) 추가했다가 **되돌림**. 이유: itemCode가 매칭산출인지 OCR-read인지는 **업체별 속성**(백제=코드 미인쇄→매칭만 / 타업체=코드 인쇄→OCR로 읽음). 공용 contract/compare_table에 박으면 범용원칙 위반. → 공용 채점기 중립 유지, "백제 문서엔 코드 미인쇄=매칭산출" 같은 건 **per-testset 프로파일**에 war셋 배선 시(이미지 도착) 선언. [[project_master_match_baseline]] 워크플로와 합치.
- `eval/gt_loader.py`: `load_gt_aggregate(path)` 추가(thin 집계 1파일→{imgKey:load_gt모양}, 기존 _flatten_fields/_value_rows 재사용). 백업 `*.20260624_bak`.
- 검증: 23,737 docs / 272,965 fields / 150,251 rows, loader OK. supplyAmount 산술·buyer 조인·itemCode 진입 실데이터 확인.

**재발행 커맨드(사용자 실행, ★-o 필수 — PowerShell `>`는 UTF-16라 깨짐):**
`$env:PGPASSWORD="root123"; $env:PGCLIENTENCODING="UTF8"; & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -d bjocr -v mon=2606 -A -t -X -o "...\eval\data\invoice_war\ground_truth_2606.json" -f "...\build_gt.sql"` (≈49MB)

**comparator 자동채점**: compare_fields는 `gt_fields.keys()`를 채점(고정목록 아님) → enrich 3필드 자동 포함. normalize.py에 supplyAmount=amount/buyerCompany=text/buyerAddress=address 이미 정의. contract.py THIN_SCALAR_FIELDS는 fixture down-projector용이지 채점게이트 아님 → 수정 불필요. checker 일관성 경고 가능성만 있고 war runner 배선 시 한 줄로 정리.

**★학습루프 배선 완료(2026-06-24): thin = war 실데이터로 교체.** "이미지만 올리면 바로" 요구 충족, mock으로 양쪽 루프 증명.
- `contract.py`: `_testset`에 `gt_aggregate`/`images_nested` 옵션 + `safe_sample_id()`(키의 `/`→`__`). `invoice_thin` repoint: dir=`eval/data/invoice_war/images/`, runMode=**live**, gt_aggregate=ground_truth_2606.json, expected={}. (기존 canned 픽스처 빠짐)
- `build_manifest.py`: `_build_manifest_aggregate`+`_images_nested`. 집계GT 1회 로드, 중첩이미지 walk(key=relpath posix), sourceFile=safe id·gtKey=원본키. 이미지 올린 것만 active, 나머지 gt_orphan(안 돎).
- `compare_run.py`/`replay_compare.py`: manifest.gtAggregate면 `load_gt_aggregate` 1회+`agg[gtKey]`, 아니면 기존 per-file `load_gt`. run_batch/parser_drop_classify/local_summary=무수정(sourceFile 평면·sidecar reader).
- 검증: mock 이미지 3장→manifest active 3/gt_orphan 23734, compare echo 100%. 로컬루프 replay_compare도 집계GT 조회+채점 동작. 백업 `*.20260624_bak`.
- **사용자 할 일**: `Z:\LIVE\processed\2606`의 **하위폴더들을** `images/` 바로 밑에 복사(←2606 폴더 자체 아님, 경로 `images/451694/...`). 서버:9099 켜고 `python eval/run_all.py --testset invoice_thin`. 수천장만(전량 23737은 CPU 며칠).
- 미테스트: live OCR POST 한 곳(기존 무수정 코드). 다음=이미지 도착→측정.

**전처리 진단 = parser_drop_classify에 섹션 추가(2026-06-24, 새 HTML/스크립트 0개).** 별도 리포트 안 만들고 기존 `PARSER_DROP_CLASSIFY.html`에 "전처리 진단" 섹션으로. 설계: run의 `samples/*.json` preprocess 텔레메트리(orientation.allScores margin·deskew.absAngle·overApplyGuard·document.areaPct/forcedWarpOnSkip/uvdoc conf) 읽어 **조건 버킷별 셀정확도+recognition율+Δ vs baseline** 교차표(O(버킷)=수천장 스케일불변, GT前 위험신호라 서버 전처리 결함에 직결). `_pp_features`/`_orient·deskew·warp_bucket`/`_preprocess_buckets`/`_render_preprocess_section` 추가. **run_all 사이드카에 parser_drop_classify 추가(2026-06-24)** → 매 run 자동 생성(전처리 진단 포함). 로컬루프·local_summary에서도 생성. **검증(study 054): 270°적용 recognition 48.7%=+34.7pp, guard-revert 100%=+85.2pp 신호 잡음.** md/json/html 다 포함, 기존섹션 무회귀.

**★전 체인 실증(2026-06-24)**: 가짜 war run(실GT키+study차용 스냅샷/processed/preprocess)으로 `run_all._measure(reuse,testset=invoice_thin)` 구동 → compare/metrics/report/**checker PASS**/finetune적립/table_align/parser_drop+전처리 전부 정상. **남은 미검증=live OCR POST 1줄(기존 무수정, 서버+실이미지 필요)+실제 정확도(실이미지). 그 외 끝까지 검증.** 세션 수정 8파일: build_manifest·compare_run·contract·gt_loader·parser_drop_classify·replay_compare·run_all·table_align_diag(미커밋). 테스트가 finetune_corpus 오염시키니 후엔 `git checkout finetune_corpus/labels*.txt && git clean -f finetune_corpus/crops*/`로 정리.

**★마스터 사전 추출 완료(2026-06-24, 이미지-무관 선결인프라).** `eval/data/invoice_war/build_master.sql`(생성기, build_gt.sql 옆) → `master_dict.json`(10.4MB, gitignore). 단일 JSON 5사전+_meta: `item`(38,848: item_cd→{nm,unit,bp1,bohum}) `cust`(14,954: cust_cd→{nm,addr}) `brch`(10: brch_cd→{nm,addr}) `biznoToCust`(4,835: 사업자번호→cust_cd, master_buycust엔 사업자번호 없어 invoice_master서 유도=우리 거래처매칭 앵커) `learndata`(75,332 distinct ocr_item_nm→{cd,n} top-count). 매칭입력(item_nm·bp1)+채움출력 다 포함. 재발행 `-o master_dict.json -f build_master.sql`(★-o필수 UTF-8). 아직 매칭기 미구현(이건 사전만). [[project_master_match_baseline]] 순서: 룰→마스터→파인튜닝.
