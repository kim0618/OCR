---
name: project-invoice-numeric-rules-p1p2p3
description: "금액·수량·단가 룰 트랙 완주 — P1 열복구·P2 산술fill·P3 geometry 재구성 채택(구조룰 게이트 재정의), 기각된 접근 목록 포함"
metadata: 
  node_type: memory
  type: project
  originSessionId: a2b7872e-991d-42d1-a975-6de0493723a9
---

2026-07-14~15 확정. 측정 base = 066 thin live compare(5,964장) + replay(P1~P3는 replay_compare.py 미러, `--skip-upa`로 일괄 off).

**★트랙 마감(2026-07-15)**: 7층 완성 + **커밋 `9bfe304e6`**(4파일: invoice_statement_free/main.py/replay_compare/replay_gate_diff — 이전 세션 jamo V5·매칭 미커밋분 동반 탑재). push·AWS pull·재시작=사용자. **최종: 금액 68.4%·수량 64.4%·단가 59.7%** (시작 58.8/48.7/46.3), 셀 44.6→49.0%(+15,413), spurious 0·study 0·master +131. 잔여깔때기 확정: 회색 52~56%(목표밖)·룰잔여 ~3,600/컬럼(안전앵커 무 — 부분트리플/모호/중복가드, 전부 정밀도 50~60% 함정 실측)·recognition(금액1,456/수량2,323/단가3,520)=FT몫. **다음 레버=FT뿐이나 사용자가 FT 보류 결정(2026-07-15 "굳이 할필요없을듯")** — 재개 시 build_dataset.py 재실행+cropReady 재산출(7층 반영) 선행. 주의: main.py 커밋됨 — AWS gpu sed 충돌 시 stash→pull→sed 재적용. 변경 4파일 = extractors/invoice_statement_free.py(+P1/P2/P3 함수), main.py(합류점 3블록: P1→P2→P3 순서 필수 — P1이 채운 단가를 P2가 쓰고 P3 정체앵커로 씀), eval/replay_compare.py(미러+토글), eval/replay_gate_diff.py(신규 행단위 게이트 도구). 백업 3세트 backup/*_before_p1_unitprice_recover.*, *_before_p3_geom_recon.*.

**채택 룰 3개 (모두 free+fallback 합류점, 경로무관, 덮어쓰기 없음):**
- **P1 recover_unitprice_amount_columns**: 단가값이 금액칸에 착지한 오배치 재배정(A) + 단가 빈칸 나눗셈fill(C). 핵심가드 = 행 정체성(_rawText 토큰↔OCR밴드 중첩 유일최대). 전수검증 회귀0·spurious0, 정밀도 88~98%, +~750셀.
- **P2 fill_arith_empty_amount**: 빈 금액 = 수량×단가, 그 값이 행 _rawText에 money 토큰으로 실재할 때만. fired 163, 회귀0(1건은 검증스크립트 조인 아티팩트로 판명). WRONG-overwrite 갈래는 정밀도 53%·회귀77로 폐기.
- **수량L1 `fill_arith_empty_quantity`** (2026-07-15): 빈 수량=금액÷단가(정수 1..9999만). 드라이런=프로덕션 동조건: 발화 761·정밀도 92.2%·회귀 0·spurious 0. **덮기 변형 기각**(73.3%·회귀 760 — 할인행서 나눗셈 정수가 우연 성립). 역방향(단가=금액÷수량)도 **기각**(19.0% — 나누는 쪽 수량이 짧고 불신).
- **수량L2' `fix_swapped_qty_unitprice`** (2026-07-15): 수량칸↔단가칸 통째 스왑 복원. 게이트=모양(수량칸 money꼴+단가칸 소형정수 비콤마)+금액존재+**산술 불성립**(성립 행은 교환법칙상 방향판정 불가·실측 55.8%라 불가침). 발화 1,134·both OK 86.5%(수량 88.8/단가 94.1)·회귀 27=75:1·spurious 0. 체인 위치: geo 뒤·L1 앞. **스왑+나눗셈유도(u'=a/q) 변형은 기각**(6~64%·회귀 794).
- **문서합 오라클(Σ행금액=합계금액) 기각**: GT 자기일관 29.2%뿐(합계=부가세포함 관행), 유일차액복구 62%·물량 130.
- **트리플 스캔 `_geo_triple_scan` (2026-07-15, 사용자 "확실해?" 재반박으로 발견)**: y-밴드별 유일 산술 트리플(q×u=a, q≥2) 스캔 — **열배정·x클러스터 불요**(기울어진 문서 면역), 병합토큰 내부 money findall, 글자붙은 숫자(625mg) 경계가드, 거울쌍 (a,{q,u}) 정규화, 요약행 skip. 병합: 값앵커(수량+단가 or 단가유일)=강→F4b 금액가드 덮기 / 이름앵커=약→빈칸만 / append(금액·품명 중복금지). reconstruct_numeric_columns 3개 반환경로 전부 경유(배정실패 문서 포함). 상한실측 1,886셀(배정성공 1,444+실패 442, 모호 9~11% skip). 검증: 증분 net +1,107(금액+557)·회귀+105 = 10.5:1·spurious 0. **교훈: "F2=값오독=룰불가" 단정은 x-격자 기준이었을 뿐 — 산술 자가결정은 격자 없이 성립.**
- **F4b (P3 내부 확장, 2026-07-15)**: 강한 바인딩(값일치 유일 앵커) 행에서 geo행 산술성립 시 **오값도 덮음**(빈칸만이 아니라). 헤드룸 6,734 중 geo가 이미 amount열에 정답 잡은 2,603(=R2) 회수. 감사: 수량 43:1·단가 21:1 무가드 안전, **금액은 4.5:1(회귀55=비-곱행 할인함정)** → **금액 가드**: 현재값==단가(침범) OR 곱의<0.45배(쓰레기)일 때만 덮고 0.45~1.02배(할인가능대)는 보호. 가드 후 전수검증(4,909문서): net +6,487·spurious0·수량+2,412(13.6:1)·단가+2,298(15.4:1)·금액+1,799(10.2:1). 신뢰-렌즈 원칙을 코드로 강제(산술이 정답 아닌 amount 구간 불가침).
- **P3 reconstruct_numeric_columns**: 붕괴문서(수량·단가·금액 3열 동반결함 11,302행) geometry 재구성 — 행=money y-클러스터, 열=숫자 x-클러스터, 열정체=헤더토큰(V2)→산술투표(V1, ≥2행). 병합=값일치(유일값만)→품명→rawText-y(토큰3+) 3패스 바인딩 후 빈칸 fill(geo행 산술성립 필수) + 미바인딩 산술성립행 append(금액중복·품명중복 시 금지). v3 최종: **net +5,111 (단가+2,050 수량+1,772 금액+1,366), 회귀 508, spurious 0, 11:1.**

**★게이트 재정의 결정(사용자 채택, 2026-07-15)**: §3 "숫자열 회귀 0"은 셀단위 룰용. **구조 룰(행 채움/추가)은 정렬 재편성 때문에 문자 그대로 0 불가능** — 게이트 = "컬럼별 net>0 + spurious 0 + study 회귀 0 + master net≥0"으로. 조임 3라운드(2,023→755→508)에서 net −2,066 깎이며 수확체감 실증.

**기각된 접근 (재론 금지, 전부 066 실측):**
- free 게이트 일괄 완화: 숫자 −532·전체 −1,475 (063 "78% 탈락" 진단 반증)
- 행별 밴드 산술 트리플: 발화 7%·정답 49% (GT 산술성립 57.8% 천장)
- 열좌표 자기학습: amount 정밀도 19.6% (붕괴문서는 학습원천도 오염 — 순환)
- HA append 가드 완화(lost 625): 회수 ~110뿐, 차단된 HA셀 79% 쓰레기 — 기존 가드가 옳음
- V3 순서/타입 휴리스틱 열배정: V1 일치 40%
- per-doc A/B 셀렉터: 최선 +195/500docs, but 악화문서 20 동반(오라클 상한 +830의 24%) — 보류

**남은 레버**: ① MISSING 중 HA게이트실패+품명있음 1,879(reason: append_gate 883/too_few_rows 828/no_header 779) = HA 알고리즘 개선(중형) ② recognition-bound(붕괴의 ~35%: 품명이 OCR에 없는 행 2,229 등) = 재OCR/FT 몫 ③ fallback 라인조립(E5: MATCHED 붕괴행의 64%는 금액이 rawText 밖) = 파서 본체 수술.

다음 = 사용자 표준 루프(replay_compare→parser_drop_classify, study+thin)로 공식 수치 확정 → study 회귀·master net 게이트 최종 확인 → AWS 배포(git). 관련: [[project_invoice_066_master_reprioritization]] [[project_invoice_rule_work_priorities]]
