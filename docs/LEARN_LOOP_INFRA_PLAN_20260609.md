# LEARN-LOOP-INFRA 실행 계획 (2026-06-09 lock)

> 새 채팅방 인수인계용 자기완결 문서. 이 대화 맥락 없이 이 문서 + 코드 + invoice_study GT만으로 Phase 0부터 실행 가능.

## 0. 한 줄 목표
대량 (이미지+정답)을 흘려 **측정→4버킷분류→룰 보강→재측정→회귀추적**이 자동으로 도는 평가/개선 루프를, **지금 6→30장으로 다 만들어 검증**하고, 데이터가 오면 **DB연결 한 줄만** 추가해 그대로 돌게 한다.

## 1. 배경 / 데이터 출처
- 경쟁사 `bak.war`(백제약품 OCR) 심층분석 결과: 그쪽 OCR 본체 = **Google Document AI**(자체 OCR 로직 없음, 매입 거래명세서→ERP 등록 래퍼). "학습"=교정 룩업테이블(우리 자동복원과 동일 패턴).
- 우리 = **PaddleOCR 자체호스팅(인식) + 룰 기반 비정형 추출기(구조화)** 로 이미 자체화 우위. Google은 비교/검증 기준일 뿐.
- 수천 장 학습데이터 = bak.war의 PostgreSQL DB(`tbl_ocr_invoice_master/body` = 검증된 이미지+정답). 사업 확정 후 덤프 확보 → ETL로 우리 GT 변환. 컬럼 매핑/ETL 초안: `d:\Free_Vue\_waranalysis\bjocr_db_to_gt_etl.py`. 컬럼 갭: 메모리 `project_invoice_column_gaps`.
- ERP코드 매칭/교정학습 적용 = **SI 영역**(OCR 범위 밖). 본 계획은 OCR 영역만.

## 2. 현재 상태 (GO)
- GT fixture 준비 완료: `OCR/mysuit-ocr/public/data/testsets/invoice_study/`
  - 이미지 6장 + `GT/` 6개 (draft-gt-document.v1). **2.pdf는 제외**(일시).
  - 행수: 1.jpg=28, 5.pdf=6, 6.pdf=6, 3/4/7.pdf=1(실제 단일품목 확정).
- 하니스 코드는 **아직 미생성**. Phase 0부터 시작.

## 3. 검증 통과 — 하니스 생사 3대 정합성 (코드 확인됨)
| 항목 | 결과 | 근거 |
|---|---|---|
| scalar 필드키 = GT labelEn(14) | ✅ 완전일치 | `ocr-server/extractors/invoice_statement_free.py` L49-66 vs GT labelEn |
| 테이블 행키 = GT 행키 | ✅ 포함 | free 행키(itemName/spec/productCode/lotNo/expiryDate/quantity/unitPrice/amount) L24-37 |
| API 응답 봉투 | ✅ 확정 | `response["document_fields"]` (main.py:3012) 안에 scalar+tableRows+tableMeta |

GT labelEn 14: supplier/buyer×{Company,BizNumber,Representative,Address}, issueDate, supplyAmount, taxAmount, totalAmount, cumulativeAmount, totalQuantity.

## 4. 검증 중 잡은 7개 캐치 (계획에 반영됨)
1. GT 필드 샘플마다 13개·union 14 (totalAmount/totalQuantity가 파일마다 갈림) → **per-sample 필수셋, 없는 필드 감점 금지**.
2. rich(지금: bbox/edited/confidence/fieldStatus) vs thin(ETL GT: 없음) → 이들 **optional**, 코어비교는 값+행만.
3. 응답 키 혼합: 봉투 snake `document_fields`, 내부 camel `supplierCompany`, 배열 `tableRows` → `resp["document_fields"]["tableRows"]`로 정확히.
4. GT 행 리뷰메타(amountOnly/missingFields/fieldStatus/reviewStatus/excludeReason/sourceRowMeta/tableExtraColumns)는 추출기 출력 아님 → **value 키만 비교**.
5. GT 최상위 `excludedRows` → 비교가 **누락으로 오판 금지**.
6. free 실패 시 fallback `extract_invoice_statement_fields`(main.py:3003)로 전환 → 결과에 **`tableMeta.extractionSource` 기록**, free/fallback 분리 집계.
7. run_batch는 라이브 9099 필요, PDF=fitz 멀티페이지(샘플은 1p) → **page0 가정+페이지수 assert**.

