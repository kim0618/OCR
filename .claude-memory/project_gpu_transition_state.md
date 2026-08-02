---
name: project_gpu_transition_state
description: GPU 전환 운영상태 + 첫 GPU run(035) 결과 + 다음 분석(드리프트냐 진짜 하락이냐). GPU 이후 뭘 봐야 하는지
metadata: 
  node_type: memory
  type: project
  originSessionId: 2760a9ad-7e14-435b-b20f-db7b97d95547
---

2026-06-16 GPU 전환 완료·첫 run 돌림. AWS g4dn.xlarge(T4)에서 server_det 가동.

**운영 컨벤션 (2026-06-16 갱신 — sed 방식 폐기, runtime_config 분리):**
- **main 브랜치 = source of truth**. repo `ocr-server/runtime_config.py` 커밋값 = **로컬 cpu 기준**.
- **sed 폐기.** cpu/gpu 차이는 `runtime_config.py` 4개 값으로 일원화: `DEVICE`(cpu/gpu), `DET_MODEL`(mobile_det/server_det), `INVOICE_OCR_MAX_W`(950/2000), `DET_LIMIT_SIDE_LEN`(960/2000). main.py는 `import runtime_config as RT`로 읽음 → **로직 단일소스, drift 없음**. rec은 양쪽 mobile 유지(한국어 server rec 없음).
- 배포(AWS GPU): main pull → `cp runtime_config.gpu.py runtime_config.py` → 실행. (gpu값 템플릿 = `runtime_config.gpu.py`, 커밋됨)
- **AWS→로컬 push 시 `runtime_config.py` 제외**(`git reset ocr-server/runtime_config.py`) — 구 main.py 통째 제외 규칙 대체. main.py는 이제 device-무관이라 양방향 안전.
- `main_local.py` = config-split 직전 **CPU main.py 동결 스냅샷**(비상 폴백, 유지보수 안 함 — 살아있는 로컬경로는 main.py+runtime_config.py cpu값). 백업: `backup/main_*_before_runtime_config_split.py`.
- 분석은 결과(runs/)+스냅샷 replay로 — replay_free는 추출기 직접호출(서버·device 무관). [[project_ocr_snapshot_replay]]

**GPU 작업 우선순위 (2026-06-16 확정):** P0 고해상 OCR(코드완료=ocr_max_w·det_limit 2000, INVOICE_OCR_MAX_W 게이트) → P1 orientation 4방향(force_full_eval) → P2 perspective 워프 → P3 W4 측정 재캘리브+게이트보강 → P4 스케일(실데이터)+DB. 큰 버킷순(recognition195>variant134), 한 번에 한 변수, 게이트=재실행 측정. [[project_cpu_phase_exhausted]] [[project_learn_loop_audit]]

**AWS 학습 실행 SOP (사용자 절차):**
1. `~/OCR/start-all.sh` — 백엔드/프론트(tmux). `~/OCR/logs/backend.log`에 `Engine warmed up` 확인.
2. `tmux new -s eval` → 안에서 `~/OCR/run-eval.sh` 실행
3. **나오기 = `Ctrl+B` 떼고 `D`** (detach, 계속 돎). ⚠️ `Ctrl+D`는 종료(사라짐)니 금지.
4. 다시 확인 = `tmux attach -t eval` 또는 `tail -f ~/OCR/logs/eval.log`. 끝 = `전체 GO ... checker PASS` + `학습 끝`.
- run-eval.sh = `stdbuf -oL -eL python -u eval/run_all.py --all 2>&1 | tee -a ~/OCR/logs/eval.log` (버퍼 꺼야 라이브 로그 나옴). repo에 커밋됨.

