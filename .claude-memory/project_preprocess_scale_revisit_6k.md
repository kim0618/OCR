---
name: project_preprocess_scale_revisit_6k
description: "6천장(066) 전처리 재방문 — orientation 유지, deskew 752장 갭(+0.74pp), 32장 하드"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5ccf9062-7163-4183-9557-11f591e33402
---

2026-07-10 run 066(6천장) 전처리 × 셀정확도 전수분석 (샘플 preprocess 텔레메트리 + compare 셀acc 조인). 메모리 [[project_preprocess_orientation_fix]]가 "스케일서 갭시 재방문" 남겨둔 것 실행.

**① orientation = 능동 갭 아님(스케일 유지 확인):** 미적용(0°) 5269장 44.1% / 90°적용 307장 52.1%(오히려↑) / 180° 120장 44.7% / 270° 268장 42.0%(-2pp 경미). 062 box-AR reverify가 6천장서도 일반화. 회전보정 정상.

**② ★deskew = 진짜 스케일 갭:** 적용 752장 **전부 측정각 <0.5°인데 cellAcc 39.4% vs 미적용 45.3% (-5.9pp)**. 근본원인=[[project_preprocess_image_deskew_gap]]의 "각도검출이 표테두리 락온→기울어진 사진을 ~0°로 오판→미보정 잔존". PDF는 3O정책(abs≤2° skip)으로 고쳤으나 **이미지 경로 미수정**이라 스케일서 752장 노출. **상한=752장 45.3% 회복시 +0.74pp overall cell.** 대응=이미지 각도검출 보강(테두리 락온 회피) or 이미지에도 skip정책.

**③ 32장 near-total 실패(0.5%):** acc<8%+표1행만 = 사실상 전멸. orient미적용/free 18 + orient적용/fallback 8 등. 메모리 "남은 39장(15누움+24기울기)"이 6천장서 ~32장 재확인. 잔여 하드(사진기울기/품질), 후순위.

**⚠️ 검증제약:** 전처리는 서버측 재-OCR이라 **로컬 replay 검증 불가**(replay는 이미 전처리된 OCR 재사용). deskew 정책변경은 **AWS 재run으로만 측정**(로컬=CPU). 위는 진단·상한, fix효과는 AWS 실험 몫. **다음=deskew 이미지 각도검출 보강 준비→AWS 실험(+0.74pp 상한 검증), 32장 후순위.**