거버넌스: `eval/`은 신규·측정전용(추출기 호출만, 수정 없음), 결과는 `eval/runs/`에만, `public/data` read-only → CLAUDE.md 단계규칙 위반 없음.

## 5. GT 계약 (Phase 0 산출물)
```
schemaVersion: draft-gt-document.v1 / 단위: 이미지1=GT1파일
필수(rich·thin 공통, 비교대상):
  documentFields = normalizedResult.fields[] → {labelEn: value} 평탄화
    공통 12: supplier/buyer×{Company,BizNumber,Representative,Address}, issueDate, supplyAmount, taxAmount, cumulativeAmount
    per-sample(있을때만 채점): totalAmount, totalQuantity
  tableRows[] value키: rowIndex,itemName,spec,productCode,lotNo,expiryDate,quantity,unitPrice,amount
선택(rich전용, 보너스/없어도통과): bboxRefs, edited, confidence, fieldStatus, orientationGt
제외: 행 리뷰메타, excludedRows(=감점제외), ERP코드(thin엔 없음)
```

## 6. 단계 (Phase 0~6 = 지금/6장 · 7 = 데이터 올 때)
| Ph | 작업명 | 산출물 | 게이트(GO) |
|---|---|---|---|
| 0 | SCHEMA-CONTRACT | `eval/GT_CONTRACT.md`(§5) + `eval/` 골격(.gitignore runs/) | 6장 계약 100% 파싱 |
| 1 | INGEST | `build_manifest.py`(자동페어링+status, 2.pdf=excluded), `gt_loader.py`(fields[]평탄화·thin우아·excludedRows분리) | 6장 manifest+로더 6/6(checker) |
| 2 | RUNNER | `run_batch.py`(PDF직접POST templateMode=unstructured, resp["document_fields"]+page0, 재개·병렬·에러격리, runs/<ts>/, extractionSource 기록) | 6장 실행→result 저장, 실패0/격리 |
| 3 | COMPARE | `compare_fields.py`(labelEn매칭+정규화freeze+edited트래킹+per-sample필수셋), `compare_table.py`(per-row 풀, value키만, excludedRows제외), 4버킷태깅(인식A/구조B/전처리/레이아웃) | 6장 비교가 사람 스팟체크 일치 |
| 4 | METRICS-REPORT | `metrics.py`(필드/전체/버킷+슬라이스 supplier·layout·qualityTag, edited별도, free/fallback별도), `report.py`(MD: 가설배너+필드표+실패 GT/추출 나란히), 시계열(sqlite/parquet) | 6장 e2e→report.md, 메트릭 자기일관 |
| 5 | CHECKER-RUNALL | `checker.py`(manifest↔파일·메트릭합·파싱율·정규화 골든회귀), `run_all`(1커맨드) | checker PASS+1커맨드 재현 = **MVP GO** |
| 6 | SCALE-DRYRUN-30 | 사용자 24~30장 GT 흡수, holdout/슬라이스 코드경로 실발화 | 30장서 신뢰 버킷·슬라이스 = **인프라 검증 완료**(정확도 판정 아님) |
| 7 | DATA-SEAM(데이터 올때) | `bjocr_db_to_gt_etl.py`를 GT계약에 정렬(평면→draft, thin프로파일)+로컬DB/이미지 fetch+**master JOIN 보강(아래 §6.5)** | ETL GT 1배치 하니스 무수정 통과 = **드롭인** |