**round-trip 루프 (받아서 수정하는 과정):**
```
[AWS]  start-all → tmux run-eval.sh → 결과 push (⚠️ runtime_config.py 제외!)
        git add -A; git reset ocr-server/runtime_config.py; git commit; git push origin main
[로컬]  git pull → runs/<ts>+스냅샷 받음 → 내가 replay_free로 분석/파서수정 → 검증 → push
[AWS]  git pull → 다시 run-eval.sh
```
- **push 제외 대상 = `runtime_config.py` 뿐**(cpu/gpu 분기 단일 격리 파일). **main.py 는 제외 아님**(2026-07-14 확정, 사용자 지시). main.py 는 `RT.DEVICE` 참조만 하는 device-무관이라 양방향 정상 push/pull. 구 "main.py 통째 제외"는 폐기됨.
- **pull 막힘 주의**: 로컬에 동명 untracked 파일 있으면 pull 중단됨(예: run-eval.sh). `rm`/`mv` 후 pull. (035 때 실제 발생.)

**첫 GPU run 035 (2026-06-16, server_det) — study가 CPU(034) 대비 하락:**
- 필드 micro 63.1→**59.8%** (macro 61.8→61.4 거의 평), 셀 micro 74.3→**52.1%** (macro 41.5→32.0). 셀 하락 큼.
- thin은 67.6/72.1·89.5/82.4 (모형이라 의미 적음, [[project_learn_loop_audit]] C1).

**035 하락 분류 완료(replay 034/035, 둘다 FAITHFUL):** 파서 무죄, 하락은 전부 OCR envelope. W4 아님(글자 자체 오인식=실제 하락). 1-1/1-2 행 28→27 병합.

**036(2026-06-16, server_det + 고해상 2000px) — P0 가설 실패 + 새 회귀:** 필드 50.8%(63.1→59.8→50.8 단계마다 악화), 셀 51.7%. 전수분해 결론:
- **고해상은 원인 아님(반증):** 1-1/1-2가 2000px에도 rows 27 병합 유지·recog 167→148/98→97 거의 불변·cell 10→12/45→47. 라인수 256→254 불변(server_det 분할이 해상도 비민감).
- **고해상이 새 회귀 유발:** 단일행 문서 과분할(phantom rows) — 4.pdf/4-1 rows 1/1→1/3, 6.pdf 6/6→6/1, 5.pdf 6/7→6/9. 구조오류 162→207→240.
- **진짜 범인 = server_det(해상도 무관).** 같은 950px서 det만 바꾼 결과: mobile_det@950(034) 1-1 cell78%·rows28/28·recog35 ✅ vs server_det@950(035)·@2000(036) cell10~12%·rows27·recog148~167 ❌. server_det가 dense 28행 한국어표 병합·오인식, 해상도로 안 풀림.

**결론·조치:** server_det·고해상 둘 다 **롤백**(`runtime_config.gpu.py` = mobile_det/950/960, DEVICE만 gpu). **GPU는 속도 전용**(server_det 아님) — orientation 4방향·워프를 CPU 타임아웃 없이 돌리는 게 본 가치.
**038(2026-06-16, GPU+mobile/950 클린 A/B) — server_det 범인 확정 + GPU 베이스 클린:**
- 셀 51.7→**73.3%**(034의 74.3 복귀), recog 379→198, 1-1 cell 12→**77%**·recog148→32·rows27→**28/28** 완전복구. → server_det가 dense 28행 표 파괴 확정, 해상도 무관(반증).
- 잔여: 필드 63.1→**59.8%**(3.3pp 갭) + free 6→5. **원인=4-1.jpg 1장**(single-row 각도사진, GPU서 검출 과분할 1/1→1/3 → free게이트 탈락→fallback). GPU float 경계플립, 어려운 1건일 뿐 체계적 회귀 아님(P1/P2가 고칠 각도사진).
- ⚠️ 설정 반영 함정: `runtime_config.py` 덮어쓰기 **+ 서버 재기동** 둘 다 해야 det 모델 바뀜(037은 미반영 재실행이라 036과 동일했음). 스냅샷 `image_size`(950 vs 2000)로 반영여부 즉시 확인.

**확정 베이스라인 = GPU + mobile_det/950 (DEVICE만 gpu), 셀 73.3%.** server_det 보류.

