# OCR 프로젝트 운영 수준 완성도 진단 리포트

**작성일**: 2026-05-17  
**기준 작업**: T-23 이후 (preprocessing UI 포함)  
**작성 목적**: DB-2 작업 및 운영 전환 우선순위 결정  
**방법**: 코드 수정 없는 순수 분석

---

## 1. 생성 파일

- `mysuit-ocr/docs/ops/ocr_operational_readiness_assessment_20260517.md`
- `mysuit-ocr/docs/ops/ocr_operational_readiness_assessment_20260517.json`

---

## 2. 전체 결론

| 항목 | 평가 |
|---|---|
| **현재 운영 단계** | **Internal Alpha** — 개발자 로컬 + 제한 내부 사용 가능 |
| **전체 완성도** | **약 52%** (기능 구현은 ~72%, 운영 인프라는 ~30%) |
| **가능한 범위** | 로컬 개발 테스트, TestWorkspace 검증, 내부 invoice/receipt OCR 확인 |
| **불가능한 범위** | 다중 사용자, 유료 SaaS, 장기 History 보존, 사이트별 격리, 외부 고객 계정 관리 |
| **가장 큰 병목 3가지** | ① users.json 평문 비밀번호 (보안) ② localStorage 기반 저장 (데이터 지속성) ③ Site 격리 미구현 (멀티 테넌시) |
| **다음 최우선 작업** | DB-2 schema.sql → bcrypt 인증 → templates/history DB 전환 |

---

## 3. 영역별 완성도 점수

| 영역 | 점수 | 단계 | 근거 |
|---|---:|---|---|
| **OCR core accuracy** | 82 | Private Beta | docTypeMatch 80.7%, coreFieldFill 89.1%, 회귀 0건 |
| **invoice_statement** | 90 | MVP Production | rowCount 7/7 exact, OP-anchor, colGuides, E2E PASS |
| **receipt baseline** | 75 | Private Beta | T-16 baseline 개선, classification_mismatch 9→7 잔존 |
| **generalization** | 55 | Internal Alpha | 57개 샘플 기준, 새 샘플 일반화 검증 미완 |
| **preprocessing** | 72 | Private Beta | qualityTags 기반 조건부 적용, guard 완성, 운영 연결은 opt-in |
| **TestWorkspace QA** | 85 | MVP Production | RunAll, diff, preprocessing debug, 검증 체계 완성 |
| **RunOCR UX** | 65 | Internal Alpha | 기본 흐름 동작, autoApply 미연결, History 한계 |
| **Template UX** | 68 | Internal Alpha | 생성/저장 동작, site 격리 없음, localStorage 중복 |
| **History** | 45 | Prototype | localStorage 50건 한계, 이원화, 이미지 서버 없음 |
| **DB/storage** | 25 | Prototype | localStorage/JSON 파일 기반, DB-2 준비만 완료 |
| **Auth/security** | 15 | Prototype | **⚠ 평문 비밀번호**, 토큰 서버 미저장, 인가 없음 |
| **Site/multi-tenant** | 10 | Prototype | UI 렌더링만, 완전 비기능 |
| **Operations/logging** | 35 | Prototype | review_log.jsonl만, 모니터링/알림/백업 없음 |
| **Deployment readiness** | 30 | Prototype | uvicorn 단일 프로세스, 프로세스 관리 없음 |
| **Maintainability** | 70 | Private Beta | 명확한 모듈 구조, 테스트셋/리포트 체계 |

---

## 4. OCR 기능 수준 평가

### 4.1 수치 요약

| 지표 | T-18 (이전) | T-19 현재 | 변화 |
|---|---:|---:|---|
| docTypeMatchRate | 77.2% | 80.7% | +3.5%p |
| coreFieldFillRate | 87.6% | 89.1% | +1.5%p |
| coreFieldGtMatchRate | 99.1% | 99.1% | 유지 |
| rowCountExactRate | 100.0% | 100.0% | 유지 |
| classification_mismatch | 9건 | 7건 | -2 |
| parser_missed_source_exists | 4건 | 2건 | -2 |
| warningCount | 40 | 38 | -2 |

### 4.2 문서유형별 성능

