---
name: aws-setup-decision
description: AWS PoC/데모 환경 구성 결정 사항. g4dn.xlarge GPU + Deep Learning AMI + 최소→최적 점진 확장 방식. 2026-05-21 합의.
metadata: 
  node_type: memory
  type: project
  originSessionId: c63e45b4-2887-4282-8ac0-40829e956791
---

OCR 제품의 AWS 데모/PoC 환경 구성 결정. 2026-05-21 결정. 합의된 접근은 **"최소 셋팅으로 시작 + 트리거별 무중단 추가"**.

## 최소 셋팅 (PoC 시작점)

| 항목 | 값 |
|---|---|
| 인스턴스 | g4dn.xlarge (T4 16GB / 4 vCPU / 16GB RAM) |
| 리전 | ap-northeast-2 (서울) |
| AMI | AWS Deep Learning Base GPU AMI (Ubuntu 22.04) |
| EBS | gp3 50 GB |
| Elastic IP | ❌ |
| HTTPS/nginx | ❌ (HTTP 직접 노출) |
| 보안그룹 | 22 (SSH 내IP) + 8089/9099 (전체) |
| 월 비용 | 데모 50h ≈ $43–50, 평일 8h×22 ≈ $125 |

## 최적 셋팅 (운영 수준)

| 항목 | 값 |
|---|---|
| 인스턴스 | g4dn.xlarge → 트래픽 늘면 g4dn.2xlarge 업스케일 |
| EBS | gp3 80 GB |
| Elastic IP | ✅ |
| HTTPS | ✅ nginx + Let's Encrypt + certbot |
| 보안그룹 | 22 + 80/443 (백엔드 포트 직접 노출 X) |
| 프로세스 관리 | systemd 2개 (FastAPI 9099 + Next.js 8089), --workers 1 |
| 로그 회전 | logrotate |
| 모니터링 | CloudWatch Agent |
| 비용 최적화 | 1년 RI 또는 EventBridge stop 스케줄 |
| 월 비용 | 24/7 온디맨드 ≈ $495 / 1년 RI ≈ $305 |

## 코드 변경 (공통)

- `ocr-server/main.py:997-1011` `get_ocr_engine()`:
  - `device="cpu"` → `device="gpu"`
  - `text_recognition_batch_size=30` → `64` (T4 메모리 여유)
  - device 전환은 `.env` 의 `OCR_DEVICE=cpu|gpu` 로 분기 (env 방식 합의)
- `ocr-server/requirements.txt` 보강: `paddlepaddle-gpu`, `paddleocr`, `PyMuPDF` 명시

## 처음에 잡고 가야 마이그레이션 안 아픈 4가지

1. 리전 = 서울 (ap-northeast-2)
2. AMI = Deep Learning Base GPU AMI Ubuntu 22.04
3. venv 단일 환경 (시스템 Python 혼용 금지 — 로컬 9099 미스터리 재현 위험)
4. EBS = gp3 50 GB 이상 (gp3는 무중단 resize 가능)

## 점진 업그레이드 트리거

| 추가할 것 | 트리거 조건 |
|---|---|
| Elastic IP | 시연자에게 URL 미리 공유 필요 ($3.6/월) |
| systemd 서비스화 | reboot 시 자동 재기동 필요 |
| CloudWatch Agent | GPU util/메모리 실측이 영업 자료에 필요 |
| logrotate | review_log.jsonl 100MB 넘을 때 |
| EBS 100GB resize | disk 사용량 70% 넘을 때 (무중단) |
| warmup 옵션 A + batch_size 64 | 첫 요청 cold start 가 시연에 거슬릴 때 |
| g4dn.2xlarge 업스케일 | 동시 2건+ 처리 필요 |
| 1년 RI 전환 | 월 가동 400h 초과 (비용 분기점) |

## 권장 진행 순서

1. 로컬: `.env` + device 분기 코드 추가 (`OCR_DEVICE=cpu` 로 현재 동작 유지 확인)
2. 로컬: requirements.txt 정리 (현재 .venv 기준 pin 추출)
3. AWS: g4dn.xlarge 인스턴스 생성 (서울, Deep Learning AMI, gp3 50GB, 보안그룹 8089/9099)
4. AWS: 코드 배포 (git clone, .venv 재생성, npm install)
5. AWS: `nvidia-smi`, `paddle.utils.run_check()` 통과 → device="gpu" 전환
6. AWS: 단건 호출 검증 (거래명세서 1.jpg → 12–20초 응답 목표)
7. 시연자 IP 보안그룹 허용 → 데모

## SI 영업 자료화 (PoC 부산물)

g4dn.xlarge 측정 결과 = SI 고객사 온프레미스 사양 추천 reference benchmark.
- g4dn.xlarge (T4 16GB) 거래명세서 12–20초 → 동급: NVIDIA L4 24GB (신규) / T4 16GB (저가) / RTX A4000 16GB (워크스테이션)

관련: [[server-restart-command]] (포트 9099 운영), [[ocr-workspace-hygiene]] (배포 시 파일 위치 규약).