**전처리 실험 2건 모두 net-negative → 롤백 (둘 다 runtime_config 플래그로 토글, 코드 보존):**
- **P1 orientation 무조건 4방향+512 (039, `ORIENT_FULL_4WAY_512`):** 셀 73.3→**44.7%**. early-stop이 *맞던* 방향을 512 스코어러가 재채점→틀린 방향 채택. 1.jpg 0°→90°(셀90→1), 1-2 90°→180°(84→0) 큰표 오회전. 6-2/6-3(작은표)는 살렸으나 큰표 손실이 압도. '확신하며 맞음'vs'틀림' 구분불가 → brute 4방향=틀린 도구.
- **P3 이미지 텍스트투영 deskew (040, `IMAGE_TEXT_DESKEW_PROJECTION`):** 셀 73.3→**68.4%**. 진짜기운 4-1(7°,+20)·5-3(+3)은 살렸으나, **투영 프로파일이 dense 28행표 행주기성에 락온→1-1 가짜 -3.5°**(P0 bbox는 0°)→straight표 회전해 77→44%. 투영=minAreaRect 테두리락온과 같은 실패계열. 자기검증(pre/post 같은 방법)이 못 막음.

**핵심 교훈:** 035~040 전처리 변경 전부 회귀 — **공통 원인 = blunt 변경이 dense 1-series(고채점칸·고가치)를 sparse보다 더 망침.** tilt 레버 자체는 진짜(P0: |tilt|≥1° 셀10% vs <1% 69%, 4-1 보정 시 +20 입증). **유일한 신뢰 각도소스 = OCR 텍스트라인 bbox**(P0가 쓴 것; dense=0° 정확, 4-1=7° 정확). 투영(pre-OCR)은 dense표서 못 믿음.
**P3'(041, bbox 기반 deskew+재OCR, `IMAGE_BBOX_DESKEW_REOCR=True`) — 첫 net-positive, 커밋:**
- 셀 73.3→**74.7%**, 필드 59.8→**61.9%**, 변주 69.3→**71.0%**, structure 173→**149**, **base 85.0% 불변**.
- 작동: 진짜 기운 5-1(-13.8°) 17→**53%**(+37)·3-3(8.7°) 0→12 보정. **dense 1-series(0.0°)는 스킵→불변**(040 투영이 1-1 망친 것과 정반대). 개선2/회귀1(6-1 -8). 신뢰 각도소스(bbox)가 정답.
- 구현: `main.py` 1차 OCR 후 `_median_textline_angle(ocr_lines_raw)` → 1.5~15° 이면 doc_deskewed 회전+재OCR, 잔여각↓·라인 안무너질때만 채택. invoice+image+flag 전용.
- **측정 사각:** `bbox_deskew` 메타를 timings 에 넣었는데 eval 샘플이 timings 미저장 → 장별 발동여부 안 보임. preprocess 디버그로 옮기면 보임(다음).
- 남은 손실: 큰 tilt 4-2(-35.7°)=P3' 정상 스킵→**P2 워프** 몫. 중간 tilt 안 살아난 것(4-1/3-2/6-3/7-3)=가드 과엄격 or 인식바운드(측정 후 판단).

**P1(044, orientation Korean-reverify, `ORIENT_KOREAN_REVERIFY=True`) — 두번째 net-positive, 커밋:**
- 필드 61.9→**65.2%**(+3.3), 셀·base 무회귀, 회귀 0장.
- 신호: orientation confidence는 '확신하며 틀림'(6-2: 0°강하게 택했으나 텍스트 거꾸로) 못 거름. **출력 한글다움(KR ratio)이 신뢰 신호** — garbage(<0.10)면 4방향 재OCR해 한글 최다 채택. 6-2(KR 0.009→0.396, pick90)·6-3(0.0→0.395, pick180)만 발동, 깨끗한 장(1.jpg KR0.22, 6-1 0.41)은 스킵=039 회귀 회피.
- 결과: 6-2/6-3 **필드 0→80%**(예측 60 초과), 셀도 6-2 40%·6-3 38%(rows 6/6) 회복(파서바운드 예측 일부 빗나감). 6-1만 0%(특유 transposed 레이아웃=파서, 별개).
- 구현: `main.py` 1차 OCR 후 `_korean_char_count` → garbage면 `_prep_and_ocr_lines`로 90/180/270 재OCR, 한글 2배+ & 20자+ 일때만 채택. bbox-deskew 앞에 배치(orientation 상류).