| documentType | docTypeMatch | coreFieldFill | 판정 |
|---|---:|---:|---|
| invoice_statement (7) | **100.0%** | n/a (table) | **Stable** |
| food_cafe_receipt (15) | 93.3% | 93.3% | Good |
| card_receipt (13) | 76.9% | 94.5% | Classification weak |
| medical_receipt (6) | 66.7% | 91.7% | Classification weak |
| pos_receipt (10) | 70.0% | 76.7% | Both weak |
| finance_slip (5) | 80.0% | 0.0% | **Suppressed — extractor 없음** |
| unknown (1) | 0.0% | 50.0% | 추가 분석 필요 |

### 4.3 핵심 평가

**강점**:
- invoice_statement rowCount 7/7 exact → 해당 영역에서 운영 품질
- coreFieldGtMatchRate 99.1% → 추출된 값의 정확도는 매우 높음
- OP-anchor, colGuides, header-skip 등 정교한 invoice 처리 로직
- 회귀 방지 체계 (TestWorkspace RunAll, snapshot 비교)

**약점**:
- pos_receipt/medical_receipt classification 70% 미만 → 새 영수증에서 분류 오류 가능
- OCR source garbled/missing 케이스 6건 잔존 → 이미지 품질 문제 시 빈 결과
- 57개 샘플 기준 검증 → 실제 운영에서 새 양식 시 일반화 불보장
- 특정 샘플 패턴에 최적화 위험 (baseline_fast 데이터셋이 baseline과 동일 샘플)

**운영 관점 판단**:
- 보유 샘플 기준: **MVP 수준** — 알려진 형식에서 안정적 동작
- 범용 제품 수준: **아직 부족** — 새 영수증 양식/인쇄 품질 대응 미검증

---

## 5. 문서유형 커버리지 평가

| documentType | 현재 상태 | 운영 가능성 | 부족한 점 | 다음 작업 |
|---|---|---|---|---|
| **invoice_statement** | rowCount 7/7, E2E OK | **운영 가능** | optional 필드 partially missing | 실제 고객 문서 테스트 |
| **pos_receipt** | baseline 10건, docTypeMatch 70% | **베타 수준** | classification weak, garbled 다수 | 추가 샘플 수집, classifier 개선 |
| **card_receipt** | baseline 13건, coreFieldFill 94.5% | **베타 수준** | merchantName 일부 missing | T-15d 개선 완료, 추가 샘플 필요 |
| **food_cafe_receipt** | 15건, docTypeMatch 93% | **베타 수준** | food_002 merchantName garbled | 추가 샘플 수집 |
| **medical_receipt** | 6건, docTypeMatch 67% | **베타 수준** | animal hospital 특수 케이스 | 의원/동물병원 구분 샘플 |
| **finance_slip** | suppressed, extractor 미구현 | **불가** | parser 없음, 정책 suppressed | P2: 은행 전표 extractor 구현 |
| **tax_invoice (세금계산서)** | 샘플 없음 | **불가** | 전혀 미구현 | P2: 샘플 수집 후 설계 |
| **transaction_statement** | 예비 타입만 | **불가** | 미구현 | P3 |
| **unknown/suppressed** | 정책 완성 | 정책 정합 | — | 유지 |

---

## 6. Template/RunOCR/History 사용자 흐름 평가

### 6.1 Template 탭

**현재 완성도**: 68/100

| 기능 | 상태 | 문제 |
|---|---|---|
| 템플릿 생성/수정/삭제 | ✅ 동작 | — |
| table region + colGuides | ✅ 동작 | — |
| documentType 저장 | ✅ 동작 | — |
| site별 격리 | ❌ 없음 | 전체 공유 |
| 동시 쓰기 | ❌ 취약 | JSON 파일 race condition |
| localStorage 중복 | ⚠ 있음 | 서버와 동기화 로직 없음 |

### 6.2 RunOCR 탭

**현재 완성도**: 65/100

| 기능 | 상태 | 문제 |
|---|---|---|
| 파일 업로드 + OCR | ✅ 동작 | — |
| 템플릿 선택 + regions 전달 | ✅ 동작 | — |
| 결과 표시 + autofill | ✅ 동작 | — |
| autoApplyPreprocessing 연결 | ❌ 미전달 (선택 A) | 수동 T-21 보류 |
| History 장기 저장 | ❌ 50건 한계 | DB 필요 |
| 이미지 파일 서버 | ❌ 없음 | localStorage base64 (자동 제거) |
| 재실행 기능 | ❌ 없음 | job_id로 재실행 불가 |

### 6.3 History 탭

**현재 완성도**: 45/100

