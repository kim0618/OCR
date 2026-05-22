---
name: aws-local-divergence-demo-prep
description: 2026-05-21 ~ 1차 발표 종료 기간 AWS와 로컬 분리 운영 정책. AWS 직접 수정 사항은 로컬에 자동 반영하지 않음.
metadata: 
  node_type: memory
  type: project
  originSessionId: 3d564606-0439-4504-ac81-66a37391c611
---

1차 발표 (다음 주) 준비 기간 동안 사용자는 **AWS 인스턴스에서 직접 코드/설정을 수정**하며, 그 변경사항은 **로컬 repo에 자동 반영하지 않는다**. 발표 종료 후 별도 sync 작업 예정.

**Why:** 발표 일정 압축. AWS에서 빠르게 iteration하면서 로컬과 sync 비용 줄이기 위함. 사용자가 명시적으로 "커밋 안 함" 선언.

**How to apply:**
- AWS 변경 (uvicorn 설정, requirements 추가 설치, 임시 코드 패치 등)은 로컬 상태와 별개로 가정
- 로컬에서 코드 보고 "이거 AWS에 반영해야 함" 같은 제안 자제
- AWS 작업 결과를 로컬에 자동 commit/push 제안 하지 않음 (사용자가 명시 요청 시에만)
- 발표 종료 후 사용자가 "이제 sync 작업하자" 시그널 줄 것

**Related state (2026-05-21 기준):**
- AWS 인스턴스: `i-0ac34c3757dae05a2` (g4dn.xlarge, ap-northeast-2)
- 퍼블릭 IP: 54.180.124.22 (변경 가능 — 인스턴스 stop/start 시 바뀜)
- 로컬 repo 상태: `requirements.txt` 109줄로 업데이트됨 + `requirements-aws.txt` 신규 생성 — **미커밋**
- AWS repo 상태: git HEAD `d38eaf6` 클론. 로컬의 위 두 파일 변경사항은 AWS에 아직 없음 (heredoc으로 별도 생성됨)

[[ocr-servers]] [[aws-setup-decision]]
