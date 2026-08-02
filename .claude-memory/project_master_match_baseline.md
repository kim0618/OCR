---
name: project_master_match_baseline
description: 마스터매칭(약 이름 자동교정) baseline + 2026-07-06 심층 시뮬(우리 Paddle→매칭 top1 58/67, war 99.4) + value-add 로드맵(품명클린→랭킹→learndata부트스트랩→게이트→파인튜닝). 사업=파리티/비용플레이
metadata: 
  node_type: memory
  type: project
  originSessionId: 643d94e6-d9a2-497c-8aad-f5a1d285e5b7
---

2026-06-24. [[project_invoice_war_db_restored]]의 learndata(OCR원문→정답)로 **이미지 없이** 마스터매칭을 만들고 채점하는 중.

**baseline (learndata 300건, 생 트라이그램 SIMILARITY):** top-1 **40%**, top-3 69%, top-10 **89%**. → 인식이 아니라 **ranking 문제**(정답은 후보에 거의 있음, 1등을 못 고름). 순진한 보정 2개 실패: 규격꼬리 정제 −4pp(규격이 동명이품 구별신호라 떼면 손해), 단가-우선픽 −6pp(단가만은 너무 거침). **정답=유사도1차 + 보정된 단가/규격 2차 + learndata L_N 학습조회.** 24장으론 못 만듦(과적합), war 20만건이라야 튜닝 가능 — 이게 이미지-프리로 매칭을 만드는 이유.

**2층 구조:** 인식층(파인튜닝=rec모델 재학습, 손잡이 자동조정) vs 파서층(룰=코드). 마스터매칭=파서층. 마스터사전 런타임=정적 JSON(AWS 무DB), DB는 추출1회용. [[feedback_no_model_discussion]] 예외: 사용자가 파인튜닝 직접 요청함.

**작업 순서(합의):** 룰 → 마스터매칭 → 파인튜닝(마지막, 비싸니 잔여만). 이미지 도착 시 파이프라인: **측정 → 전처리 → 룰/마스터 → 파인튜닝**. 전처리는 교란변수라 맨앞(단 24장 작업 있으니 갭 뜰때만 재방문). 파인튜닝 코퍼스=live run만 적립, 학습은 앞단 다 고친 **클린 잔여**로([[project_ocr_snapshot_replay]] 흐름).