| 기능 | 상태 | 문제 |
|---|---|---|
| 실행 결과 저장 | ✅ 동작 (50건 한계) | |
| 상세 보기 | ✅ 동작 | |
| GroundTruth 저장 | ✅ 동작 (localStorage) | 브라우저 로컬만 |
| 삭제 | ✅ 동작 | |
| 장기 보존 | ❌ 없음 | 50건 초과 소실 |
| 이미지 복원 | ❌ 없음 | 용량 초과 시 자동 제거 |
| 여러 사용자 공유 | ❌ 없음 | — |
| 검색/필터 | ❌ 없음 | — |

### 6.4 TestWorkspace 탭

**현재 완성도**: 85/100 — 개발/검증 도구로서 높은 완성도

| 기능 | 상태 |
|---|---|
| RunAll / RunOne | ✅ 완성 |
| diff 비교 | ✅ 완성 |
| KPI 요약 | ✅ 완성 |
| JSON/MD export | ✅ 완성 |
| preprocessing debug/autoApply 체크박스 | ✅ T-21 완성 |
| qualityTags 전달 | ✅ 완성 |
| 복수 testset 관리 | ✅ 완성 |
| DB 연동 | ❌ 없음 (localStorage 기반) |

---

## 7. TestWorkspace/QA 체계 평가

**점수**: 85/100 — 이 프로젝트의 가장 강한 부분 중 하나

**강점**:
- T-22 기준 26개 샘플 검증 체계
- regression 0건 달성 및 유지 체계
- invoice_statement 7/7 exact guard
- JSON/MD 리포트 자동 생성
- preprocessing debug/autoApply 옵션 연결

**약점**:
- 실제 OCR 서버 실행 없이 캐시 기반 검증 일부 (`cache_based_parser` 경고)
- 새 샘플 추가 시 자동화 파이프라인 없음
- CI/CD 연동 없음

---

## 8. Preprocessing 체계 평가

**점수**: 72/100

| 항목 | 상태 |
|---|---|
| T-20 실험 (10샘플 72 variant) | ✅ 완료 |
| qualityTags 기반 policy | ✅ 완료 |
| guard (8개 규칙) | ✅ 완료 |
| debugPreprocessing API | ✅ 완료 |
| autoApplyPreprocessing (receipt opt-in) | ✅ 완료 |
| invoice_statement 영구 제외 | ✅ 완료 |
| productionApplied 4건 확인 | ✅ 완료 |
| RunOCR 자동 연결 (Phase 3) | ❌ 보류 |
| 기본값 false (안전) | ✅ 유지 |
| preprocessing_candidate 태그 보강 | ✅ T-20h 완료 |

**운영 판단**: preprocessing은 opt-in 방식으로 안전하게 설계됨. Phase 3 자동 연결은 추가 실사용 검증 후 결정이 적절.

---

## 9. DB/저장 구조 평가

**점수**: 25/100

### 현재 한계

| 저장소 | 한계 |
|---|---|
| `mysuit_ocr_history` (localStorage) | MAX 50건, 5MB 한계, 이미지 자동 제거 |
| `templates.json` (backend) | 동시 쓰기 race condition |
| `users.json` (backend) | **평문 비밀번호** — 운영 불가 |
| `history.json` (backend) | 메타만 4개 필드 |
| `review_log.jsonl` (backend) | 무제한 누적, 검색 불가 |
| `mysuit_ocr_groundtruth` (localStorage) | 브라우저 로컬만 |
| Site 격리 | 없음 |

### DB 전환 없이 운영하면?

- 50건 이후 History 영구 소실 → 고객 불만 직결
- users.json 노출 시 모든 계정 탈취
- 여러 사용자가 같은 서버 접속 시 templates.json 충돌
- GroundTruth 브라우저 종료/교체 시 소실

### DB-2 준비 수준

- ARCH-1 데이터 흐름 분석 완료 ✅
- DB-PREP-1 15개 결정사항 완료 ✅
- schema.sql 작성 준비 완료 ✅
- 실제 schema.sql 미작성 ❌
- DB 연결 코드 없음 ❌

---

## 10. Auth/Security 평가

**점수**: 15/100 — 운영 투입 시 가장 큰 리스크

### 현재 상태

```
users.json:
  admin / 1234  (평문)
  user  / user  (평문)
```