### 6.5 GT 보강 규칙 — master JOIN (Phase 7 확정, 2026-06-09)
bak.war DB 통째 긁으면 마스터 테이블도 딸려옴. 거래테이블에 없는 필드는 **코드 JOIN으로 보강**:
- `invoice_master.cust_cd` → `tbl_ocr_master_buycust.cust_nm`(회사명), `.cust_address`(주소) → supplierCompany/supplierAddress 채움.
- JOIN은 코드 직결이라 **유사도 대조 불필요**(cust_cd가 이미 확정 링크, ERP 등록 전 사람 확인됨).
- ⚠️ 마스터=공식값 / 종이=인쇄값 → 보통 일치(우리 정규화가 `(주)`·공백 흡수), 드물게 어긋남(지점명/옛이름).
- → master로 채운 필드는 **`source:master` 태그** 부착(검증 추적용). 메트릭은 사람검증분과 분리 집계. 소수 어긋남만 스팟체크.
- 적용 대상 = 회사명·주소(거래테이블에 깨끗이 없는 것)만. 품목명(description)·금액·수량·날짜·사업자번호는 거래테이블 직접 사용(JOIN 불요). 대표자·요약필드는 마스터에도 없음 → invoice_study(rich)가 담당.

### 6.6 Phase 7 사전 재설계 (P0, GT-driven, thin-ready) — LOCK 2026-06-09
**상태: 설계 LOCK + war 컬럼계약 검증 완료. 빌드 PENDING (새 채팅방서 step 0부터). 이건 정확도가 아니라 측정·수용 인프라 작업.**

**왜:** Phase 0~5 MVP는 rich invoice_study 6장에 하드코딩됨(`gt_loader` COMMON_12+rowIndex 강제, `compare_fields:31` 14필드 고정, `compare_table:21` CELL_KEYS 고정, `phase1/3_check` 필드수13, `contract.TESTSET_DIR` 단일, profile 콘텐츠추론). → DB thin GT 넣으면 **로드부터 실패.** "thin 통과"가 문서원칙일 뿐 미구현. P0=전 파이프라인 GT-driven化.

**war-검증 컬럼계약 (실 SQL 대조, SSOT 상수로 코드화할 것):**
- 스칼라(10): totalAmount, taxAmount, discountAmount⭐, issueDate, documentNumber⭐, supplierBizNumber, buyerBizNumber, supplierCompany(저신뢰=brcd_name), taxType⭐(저신뢰), supplierAddress(master JOIN §6.5)
- 행(6): itemName, quantity, unitPrice, amount, expiryDate, manufacturingNo (rowIndex 없음)
- 멀티페이지: separate_img_path → 1이미지=1GT. ⭐=신규3필드(추출기 미배출→정직한 100% miss). thin 미보유 7필드(supplyAmount·supplierRepresentative·buyerCompany·buyerRepresentative·buyerAddress·cumulativeAmount·totalQuantity)=rich(invoice_study) 전담.