---
**★★ 2026-07-06 심층 매칭 시뮬(로컬 bjocr PG, 우리 062 Paddle 품명읽기 7,416행 → 마스터 38,848 trigram) ★★**
파서룰 phase 끝(cell 22.7%, [[project_invoice_rule_work_priorities]]) 후 **사업 관점 재정렬**. 매트릭스 순환제외(value-add)로 보면 품명 우리 9.9% vs war(구글 Document AI) 단계별 26.7→48.1→**99.4%**. **우리는 매칭을 아직 안 걸어서 raw OCR(9.9%) 고정**.
- **사업 본질 = 사람이 고치는 건 품명뿐**(war learndata 테이블 `tbl_ocr_learndata_invoice_modify` 유일, ocr_item_nm→user_item_cd, **214,891건**/고유읽기 75,332/코드 19,428, 품목당 평균 4.3변형). 공식 약품마스터 `tbl_ocr_master_item`=**38,848개**(표준코드 94%·보험코드 75%)도 **war DB에 이미 있음=우리가 가져온 것, 우리 고유무기 아님**. 접속: PG17 localhost, user postgres, pw root123, db bjocr, `"/c/Program Files/PostgreSQL/17/bin/psql.exe"`, PGCLIENTENCODING=LATIN1(일부 raw OCR 바이트 non-UTF8).
- **우리 자동매칭률(trigram, GiST `nm <-> read` KNN top-k, 정답=코드3종중일치 OR 정규화이름일치):** RAW blob top1 **57.8%**/top10 82 · **CLEAN(선행코드/제조사/행번호 제거·규격유지) top1 67.1%/top10 90.9** · GT완벽이름 top1 74.7/top10 97.3(상한). learndata EXACT는 우리읽기 기준 **18%뿐**(키=구글읽기라 우리 Paddle 읽기와 안 맞음→war 캐시 못 물려받음, 우리 것 새로 쌓아야).
- **격차 분해(→war 99.4):** 룰(품명클린)+9pp · **랭킹(top1→top10) +~20pp=최대레버**(정답 top10에 91% 있는데 1등 못고름, 동명이품 규격구별) · OCR파인튜닝 +8pp(캡슐→캡슬·실크론G→500G(JAR 글자오인식) · learndata플라이휠(본품목 EXACT)로 마지막.
- **★품명클린은 매칭 전처리(파서 아님)**: 우리 셀점수엔 무효(GT가 규격유지→cell dead end, 앞서 반증). 오직 매칭 입력 정규화용. 첫 클린 시도가 규격까지 벗겨 무효였고(58→58 오판), 규격유지 재측정서 +9pp 확인. 이미지 전처리(orientation, [[project_preprocess_orientation_fix]] 완료)와 **다른 단계**.
  - **⚠️2026-07-06 정정 — "셀엔 무효"는 좁은 뜻**: 클린 *문자열*을 `itemName` 셀에 그대로 표시하지 않는다는 뜻일 뿐, **작업 자체는 결국 셀에 반영됨**. 착지점 = **`itemNameMaster` 셀**(매칭결과=정식명). 경쟁사가 셀에 보여주는 것도 정식명(itemNameMaster). 연결: 읽기→[클린]매칭키→trigram+랭킹→정식명→itemNameMaster 셀 기록. **현재 우리 파서엔 마스터매칭 코드가 전무**(grep 확인: main.py/app에 itemNameMaster/trigram/learndata 산출 없음) → itemNameMaster는 GT에만, 우리출력은 미산출=전량 drop(thin 4,796). 그래서 셀 루프가 아직 안 움직임. 매칭단계 빌드+파서배선 후 그 컬럼이 움직임.
  - **★진행결정(사용자, 2026-07-06): 벤치 먼저 완성 후 배선.** 격리 벤치(매칭 top1)에서 clean+랭킹 튜닝 완성 → 그 뒤 파서에 배선해 itemNameMaster 셀 채움. 셀 루프 변화는 배선 후.
  - **★생산 모듈화 완료**: SQL-regex 프로토타입을 파이썬 `eval/item_name_clean.py`로 이관(`clean(name, level='strip')`, **규격보존 불변**). 하네스: `_gen_clean_variants.py`→`_match_clean.csv`, 채점=psql `data/invoice_war/_score_clean.sql`(3-코드 정답, 전체+오염행 층화). 접속: `-U postgres -d bjocr` pw root123, DB=UTF8(내 CSV도 UTF8, LATIN1 불요), `"C:\Program Files\PostgreSQL\17\bin\psql.exe"`. 로컬 프록시(`score_clean_local.py`)는 언더파워(2-코드)라 삭제.
  - **★★2026-07-06 전체 7416 psql 실측(authoritative) — 메모리 통념 정정★★**: raw top1 **61.2**/top10 87.2 · **strip(오염토큰만 제거·규격+제조사+이름 유지) top1 63.5(+2.3)/top10 90.5 — 채택** · core(제조사도 제거) 62.9 · form 62.6 · formbase 45.8(폐기) · **gt완벽 top1 70.1/top10 97.3**. **오염행(n=2870)**: raw 55.5→strip **61.6(+6.1)**/top10 81.1→89.5(+8.4). 
    - **정정①**: 이전 "CLEAN +9pp(58→67)" **재현 안 됨**. 진짜 클린 레버 = **+2.3 전체 / +6.1 오염행**(훨씬 작음). strip은 오염행 39%에 효과 집중.
    - **정정②**: "제조사 제거"가 승리 레시피라던 것 **틀림** — maker 남기는 strip > maker 떼는 core/form. 단순 룰(숫자/코드/날짜/금액 토큰만 제거)이 이김.
    - **정정③(핵심)**: **진짜 큰 레버는 클린이 아니라 랭킹.** top1 63.5인데 top10 90.5(정답 27pp가 2~10등). **GT완벽 이름도 top1 70.1뿐/top10 97.3** → 동명이품을 trigram이 1등 못 고름(규격·단가 tiebreak 필요=랭킹). 클린은 소폭 확정레버, 랭킹이 +20 대형레버(로드맵 ② 맞음). 클린 추가 튜닝은 수확체감 → strip 락 후 랭킹으로.

**★★2026-07-06 war 매칭 심층조사(ocr.xml+class+DB 코드로 확정)+우리 천장 실측★★**
- **war 캐스케이드**(mapper `ocr.xml` L400-470, `OcrServiceImpl.class`): ①`selectMasterItemLearnData`(learndata exact, learn_count≥3, match_type L_) → ②`selectMasterItemLike`(clean+공백strip LIKE substring, NM_L) → ③`selectMasterItemBestLike`(trigram KNN, SIMILAR). **모든 단계 tiebreak = SIMILARITY DESC → |bp1_amt−단가| ASC.** 임계값 없음=항상 top1=99%커버.
- **`fn_get_item_name_clean`(DB함수 실체) = 괄호안 제거(`\(.*\)`)만.** war 품명클린은 이게 전부(+공백제거). 우리 strip과 방향동일, war가 더 단순.
- **★가격 tiebreak=랭킹 그 자체(로컬 실측):** 품목 **62%가 동명이품**(이름동일·규격/가격/코드 상이). GT이름 기준 **itemCode top1: 유사도만 63.5%→+가격 87.9%(+24pp)**. 이게 로드맵 "②랭킹+20"의 정체. **단 itemNameMaster(이름)엔 가격효과 소폭**(동명이품 이름은 같아서 어느 팩이든 이름 맞음).
- **★우리 천장 실측(replay 우리읽기+단가, Jaccard프록시=실제보다 −5pp 보수적):** A.우리읽기+우리단가 itemNameMaster/code **82.9%** · C.GT이름+GT단가(천장) **92.9%**. → **매칭 붙이면 itemNameMaster ~10%(현재 무매칭)→~82%(즉시)→~93%(읽기개선 천장)→95~99%(learndata 부트스트랩)**. 전체셀=매칭정확도×읽은비율(못읽은행이 상한 깎음).
- **우리 실행계획:** war 캐스케이드 구조 그대로 복제가능(같은 master 38848 로컬 `master_dict.json`엔 bp1 포함, pg_trgm). 차이=learndata가 Google읽기로 키됨→우리Paddle과 18%만→우리것 부트스트랩 필요.

**★확정 로드맵(value-add 매칭, 사업본체):** ①품명 클린 전처리(매칭입력 정규화, +9) → ②랭킹 개선(최대레버, +20) → ③learndata 부트스트랩(과거 2000+장에 우리 OCR 돌려 우리읽기→정답코드 시딩=우리 플라이휠 콜드스타트 해소) → **🚦게이트: 자동매칭률 vs war 99.4 측정**(근접→비용/독립 파리티 사업 GO, 격차크면→④) → ④OCR 파인튜닝(천장상향). (옆)사업자번호 룰=독립·소폭·선택. 사업 = 구글 "이기기"가 아니라 **파리티+비용/데이터독립**(구글 페이지당요금 회피), 신규품목은 양쪽 다 사람 필요(learndata 플라이휠로만 축소). 단계마다 top1/top10 재측정. 시뮬 산출물=eval/data/invoice_war/_match_*.sql·csv(로컬 전용).

**★인계(2026-07-06, 새 채팅서 순서대로 착수) — 사용자 지시:**
- **파서룰 phase 끝**(cell 22.7%, 미커밋, [[project_invoice_rule_work_priorities]]). **AWS 런 지금 불필요**(replay=파서진실=GPU동일). AWS는 배포 시점에 파서+매칭 묶어 한 번(salvage main.py 배선 그때 실런검증).
- **다음 착수 = ①품명 클린 전처리부터 순서대로.** 품명클린=매칭입력 정규화(선행 코드/제조사/행번호 제거·규격유지), 셀점수엔 무효·매칭 top1 +9pp 전용. 로컬 062 replay 읽기 + bjocr DB로 진행(서버 불요).
- **⚠️ ②마스터 매칭 엔진(trigram/learndata 파이프라인·랭킹) 착수 전 반드시 사용자에게 알리고 확인받을 것.** 품명 클린(준비)까지 하고, 매칭 엔진 빌드 전 체크인.