**해상도 재확정(048, mobile_det@1400, net-negative 롤백):** 작은글자 사진은 살리나(4-1 0→**60%**, 측정 8px→950서 2.5px 뭉갬 가설 입증) dense 28행표 파괴(1-1 77→**12%**, 행28→27). **mobile_det@1400도 1-1 붕괴 = 036의 dense표 파괴는 server_det 탓 아닌 해상도 자체 확정.** 950=dense표 sweet spot. **글로벌 해상도 死, 남은 레버=텍스트크기 적응형뿐**(작은글자 sparse→고해상, 큰글자 dense→950; 텍스트높이가 1-series 28px vs 4-series 8px로 자연 분리).

**전처리 잔여 진단(045 전수, OCR신뢰도 기준):** 저성능 15장 중 **저신뢰(품질저하)=4장뿐**(4-1/4-3/4.pdf/3-2, medConf0.86~0.92). 나머지 11장 고신뢰(0.98~0.99)=전처리 무관(모델/파서). 저신뢰 4장 결함=작은글자(4-3/3-2 8px)+블러(4-1). **즉 전처리 남은 건 적응형 해상도(작은글자 2~3장)뿐.** 

**누적: 038(59.8/73.3) → 044(65.2/74.3) → 047(65.6/74.5), 회귀0.** 전처리 클린 win 2개(P3' deskew, P1 orient). **money-col snap(046)은 5-2가 legacy_text_items 경로라 미발동(헤더-경계 경로에 넣음)=파서 다중경로 문제, foundation작업.**

**조건부 UVDoc(050, `DOC_UNWARPING_GATED`, dual-pass 신뢰도게이트) — keep(안전한 스케일 안전망):** 펴서 재OCR→원본보다 median conf 높을때만(+0.01) 채택. 휜 4-1 0→80(applied), 평평한 5.pdf 97유지(not applied)=clean 무회귀(049 전역이 5.pdf 97→0 파괴한 걸 게이트가 막음). **24장 수익 작음(휜게 4-1 1장, 셀+0.2 필드-1.3) 가치는 스케일.** 전역 `DOC_UNWARPING`=False(엔진flag), 조건부는 standalone `TextImageUnwarping`+per-image. [[feedback_eval_loop_probe_not_perfect]]
**textline orientation(051, net-negative 死):** 줄단위 180° 분류기가 정상줄 오판·뒤집어 파괴(1.jpg 90→34, base 84→41). P1 문서단위와 중복+오판. 롤백.

**GPU 전처리 레버 전수 소진(2026-06-17):** KEEP=P3'deskew·P1 orient·조건부UVDoc. 死=server_det·고해상(글로벌)·brute4way512·투영deskew·textline orient·전역UVDoc. **남은 셀손실=파서(다중경로 legacy_text_items 컬럼배정)+모델(고신뢰 오류). 전처리 아님.** 전처리는 실질 종료.
**전처리 어젠다 실질 종료:** ①orientation=targeted 완료, ②워프=4-1 풀프레임이라 저수익(미착수), ③고해상=死. 남은 셀 binding = **파서(structure 139, 6-1 transposed·photo 레이아웃) + 인식(209, OCR/GPU)** = parser-branching(보류)+실데이터(P5). ⚠️ [[feedback_eval_loop_probe_not_perfect]]: 24장 over-tune 경계 — **P-D(실데이터) 전환 권장.** [[feedback_local_cpu_vs_gpu_prod]] [[feedback_no_speculation_use_run_data]] [[project_cpu_phase_exhausted]] [[project_preprocess_image_deskew_gap]]