| 항목 | 상태 | 위험도 |
|---|---|---|
| 비밀번호 저장 | **평문** | 🔴 CRITICAL |
| 토큰 서버 저장 | **없음** (uuid 생성 후 버림) | 🔴 HIGH |
| 토큰 만료 | **없음** | 🔴 HIGH |
| 로그아웃 무효화 | **불가** | 🔴 HIGH |
| 토큰 클라이언트 저장 | localStorage (XSS 취약) | 🟡 MEDIUM |
| HTTPS 강제 | 설정 없음 | 🟡 MEDIUM |
| 인가(permission) | 없음 | 🟡 MEDIUM |
| 감사 로그 | review_log.jsonl만 | 🟡 MEDIUM |
| 파일 접근 제어 | 없음 | 🟡 MEDIUM |
| 개인정보 저장 | 영수증에 사업자번호/주소 포함 | 🟡 MEDIUM |

**결론**: 현재 인증 구조는 **개발/로컬 환경 전용**. 외부 사용자가 접속하는 즉시 보안 위험 노출.

---

## 11. Site/Multi-tenant 평가

**점수**: 10/100

| 항목 | 상태 |
|---|---|
| site 드롭다운 UI | Sidebar.tsx:84 렌더링만 |
| site 선택 → API 전달 | ❌ 없음 |
| template site_id 격리 | ❌ 없음 |
| history site_id 격리 | ❌ 없음 |
| user-site 권한 | ❌ 없음 |
| 멀티 테넌시 | ❌ 미구현 |

**결론**: 현재는 단일 사용자/단일 사이트 전제. 2명 이상 사용 시 데이터 혼재 발생.

---

## 12. 운영/배포 준비도 평가

**점수**: 30/100

| 항목 | 현재 상태 | 필요한 것 |
|---|---|---|
| Backend 실행 | uvicorn 단일 프로세스 | supervisor/gunicorn |
| 프로세스 관리 | 없음 | systemd/docker |
| 로그 수집 | print() 콘솔 출력 | structured logging |
| 모니터링 | 없음 | health check, uptime |
| 에러 알림 | 없음 | Sentry 등 |
| 성능 | OCR 1회 30~70초 | GPU 가속 또는 캐싱 |
| 동시 처리 | uvicorn async (OCR는 blocking) | 큐/워커 구조 |
| 파일 저장소 | 없음 (base64 임시) | uploads/ 또는 S3 |
| DB | 없음 (JSON 파일) | PostgreSQL |
| 백업 | 없음 | 정기 백업 |
| HTTPS | 없음 | nginx + SSL |
| 배포 자동화 | 없음 | CI/CD |

**OCR 처리 시간**: review_log.jsonl 기준 30~70초/건 → 다수 사용자 동시 사용 불가

---

## 13. 현재 가능한 운영 범위

| 운영 단계 | 가능 여부 | 조건 | 막는 요인 |
|---|---|---|---|
| **개발자 본인 로컬 사용** | ✅ 가능 | localhost만, 외부 노출 금지 | — |
| **내부 팀 테스트 (2~3인)** | ⚠ 조건부 | 비밀번호 변경 필수, 같은 네트워크만 | 평문 비밀번호, site 격리 없음 |
| **제한 지인/클로즈드 베타** | ❌ 불가 | — | 평문 비밀번호, 토큰 검증 없음, History 소실 |
| **소규모 유료 MVP** | ❌ 불가 | — | 보안, DB, 파일 서버, 사이트 격리 |
| **일반 SaaS 운영** | ❌ 불가 | — | 모든 인프라 미비 |
| **기업/다중 사용자** | ❌ 불가 | — | site_members, audit, compliance |

---

## 14. 부족 작업 우선순위

