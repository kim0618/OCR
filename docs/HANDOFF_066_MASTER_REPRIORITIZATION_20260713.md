# HANDOFF — 066 raw×master 재우선순위 (2026-07-13)

품명(itemName/itemNameMaster) 개선 작업의 공식 기준 문서.
두 도구(구현 담당 + 독립 리뷰 담당)가 동일하게 읽는 단일 소스. 채팅 메모리보다 이 문서가 우선한다.

- 기준 run: `ocr-server/eval/runs/066_20260709_122046/thin` (live, 5,964장, 7패치 배포 상태 — jamo V5 미배포)
- 목표 지표: **itemNameMaster(master 품명) 정확도**. 목표선 = 구글 독립행 **81.2%** (learndata 제외)
- 현재: raw 36.36% (13,584/37,363) · master **71.62%** (26,746/37,346)

## 1. 검증 완료된 사실 (2026-07-13, 양측 독립 재현 일치)

### raw×master 행단위 교차표 (compare/ 5,964장 전수)

| raw(itemName) → master(itemNameMaster) | 건수 |
|---|--:|
| raw 오답 → master 정답 (master가 흡수) | 14,160 |
| raw 오답 → master도 오답/누락 | 9,605 |
| raw 정답 → master 정답 | 12,586 |
| raw 정답 → master **오교정** | **945** |
| raw 정답 → master 누락 | 50 |

- raw 오답 23,779건 중 59.5%는 master가 이미 흡수한다. **raw 개선 ≠ master 개선.**
- raw정답→master 전환율 = 12,586/13,581 = **92.7%**

### 파서 결함(10,809)의 master 잔존 — 우선순위의 근거

replay defect(run_meta.ran 5,964장 제한) × 같은 행 itemNameMaster 상태 조인:

| 패턴 | 전체 | master 이미 정답 | **master 잔존** |
|---|--:|--:|--:|
| drop | 1,953 | 0 | **1,953** |
| wrongpick | 7,229 | 5,473 | **1,756** |
| mislocate | 1,627 | 1,084 | **543** |
| 합계 | 10,809 | 6,557 | **4,252** |

- drop의 master 회수 0은 구조적 필연(행이 추출에 없으면 master 셀도 없음) → **drop이 1순위 파서 레버**
- master 잔존의 **73.9%(3,143)가 fallback 경로**: fallback drop 1,563 / wrongpick 1,173 / mislocate 407 · free 390/583/136

### 상한

- oracle: (26,746+4,252)/37,346 = **83.0%**
- 전환율 92.7% 적용한 계획 추정치: **~82.2%** (단, 92.7%는 기존 raw정답 행의 평균이라 신규 복구 4,252건에 동일 적용 보장 없음 — 계획 기준치이지 확정 상한 아님)
- 결론: **learndata/FT 없이 파서만으로 81.2% 도달 가능성이 데이터상 존재.** 여유폭 ~1.0pp이므로 기존 master 정답 훼손 방지 게이트가 필수.

### 죽은 레버 (재론 금지)

- **전문/일반 꼬리 strip 289건**: master는 284건(98.3%) 이미 정답 → master 순증 ≤5건(+0.013pp). 성능 작업이 아니라 평가 파이프 복구 후 **smoke test**로만 사용.
- ext=헤더문자열('품명/품목') 1건, ext=순수 행번호 18건 → 기존 패치가 이미 소진.

## 2. 평가 인프라 결함 (0단계에서 수정)

1. **replay 49장 혼입**: `eval/replay_compare.py` 199행이 snapshots/ 전체를 열거하고 195·206–211행에서 "현재 manifest gtKey 존재"만으로 필터 → 잔재 49장(현 manifest 기준 gt_orphan 47 + active 2, 전부 gtKey 보유)이 replay_compare에 포함됨(6,013 = 5,964+49).
   - **수정 기준: 과거 run의 replay 범위 = 해당 run의 `run_meta.json`의 `ran` 목록** (066 ran=5,964, compare 집합과 정확히 일치 확인됨). 현재 manifest active를 쓰면 안 됨(이미 2,002장으로 변해 066 재현 불가).
2. **clean/angle 분류 무효**: `eval/parser_drop_classify.py` 50행 `CLEAN = {"1.jpg","3.pdf","4.pdf","5.pdf","6.pdf","7.pdf"}` — 구 24장 study 전용 하드코딩. 066 thin에서는 전량 ANGLE로 오분류 → **066의 CLEAN/ANGLE 통계는 사용 금지.** 수정은 파일명 추측이 아니라 manifest/GT 메타데이터(원본/변형 여부, 변형 원본 ID, 회전/기울기 정보) 기반으로.
3. live 채점(compare_summary·report·parser_drop_classify)은 정확히 5,964장으로 오염 없음 — 수정 대상은 replay 경로뿐.

## 3. 채택 게이트 (모든 패치 공통)

패치 채택 판정은 raw 상승이 아니라 **master 순증**으로:

- [ ] raw itemName 변화
- [ ] **master itemNameMaster 순증 (최종 판정 기준)**
- [ ] 기준 `raw오답→master정답` 14,160개 **행 ID 집합의 master 정답 유지율 100%** (raw가 고쳐져 교차표 구간이 이동하는 것은 정상)
- [ ] 기준 raw 정답 행에서 **신규 master 오교정 0** (기존 945건 감소는 개선, 증가는 회귀)
- [ ] itemCode / 수량·단가·금액(숫자열) 회귀 0
- [ ] spurious 증가 0
- [ ] free/fallback 경로 분포 변화 기록
- [ ] study(기준셋) 회귀 0

교차표의 구간별 숫자 자체를 고정하지 않는다. 보호 기준은 `(sourceFile, rowIndex)` 행 ID이며,
성공적인 raw 복구는 `raw오답→master정답` 행을 `raw정답→master정답`으로 이동시킬 수 있다.

### 공식 replay 게이트 기준

0단계 복구 후 사용자가 재실행한 `066_20260709_122046/thin/replay_compare`를 이후 파서 패치의
공식 replay 기준으로 사용한다. 기준 `PARSER_DROP_CLASSIFY_replay_compare.json` 값:

- scope 5,964 / stale 제외 49
- rawWrong→masterCorrect 14,309
- rawWrong→masterWrongOrMissing 9,456
- rawCorrect→masterCorrect 12,593
- rawCorrect→masterWrong 951
- rawCorrect→masterMissing 37

패치 전후 `rawMasterCross.protectedRows`를 행 ID 집합으로 비교한다. 기준 흡수 행의 master 정답
손실과 기준 raw 정답 행의 신규 master 오교정은 각각 차집합으로 보고하며, 카테고리 총수만으로
회귀를 판정하지 않는다. live 기준 교차표 `14,160/9,605/12,586/945/50`은 별도 불변 기준이다.

## 4. 실행 순서 (확정)

| # | 작업 | 대상 물량 | 비고 |
|--|---|---|---|
| 0 | 평가 복구: replay 범위=run_meta.ran 고정, 잔재 출력 집계 제외, clean/angle 무효화, raw×master 교차표를 공식 지표로 추가 | — | 이후 모든 측정의 전제 |
| 0' | smoke: 전문/일반 289건 strip으로 파이프 검증 | master +≤5 | 성능 아님 |
| 1 | master 순증 게이트 고정 (§3) | — | |
| 2 | **fallback drop 복구** | 1,563 | 숫자행 존재+품명만 빈 행에 같은 Y-band 한글 토큰 재탐색, 1후보 1행, 헤더/합계 제외, 숫자열 불변 |
| 3 | fallback wrongpick 열경계 | 1,173 | OCR bbox 기반 품명 열 좌우 경계, 코드/LOT/날짜/금액 bbox 제외, 문자열 strip은 bbox 근거 있을 때만 |
| 4 | free release-gate **A/B 먼저** | fallback 4,218장 | candidate oracle 측정(현 fallback vs free 후보 vs master 적용 후 vs 숫자열 vs gate 실패사유) 후 순이득 실패사유만 완화. 063 '78% 탈락' 진단은 2천장 기준이라 066 미검증 |
| 5 | mislocate 복구 | 543 (fb 407/free 136) | 금액행 Y-band 1:1 배정, 행높이 비례 임계값 |
| 6 | master 오교정 945 방어 | 945 (이론 +2.53pp) | **jamo V5 배포·검증 후.** top1/top2 margin, 짧은 품명 고임계, itemCode 충돌 |
| 7 | cropReady 재산출 → 선택적 재OCR·fine-tune | 현 12,400은 파서 개선 후 무효 | build_dataset.py 재실행 필수(train.txt 오염 앵커 잔존), parser 결함 crop 제외, 원본그룹 단위 split |
| 8 | learndata | 반복 오독만 | 최종 |

## 5. 역할 분담

- **구현 + 066 재검증**: 분석 담당 도구(이 문서의 교차 집계를 수행한 쪽)
- **독립 회귀 리뷰**: Claude Code — 변경 diff를 git으로 받아 §3 게이트 기준으로 검증, 과거 설계 의도(보호 로직·checker 규약·GT 계약)와의 충돌 확인, FT 장기 운영 모니터링
- 실행(서버·eval run)은 항상 사용자가 직접 수행

## 6. 재현 방법 (수치 검증용)

- 교차표: compare/*.json의 `table.rows[].cells`에서 itemName.status × itemNameMaster.status 행단위 집계
- defect 조인: `PARSER_DROP_CLASSIFY_replay_compare.json`의 defects에서 `column=itemName, class=parser_drop`을 run_meta.ran으로 제한, `location`의 rowN을 replay_compare/*.json 같은 행 itemNameMaster.status와 조인
- 경로: 각 compare 파일의 `extractionPath`
