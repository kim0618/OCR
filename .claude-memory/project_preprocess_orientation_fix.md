---
name: project_preprocess_orientation_fix
description: 전처리 1차 완료 = orientation 90/270 오회전 수정(box-AR reverify). 검증됨(AWS 062). 남은 잔여 39장은 나중에. 룰 base=062
metadata: 
  node_type: memory
  type: project
  originSessionId: dc3825c3-fd4e-46d2-bea1-543f783e74bc
  modified: 2026-07-23T01:15:39.877Z
---

2026-07-03. 스케일(war 2002장)이 드러낸 유일한 전처리 갭 = **orientation 90/270 오선택**을 수정해 **전처리 1차 완료**. 이후 단계는 파서(룰). [[project_preprocess_complete_24base]](24장 기준 "완료, 스케일 갭시 재방문")의 재방문 조건 충족→처리함.

## 문제 (진단, run061 전수)
- 표 셀손실 지배원인이 "행 과분할"로 보였으나 전수분해→ **63%가 진짜 과분할 아니라 정렬실패 아티팩트**(itemName 미파싱). 진짜 초과는 +1~3.
- 그 이면에 **164장(8%)이 옆으로 누운 채 OCR됨**(cellAcc 1.9%). 원인=detect_orientation이 90/270 near-tie(점수 동점)서 코인플립 오선택. 180°는 정상, 0°놓침은 희박(11).
- 탐지기: **OCR 라인박스 종횡비(medBoxAR)**. 누움=박스 세로(medAR≈0.45) vs upright≈2.32로 깔끔히 분리(cellAcc 1.9 vs 13.5로 검증). korean비율은 sideways서도 ~40%라 신뢰 불가(기존 게이트가 못 잡은 이유).

## 수정 (코드, 미커밋)
- **main.py**: `_median_box_aspect()` 헬퍼 추가. `ORIENT_KOREAN_REVERIFY` 블록 보강 — 트리거에 **box-AR<1.0(세로=누움)** 추가(기존 korean garbage<0.10에 OR). 선택=`_orient_score=kr*(가로면1.0/세로면0.3)`로 "가로로 읽히며 한글최다" 방향. 채택가드=한글2배 OR (세로→가로 AR<1→≥1.5 & 한글손실무). **재-OCR 3방향 루프 try/except 방어**(후보 실패해도 원본 유지→커넥션드롭 방지).
- upright 장은 medAR≈2.3이라 box-AR 트리거 절대 미발동 → 039/051식 정상표 오회전 원천봉쇄(offline 검증: upright 0/1678 오발동, sideways 164/164 포착).

## 검증 (AWS run 062 = orientation 배포후 실측)
- **177장 재회전**(box-aspect 147+korean 30), pickedRot 270×147. AR flip 성공 151/177. **채택 이미지 cellAcc 4.4→14.2%**.
- **thin 셀 12.4→13.4%**(매트릭스 셀 13.7→14.8, 필드 47.2→47.7). **study PASS**(90.1→89.7 미세, 원인=회전성공이 R1 blob 노출—회전버그 아님. 3-2/452497/465054 육안 upright 확인).
- **sideways 164→15장**(149 해소). 회귀로 보인 것 전부 upright 확인됨=R1 파서 문제(itemName-blob/이하여백 과분할)지 회전 실패 아님.

## ★남은 전처리 잔여 = 나중에 (미룸, 사용자 승인)
- **15장 아직 누움**(reverify가 no_better_orientation—확신 못 함). 일부는 아예 못 살리는 사진(극단각도/흐림). 수천장중 소수 불량은 정상, 100% 목표 아님.
- **24장 큰 기울기(>2° deskew, cellAcc 3.7%)** — 90/270 아닌 tilt라 별도 레버. deskew가 왜 얘네만 못 고치나 미진단.
- 계 **39장(2%), 다 고쳐도 ~+0.2pp**. **재방문 시점=파서(R1~R4) 어느정도 마친 뒤 "전처리 2차 청소" 라운드.** AWS-only 검증이라 지금 하면 비쌈. 안 버리고 추적. **사용자에게 이 시점 오면 알릴 것.**

## ★2026-07-23 업데이트 = 067 replay(9,001) 전처리 실패 전수측정 + 오회전 버그 발견
- **전처리 귀책 실패 = 310장(3.4%)**: envelope 회전 66(0.7%, 셀14.9%) + 잔여기울기 2-4° 241(2.7%, 셀34.6%) + tilt≥4° 3. 헤더필드는 생존(48~58%)—전처리 실패는 **표(품목행)만** 날림. 셀 회수상한 ~5,513셀=**+0.72pp**(작음). 월분포 균일=상시잔차(스케일 신규갭 아님, 9k가 대표). 진짜붕괴 422장(normal기하 셀<15%)은 대부분 전처리 아닌 파서/인식.
- **★회전 66장 뿌리원인(원본이미지 직접확인+aspect-swap 기하테스트, 육안 3/3검증)**: **②오회전 53장(80%)=원본 완벽히 반듯한데 전처리가 90° 돌려 망침(env aspect swap) / ①놓침 13장(20%)=원본 누움을 못세움(aspect same)**. 즉 지배원인이 하드입력이 아니라 **정상문서를 깨는 버그**. 실사용자가 반듯한 송장 올려도 표 통째 날아감(사용자신뢰 임팩트, 지표임팩트는 0.28pp로 작아도).
- ⚠️ **이 062의 "upright 0/1678 오발동" 주장과 모순**(스케일서 오발동 발생). 원인=box-AR reverify 오탐의 스케일 회귀냐 다른 경로냐 **코드 미확인**(심볼=`_median_box_aspect`/`ORIENT_KOREAN_REVERIFY` in main.py). **증상만 엄밀검증**(env세로+aspect swap), 뿌리코드는 AWS측 확인 필요. deskew over-apply와 동형 "과적용" 의심.
- **위치=서버측 → 수정·검증 AWS 재run 필수**(로컬은 감지·특정까지). 측정스크립트 scratchpad(preproc_measure*.py·orient_split2.py). **당장은 룰/FT 먼저, 전처리 2차청소 라운드때 ②53장부터**(반듯문서 오회전 게이트 수정). "남은 39장"은 이 66에 흡수·확대된 셈. [[project_invoice_replay_itemname_analysis]] [[project_deskew_overapply_chain]]

## base 확정 + 워크플로우
- **룰 작업 base = run 062**(전처리+컬럼매칭, R1 미포함). BASELINE_MATRIX Paddle=062 자동반영(재생성함). R1은 base 아니라 첫 룰(base 대비 델타로 측정). [[project_baseline_matrix_stages]] [[project_invoice_rule_work_priorities]]
- **룰 작업=로컬**: 062 스냅샷(전처리 baked-in, 로컬 2000장)에 replay로 파서 재실행. AWS 재run 불요. AWS는 룰 묶음 최종확인/전처리·OCR 변경시만. [[project_ocr_snapshot_replay]] [[feedback_local_cpu_vs_gpu_prod]]