| priority | 작업 | 이유 | 예상 영향 |
|---|---|---|---|
| **P0** | **users.json 평문 비밀번호 → bcrypt** | 보안 치명 | 외부 테스트 가능 |
| **P0** | **sessions 테이블 + 토큰 서버 저장** | 로그아웃/만료 불가 | 인증 신뢰성 |
| **P1** | **DB-2 schema.sql 작성** | 모든 DB 작업의 선결 | — |
| **P1** | **DB 연결 config (PostgreSQL)** | schema 작성 후 즉시 | — |
| **P1** | **templates → DB 저장/조회** | localStorage 중복 제거, site 격리 선결 | — |
| **P1** | **RunOCR history → DB 저장** | 50건 한계 해소 | MVP 필수 |
| **P1** | **파일 서버 구현 (uploads/)** | 이미지 영구 저장 | — |
| **P1** | **Site 기능 실제화** | 다중 사용자 격리 | — |
| **P2** | GroundTruth DB 전환 | 브라우저 로컬 → 공유 가능 | |
| **P2** | audit_logs 구현 | 감사 추적 | |
| **P2** | 배포 구성 (HTTPS, supervisor) | 외부 접속 안전 | |
| **P2** | OCR 처리 시간 개선 / 큐 구조 | 30~70초/건 → 동시 처리 | |
| **P2** | finance_slip extractor 구현 | 은행 전표 운영 불가 | |
| **P3** | tax_invoice 샘플 수집 및 설계 | 세금계산서 미지원 | |
| **P3** | RunOCR autoApply Phase 3 | 자동 전처리 운영 연결 | |
| **P3** | CI/CD 배포 자동화 | 수동 배포 → 자동화 | |
| **P3** | 신규 문서유형 확장 (transaction_statement 등) | 범용성 | |

---

## 15. 다음 2주 로드맵

### Week 1 — 보안 + DB 기반

| Day | 작업 | 완료 기준 |
|---|---|---|
| Day 1 | **DB-2 schema.sql 작성** | 14개 테이블 DDL + 인덱스 + 제약 |
| Day 2 | **DB 연결 config** (FastAPI + asyncpg/psycopg2) | `DATABASE_URL` 환경변수, 연결 테스트 |
| Day 3 | **users + sessions 마이그레이션** | bcrypt 해시, sessions 테이블, /login 수정 |
| Day 4 | **sites + site_members 기본** | 기본 site 자동 생성, site_id FK |
| Day 5 | **templates → DB** | GET/POST/DELETE /templates DB 전환 |

### Week 2 — 운영 흐름

| Day | 작업 | 완료 기준 |
|---|---|---|
| Day 6 | **ocr_runs + ocr_run_files** | RunOCR 실행 시 DB 저장, storage_key 파일 서버 |
| Day 7 | **ocr_run_results** | receipt_fields + document_fields jsonb 저장 |
| Day 8 | **History 탭 DB 조회** | localStorage 대체, 50건 한계 해소 |
| Day 9 | **GroundTruth DB 전환** | ocr_ground_truth 테이블, autofill API |
| Day 10 | **audit_logs + 배포 구성** | nginx + HTTPS + supervisor, 기본 감사 로그 |

### 2주 후 예상 완성도

| 영역 | 현재 | 2주 후 |
|---|---|---|
| DB/storage | 25 | **75** |
| Auth/security | 15 | **72** |
| Site/multi-tenant | 10 | **55** |
| History | 45 | **78** |
| Template UX | 68 | **80** |
| Deployment | 30 | **60** |
| **전체** | **52%** | **~70%** |

---

## 16. 결론

### 현재 수준: 약 52% 완성

**기능 완성도**: OCR 엔진·parser·preprocessing·TestWorkspace·Template·RunOCR 흐름은 약 72% 수준으로 개발 완성에 가깝다.  
**운영 인프라 완성도**: DB/인증/보안/배포는 약 30% 수준으로 Prototype 단계다.  
이 불균형이 현재 전체 완성도를 52%로 누르는 원인이다.

### MVP 운영까지 필요한 핵심 작업 (6가지)

1. **bcrypt 비밀번호 해시** — 외부 사용자 접속 전 반드시
2. **sessions 테이블** — 토큰 만료/무효화
3. **DB-2 schema + 연결** — 모든 DB 작업의 선결 조건
4. **templates/history DB 전환** — 데이터 영속성
5. **파일 서버 (uploads/)** — 이미지 영구 저장
6. **Site 기능 실현** — 다중 사용자 격리

### 상용 운영까지 추가 필요한 작업

- HTTPS + nginx + 프로세스 관리 (supervisor/docker)
- OCR 처리 큐 구조 (30~70초/건 → 비동기 처리)
- audit_logs + 감사 체계
- finance_slip extractor + tax_invoice 지원
- CI/CD 배포 자동화
- 성능 최적화 (GPU 가속 또는 모델 경량화)
- 개인정보 처리 방침 (영수증 내 개인정보 보존 정책)

**한 줄 요약**: OCR 엔진은 베타 수준이지만, 운영 인프라(DB/보안/배포)가 Prototype 단계라 현재는 개발자 로컬 사용 또는 제한된 내부 테스트만 가능하다. 2주 DB 전환 작업 완료 시 소규모 MVP 운영이 가능해진다.
