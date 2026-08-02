---
name: project_orient_conf_pin
description: "오회전 근본수리(2026-08-02) — 방향 판정이 서빙 rec conf 의존이라 FT 교체마다 경계선 문서 뒤집힘(실측 확증). get_orient_engine(official 고정)으로 판정/인식 분리, git 배포 완료. 다음=072 official 파리티(~$3.3)로 net≈0 확인 후 새 기준선"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2e1f577d-86f6-46fb-9df5-0322285bdea5
  modified: 2026-08-02T09:11:56.955Z
---

2026-08-02. clean4 E2E 손실의 25%(오회전 267장 −7.6k, [[project_ft_seen_unseen_bench]])를 만든 파이프라인 결함 수리.

## 원인 확증 (재검증 3종, 전수 실측 — 추측 아님)
- 모델 의존 지점 2곳: ①`detect_orientation`(preprocess.py) — 회전본을 **라이브 rec**으로 채점(`score=(한글×1.2+숫자×0.9)×(0.8+avg_conf)+줄수×0.8` + avg_conf 문턱 다수) ②`ORIENT_KOREAN_REVERIFY`(main.py) — 한글비율 트리거·후보 채점·**채택 시 그 OCR을 최종 인식으로 재사용**까지 라이브 rec.
- **모든 rec 교체가 기하 판정을 흔듦**: official 대비 V1 165 / 004 169 / clean4 267장, FT끼리도 226~304장 (snapshots image_size 쌍별 대조).
- **결정타 = 겹침 검정**: 뒤집힘 집합 겹침 82/64/54장 vs 랜덤 기대 3~5장(**13~16배**) = 같은 경계선 문서가 모델 점수 따라 반복 뒤집힘.
- 방향성: 뒤집힌 267장 한글 인식 우세 official 47 : clean4 **0** — FT 뒤집기가 이득인 경우 전무.

## 수리 설계 = "판정은 고정 모델, 인식은 라이브 모델"
- **`get_orient_engine()`** 신설(main.py ~1200): rec=official **고정**(adopted 스왑 미적용) lazy 싱글턴. GPU +~1GB.
- `detect_orientation` 호출 3곳(2615/2621/2625) → 고정 엔진으로 판정. 최종 인식은 기존대로 라이브.
- REVERIFY(2929~): rot0 기준선+후보 전부 고정 엔진(같은 저울), **회전 채택 시 최종 인식만 라이브 엔진 1회 재-OCR**(FT 이득 보존). 트리거는 라이브 유지(조사 개시일 뿐).
- official 운영 중엔 고정==라이브라 동작 변화 사실상 0 = 회귀 리스크 최소. 마커 `ORIENT-PIN` 4곳.

## 배포 (git 파이프, 2026-08-02)
- 커밋 `e2af3a5ea` push → AWS pull 완료. 검증: 마커 4/4·호출 4곳·py_compile 통과.
- ★교훈: 처음 "커밋 안 됨" = **패치를 레포 밖(C:\OCR\aws_patch_orientation)에 만들어서** 워킹트리 clean → nothing to commit. **이 PC에도 레포 있음 = `C:\OCR\OCR`** (origin kim0618/OCR, d:\Free_Vue 아님). 작업 산출물은 레포 안에 만들 것.
- 롤백: AWS `git revert e2af3a5ea` 또는 로컬 main.py.orig(C:\OCR\aws_patch_orientation).

## 다음 = 072 official 파리티 런 (실행 대기)
1. `bash ~/OCR/restart-all.sh` → 스모크: 로그 `[ocr] orient engine = official ... (pinned)` 확인
2. `tmux new -s eval` → `bash ~/OCR/run-eval.sh` (~3h, ~$3.3)
3. **게이트: 072 vs 071 net ≈ 0(노이즈)** — 통과 시 **072 = 수리된 파이프라인의 영구 새 기준선**(메모리 규칙: 환경 변경 시 기준선 재측정). 이후 clean5 E2E는 오회전 교란 없이 판정.
4. 그 다음 트랙 = 수확 정렬 픽스 → clean5 ([[project_ft_seen_unseen_bench]] 로드맵).

[[project_ft_seen_unseen_bench]] [[project_preprocess_orientation_fix]] [[feedback_git_as_transport]]