**불변식 (➊~⓳', 코드위치):**
- 입출력계약: ⓮'(ETL이 정식봉투{schemaVersion/sourceFile/normalizedResult.fields[] thin+tableRows}를 per-file로, bbox/edited 없음) · ⓳'(profile=⓬ testset프로파일서 load_gt에 주입, 콘텐츠추론 폐지; `RICH_FIELD_KEYS` 추론은 checker 일관성검사로 강등) · [➒·⓮ 소멸]
- 로더: A(COMMON_12 hard→rich 한정 soft-warn) · ⓫(rowIndex optional)
- 채점(compare_fields): ➊⓭(scored=gt.keys(), perSampleField 퇴역) · ➋(per-sample 불변식 rich게이팅) · ➍(normalize 타입맵 신규3필드+이름휴리스틱 *Amount/*Price→amount,*Date→date,*Num/*Code/*No→code,manufacturingNo/serialNo→code)
- 채점(compare_table): ⓰(CELL_KEYS→GT행이 준 키 기준 iterate) · B(rowIndex정렬→내용기반 itemName/amount 유사도)
- 메트릭/리포트: ➐(difficultySplit: rich=edited / thin=low_confidence, gt["profile"]로 분기) · ➌E(커버리지 2분모: graded/GT-present vs 추출기-미시도갭)
- 체커/contract/manifest: ➑➓(EXPECTED_ROWS·필드수13[phase1_check:55/phase3_check:69] 제거→per-testset 프로파일) · ⓬(testset 프로파일{dir,expected,rich|thin}) · ⓲(build_manifest에 canned 상태=이미지없이 녹화결과로 실행) · bboxRefs 일관성검사
- fixture: ⓯⓱(정식봉투 thin GT + 녹화 rec봉투{document_fields+extractionSource+pageCount+multiPage})
- clean(무수정): buckets.py · 슬라이스 코어 · normalize 코어
- **SSOT: 다운프로젝터 thin필드셋 = ETL thin필드셋 = 위 컬럼계약 단일상수** (step1·6 공유 → oracle이 진짜 production 모양 보장)

**빌드 시퀀스 (TDD red→green):**
```
0. testset 프로파일{dir,expected,rich|thin} + load_gt에 profile 주입(⓳') + manifest canned 상태(⓲)
1. thin fixture = war실컬럼 정식봉투 + 녹화 rec봉투 (추측 아닌 war모양, SSOT상수 참조)  → red
2. 로더 바깥계약 무수정 + 안쪽완화(A/⓫/➊⓭/⓰) + profile주입(⓳') + ➋ rich게이팅       → 로드+채점 통과
3. normalize 타입맵 신규3필드 + 이름휴리스틱 폴백(➍)
4. 내용기반 행정렬(B) + rich rowIndex oracle 수치게이트(➏)
5. metrics/report: difficultySplit(➐) + 커버리지 2분모(➌E)
6. checker: thin통과 ∧ 6장rich green + per-testset 프로파일(➑➓⓬) + bboxRefs일관성 + 행정렬 oracle(➏)
```

**수용기준 (양방향):** thin fixture full-pipeline 통과 ∧ **6장 rich를 thin으로 다운프로젝션→rich경로vs thin경로 일치**(SSOT상수 기반=진짜 oracle) ∧ 6장 rich 끝까지 green.

**Deferred (실데이터 와야, 코드에 가시화):** product_code 의미(인쇄코드 vs ERP매칭코드→productCode 매핑/drop 결정) · brcd_name 의미(거래처명 vs 지점명) · page-spanning 1:1(separate_img 단위=논리적 송장 1:1인지) · 필드 채움률/null/인코딩 quirk · 실정확도(스케일) · drop-in 바이트검증 · 룰보강 실행(운영OCR 락→범위승인).

## 7. 상시 루프 ("학습이 돈다")
```
manifest → run_batch → compare(field+table)+4버킷 → metrics(슬라이스) → report → 시계열
   → 사람이 약한 버킷에 룰 보강 → 재실행 → 회귀감지 → 반복
```

## 8. 불변 원칙
- 6~30장 = 인프라 검증(기계가 도는가). 정확도 합격은 수천 장 몫. **소표본 수치=가설, 아키텍처 확정 금지.**
- 하니스는 GT파일 계약만 안다 (DB는 ETL이 흡수, 하니스 DB-무지).
- 코어 비교 = 값+행 공통분모 (bbox/edited optional → thin GT도 통과).
- 운영 OCR 로직·public/data **무수정**. 코드=`ocr-server/eval/`, 결과=`runs/`.
- 폴더 ocr-server/eval/, runs/ 는 .gitignore. 2.pdf=일시제외(status).

## 9. 새 채팅방 시작법
1. 이 문서 + `OCR/CLAUDE.md` + 메모리 `project_learn_loop_infra_plan` 읽기.
2. Phase 0부터 순서대로. 각 Phase는 산출물 = script + summary + report/notes + **checker**, 게이트 통과해야 다음.
3. 핵심 경로:
   - GT: `OCR/mysuit-ocr/public/data/testsets/invoice_study/` (이미지 + GT/)
   - 추출기(비정형): `ocr-server/extractors/invoice_statement_free.py`, 호출 main.py:2958, fallback main.py:3003
   - 응답키: `response["document_fields"]` (main.py:3012), `tableMeta.extractionSource` (main.py:3015)
   - 서버: 9099 (uvicorn --reload), 엔드포인트 `/ocr/extract` (main.py:2017, Form 2020-2028)
   - ETL 초안: `d:\Free_Vue\_waranalysis\bjocr_db_to_gt_etl.py`
```
