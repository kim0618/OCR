# DB-PREP-1 DB-2 Schema 결정사항 체크리스트

**작성일**: 2026-05-17  
**목적**: DB-2 PostgreSQL schema.sql 작성 전 필수 결정사항 정리  
**근거**: ARCH-1 현재 데이터 흐름 분석 결과  
**원칙**: 내일 schema.sql 작성 시 이 문서를 기준으로 직접 반영

---

## 1. 생성 파일

- `mysuit-ocr/docs/db/db2_schema_decision_checklist_20260517.md`
- `mysuit-ocr/docs/db/db2_schema_decision_checklist_20260517.json`

---

## 2. 핵심 요약

| 우선순위 | 결정사항 수 | 핵심 내용 |
|---|---|---|
| P0 | 2건 | 비밀번호 해시, 토큰 방식 — 보안 필수 |
| P1 | 8건 | Schema 구조 확정 필요 (site, PK, 파일, template, OCR결과 등) |
| P2 | 4건 | Schema 여지 남기고 후속 구현에서 확정 |
| P3 | 1건 | 장기 확장 |

---

## 3. P0 결정사항 (보안/무결성 — schema 전에 반드시 결정)

---

### 결정사항 1. 비밀번호 저장 방식  **[P0]**

- **현재 상태**: `data/users.json`에 평문 저장 (`"user_pw": "1234"`)  
- **선택지**:
  - **A. bcrypt** — 업계 표준, Python `passlib[bcrypt]`, Node.js `bcryptjs`. cost factor 12 권장
  - **B. argon2** — 최신 보안, 메모리 하드 해시. Python `argon2-cffi`
  - **C. SHA-256 (단순 해시)** — 권장하지 않음. salt 없으면 레인보우 테이블 취약
- **추천안**: **A. bcrypt, cost factor 12**
- **이유**: argon2보다 생태계 성숙, PostgreSQL pgcrypto에서 crypt() 직접 지원, Python/Node 모두 쉽게 사용 가능. 기존 두 계정 마이그레이션이 필요하므로 단순 구현이 중요.
- **DB-2 반영**: `users.password_hash VARCHAR(60) NOT NULL` (bcrypt 해시 60자 고정)
- **마이그레이션**: 첫 로그인 시 평문 검증 후 해시로 교체하거나, 직접 bcrypt 해시 생성 후 INSERT
- **후속 영향**: `/login` 엔드포인트 bcrypt.verify 추가 필요

---

### 결정사항 2. 인증/토큰 방식  **[P0]**

- **현재 상태**: POST /login → uuid4() 생성 → 클라이언트 localStorage 저장. 서버 미저장, 만료/무효화 불가
- **선택지**:
  - **A. JWT access(15분) + refresh token(7일)** — stateless, 서버 저장 최소화. refresh는 DB sessions 테이블
  - **B. session UUID + HttpOnly cookie** — 서버 세션 관리, XSS 안전. sessions 테이블 필요
  - **C. 현재 방식 유지 (uuid 토큰, localStorage)** — 구현 비용 없음. 보안 개선 없음
- **추천안**: **B. session UUID + HttpOnly cookie** (또는 현재 구조 최소 보강)
  - 단기: 현재 uuid 방식 유지하되 **sessions 테이블 추가로 서버 검증 추가**
  - 중기: HttpOnly cookie로 전환
- **이유**: 현재 OCR 서버는 FastAPI 단일 프로세스. JWT stateless 방식보다 sessions 테이블이 구현 단순. XSS 방어를 위해 장기적으로 cookie 전환 권장.
- **DB-2 반영**: `sessions(session_id UUID PK, user_id FK, created_at, expires_at, revoked_at)` 테이블 포함
- **후속 영향**: `users` 테이블과 sessions 1:N 관계. 로그아웃 시 sessions.revoked_at 업데이트

---

## 4. P1 결정사항 (Schema 작성 전에 결정 필요)

---

### 결정사항 3. Primary Key 방식  **[P1]**

- **현재 상태**: JSON에서 UUID 기반 (`TPL-95328E52`, `OCR-A1B2C3D4`, `RUN-XXXXXXXX`)
- **선택지**:
  - **A. UUID v4 (gen_random_uuid())** — 랜덤, 분산 안전, 순서 없음. pgcrypto 필요
  - **B. BIGSERIAL** — 자동 증가 정수, 단순, 순서 있음. 분산 시 충돌 위험
  - **C. UUID v7** — 시간순 정렬 가능 UUID. PostgreSQL 17+ 기본 지원, 이전 버전 확장 필요
- **추천안**: **A. UUID v4 (gen_random_uuid())** — 현재 시스템과 호환, 미래 분산 확장 대비
- **이유**: 기존 job_id/template_id가 이미 UUID 기반. pgcrypto는 PostgreSQL 표준 확장.
- **DB-2 반영**: `CREATE EXTENSION IF NOT EXISTS pgcrypto;` + `DEFAULT gen_random_uuid()`
- **후속 영향**: 모든 FK도 UUID 타입

---

### 결정사항 4. site/workspace 모델  **[P1]**

- **현재 상태**: Sidebar.tsx에 드롭다운만 렌더링, 비기능. comp_cd="MYSUIT" 단일 조직
- **선택지**:
  - **A. 단일 기본 site 자동 생성** — 사용자 가입 시 기본 site 1개 자동 생성. 단순, 초기 마이그레이션 쉬움
  - **B. 독립 site 엔티티 + site_members** — 완전한 멀티 테넌시. 복잡하지만 확장성 높음
  - **C. org/workspace 계층** — org > site > user 3단계. 과도한 복잡성
- **추천안**: **B. 독립 site 엔티티 + site_members** — 단 처음에는 site 1개로 단순하게 시작
- **이유**: site_members 테이블이 있어야 template/run 격리가 가능. 처음부터 FK를 site_id로 연결해 두면 나중에 멀티 테넌시 확장이 쉬움.
- **DB-2 반영**: `sites(site_id, site_nm, comp_cd, created_at)`, `site_members(site_id, user_id, role, joined_at)`
- **role enum**: `'owner', 'admin', 'member', 'viewer'`
- **후속 영향**: templates/runs/ground_truth 모두 `site_id FK` 포함

---

### 결정사항 5. 파일 저장 방식  **[P1]**

- **현재 상태**: 이미지를 base64로 localStorage에 저장 (5MB 한계로 자동 제거). 파일 서버 없음
- **선택지**:
  - **A. DB bytea 저장** — 파일을 DB 컬럼에 직접. 구현 단순, 대용량 비효율
  - **B. local filesystem + path 저장** — `storage_key = "local:/uploads/xxx.jpg"`. 빠르고 단순. 분산 미지원
  - **C. storage_key 추상화** — `storage_key VARCHAR` 컬럼에 `local://`, `s3://`, `azure://` 스키마로 경로 저장. 확장 가능
- **추천안**: **C. storage_key 추상화** — 현재는 local filesystem, 나중에 S3/Azure 전환 가능
- **이유**: DB에 파일 직접 저장은 성능 문제. 경로 추상화를 해두면 이후 클라우드 스토리지 전환이 쉬움.
- **DB-2 반영**: `ocr_run_files.storage_key VARCHAR(512) NOT NULL`, `file_size_bytes BIGINT`, `mime_type VARCHAR(64)`
- **후속 영향**: 업로드 API에서 파일 저장 후 storage_key 생성 로직 필요

---

### 결정사항 6. template 저장 정규화 수준  **[P1]**

- **현재 상태**: `template_json` 통째로 JSON blob 저장 (regions[], colGuides[], documentType, image 메타 모두 포함)
- **선택지**:
  - **A. template_json jsonb blob 전체 저장** — 현재 방식 유지. 단순, region 검색/수정 불편
  - **B. templates/regions/guides 완전 정규화** — 복잡하지만 region별 쿼리 가능
  - **C. Hybrid — 핵심 컬럼 분리 + template_json 캐시** — `ocr_templates.document_type` 분리, `template_body jsonb`는 유지
- **추천안**: **C. Hybrid** — `document_type`, `image_width`, `image_height` 분리 + `template_body jsonb`
- **이유**: 현재 RunOCR에서 regions를 JSON string으로 통째로 넘기는 구조. 완전 정규화는 API 변경 범위가 크고 당장 필요 없음. Hybrid가 중간점.
- **DB-2 반영**: 
  - `ocr_templates(template_id, site_id, template_nm, document_type, image_width, image_height, template_body JSONB, created_at, updated_at, deleted_at)`
  - P2: `ocr_template_regions`, `ocr_template_table_guides` (선택적 정규화)
- **후속 영향**: GET /templates 응답에서 template_body를 그대로 regions로 사용 가능

---

### 결정사항 7. region 좌표 기준  **[P1]**

- **현재 상태**: pixel 절대 좌표 (image.width × image.height 기준). RunOCR에서 regions JSON으로 전달
- **선택지**:
  - **A. pixel 절대 좌표** — 현재 방식. 이미지 크기 변경 시 좌표 재계산 필요
  - **B. normalized 좌표 (0.0~1.0)** — 이미지 크기 독립. 계산 필요
  - **C. 둘 다 저장** — 과도한 중복
- **추천안**: **A. pixel 절대 좌표 유지** — 현재 UI/API와 호환성 중요. image_width/height를 함께 저장해 나중에 normalized 계산 가능
- **이유**: 프론트/백엔드 모두 pixel 좌표 기준으로 구현됨. 지금 변경하면 기존 템플릿 데이터 불일치.
- **DB-2 반영**: `ocr_templates.image_width INT, image_height INT` + regions 내 pixel 좌표 jsonb 유지
- **후속 영향**: 템플릿 이미지 크기 변경 시 좌표 마이그레이션 로직 별도 필요

---

### 결정사항 8. RunOCR history 저장 단위  **[P1]**

- **현재 상태**: 
  - `history.json`: job_id + 메타만 (4개 필드)
  - localStorage: 상세 필드 + 이미지 URL + autofill summary (최대 50건)
- **선택지**:
  - **A. run 단위만 저장** — `ocr_runs` 1테이블, result는 JSON blob
  - **B. run + result 분리** — `ocr_runs` + `ocr_run_results` (receipt/invoice 분리)
  - **C. run + file + result 분리** — `ocr_runs`, `ocr_run_files`, `ocr_run_results` 3테이블
- **추천안**: **C. run + file + result 분리**
- **이유**: 파일 저장(storage_key)이 별도 필요. 결과도 receipt/invoice 구조가 다름. 나중에 테이블 추가 없이 확장 가능.
- **DB-2 반영**: 
  - `ocr_runs(run_id, site_id, user_id, template_id, run_status, created_at, deleted_at)`
  - `ocr_run_files(file_id, run_id, storage_key, original_filename, mime_type, file_size_bytes)`
  - `ocr_run_results(result_id, file_id, doc_type, run_status, receipt_fields JSONB, document_fields JSONB, raw_text, processing_time_sec, preprocessing_debug JSONB)`
- **후속 영향**: 히스토리 조회 시 JOIN 필요

---

### 결정사항 9. OCR result JSON 저장 범위  **[P1]**

- **현재 상태**: localStorage에 raw OCR fields, normalized fields, autofill summary 모두 저장. review_log.jsonl에 full_text, 금액 후보, upper_block_text 저장
- **선택지**:
  - **A. 최소화** — receipt_fields jsonb, raw_text만
  - **B. 중간** — receipt_fields + document_fields + raw_text + processing_time
  - **C. 전체** — A + extract_debug + preprocessing_debug + autofill_summary + review_log 데이터
- **추천안**: **B. 중간** — 핵심 필드만 저장, debug 정보는 nullable jsonb로 옵셔널
- **이유**: extract_debug는 수 KB ~ 수십 KB. 모든 실행마다 저장하면 DB 빠르게 성장. 중요한 것은 최종 결과 필드. preprocessingDebug는 productionApplied=true일 때만 저장.
- **DB-2 반영**: 
  ```
  ocr_run_results:
    receipt_fields JSONB,
    document_fields JSONB,
    raw_text TEXT,
    doc_type VARCHAR(50),
    processing_time_sec NUMERIC(8,3),
    preprocessing_debug JSONB,  -- nullable, productionApplied=true 시만
    autofill_summary JSONB,     -- nullable
  ```
- **후속 영향**: extract_debug는 저장 안 함 (운영 로그는 review_log 또는 audit_logs)

---

### 결정사항 10. GroundTruth 구조  **[P1]**

- **현재 상태**: localStorage `{template::file: {fieldKey: value}}`. 사용자 RunOCR 확정값. testset GT와 별도
- **선택지**:
  - **A. field 단위** — `(template_id, filename, field_key) → confirmed_value`. 유연
  - **B. document 단위** — `(template_id, filename) → {fields: jsonb}`. 단순
  - **C. run 연결** — `(run_id, field_key) → confirmed_value`. 구체적이나 run과 결합
- **추천안**: **A. field 단위** — `(template_id, filename, field_key) UNIQUE`
- **이유**: 필드별 수정 이력 추적 가능. testset GT와 구조적으로 분리.
- **DB-2 반영**:
  ```
  ocr_ground_truth:
    gt_id UUID PK,
    site_id UUID FK,
    template_id UUID FK NULLABLE,  -- 템플릿 없이 사용 가능
    filename VARCHAR(255),
    field_key VARCHAR(100),
    confirmed_value TEXT,
    confirmed_by UUID FK -> users,
    confirmed_at TIMESTAMPTZ,
    UNIQUE(template_id, filename, field_key)
  ```
- **후속 영향**: autofillEngine이 ground truth 조회 시 API 호출 필요 (localStorage 대체)

---

## 5. P2 결정사항 (Schema에 여지만 남기고 후속 구현에서 확정)

---

### 결정사항 11. preprocessingDebug 저장 여부  **[P2]**

- **현재 상태**: `response.preprocessingDebug` 백엔드 응답에 있지만 DB 미저장
- **선택지**:
  - **A. 저장 안 함** — 구현 단순, debug 이력 없음
  - **B. debug mode만 저장** — `debugPreprocessing=true` 요청 시만
  - **C. productionApplied=true일 때만 저장** — 실제 적용 시만 이력 보존
- **추천안**: **C. productionApplied=true일 때만** + Schema에 nullable 컬럼으로 준비
- **이유**: debug 정보 전체 저장은 DB 급증. 실제 전처리 적용 이력만 보존하면 충분.
- **DB-2 반영**: `ocr_run_results.preprocessing_debug JSONB NULLABLE` — 현재는 null, 향후 적용 시 저장
- **후속 영향**: autoApplyPreprocessing=true 흐름에서 productionApplied=true 시 insert

---

### 결정사항 12. tableRows 저장 방식  **[P2]**

- **현재 상태**: `document_fields.tableRows` 배열이 localStorage JSON에 포함
- **선택지**:
  - **A. result jsonb 안에 포함** — 단순, 행 단위 쿼리 불가
  - **B. ocr_run_table_rows 별도 테이블** — 행 단위 비교/검증 가능. 복잡
  - **C. Hybrid** — 핵심은 result jsonb, 별도 테이블은 향후
- **추천안**: **C. Hybrid** — 우선은 `document_fields jsonb` 안에 포함, `ocr_run_table_rows` 테이블은 P3
- **이유**: 현재 invoice 7개 샘플, 최대 28행. 별도 테이블 효과가 아직 작음. jsonb로 유연하게 시작.
- **DB-2 반영**: `document_fields JSONB` 안에 `tableRows` 포함 (P3에서 정규화 재평가)
- **후속 영향**: P3 정규화 시 마이그레이션 필요

---

### 결정사항 13. soft delete 적용 범위  **[P2]**

- **현재 상태**: DELETE는 JSON 파일에서 직접 제거. 복구 불가
- **선택지**:
  - **A. 전체 soft delete** — 모든 테이블에 `deleted_at TIMESTAMPTZ`
  - **B. 선택적 soft delete** — templates + runs만. users/sites는 status 컬럼
  - **C. hard delete** — 단순, 감사 기록 없음
- **추천안**: **B. 선택적 soft delete** — `ocr_templates`, `ocr_runs`에 `deleted_at NULLABLE`
- **이유**: templates/runs는 복구 요청이 있을 수 있음. users는 status('active','inactive','suspended') 컬럼.
- **DB-2 반영**: 
  - `ocr_templates.deleted_at TIMESTAMPTZ NULL`
  - `ocr_runs.deleted_at TIMESTAMPTZ NULL`
  - `users.status VARCHAR(20) DEFAULT 'active'`
- **후속 영향**: SELECT 쿼리에 `WHERE deleted_at IS NULL` 필터 필요

---

### 결정사항 14. audit_logs 범위  **[P2]**

- **현재 상태**: review_log.jsonl (OCR auto_extract 이벤트만 append)
- **선택지**:
  - **A. 최소** — OCR run 이벤트만
  - **B. 중간** — login + template CRUD + run + result delete
  - **C. 전체** — 모든 사용자 행동
- **추천안**: **B. 중간** — login/template_crud/run/groundtruth_update
- **이유**: 보안 감사 최소 요건 충족. 전체 저장은 volume 급증.
- **DB-2 반영**:
  ```
  audit_logs:
    log_id UUID PK,
    site_id UUID FK,
    user_id UUID FK NULLABLE,
    event_type VARCHAR(50),  -- 'login','template_create','run_delete','gt_update' 등
    resource_type VARCHAR(50),
    resource_id UUID NULLABLE,
    payload JSONB NULLABLE,
    created_at TIMESTAMPTZ
  ```
- **후속 영향**: review_log.jsonl 데이터는 event_type='auto_extract'으로 이전 가능

---

## 6. P3 결정사항 (장기 확장)

---

### 결정사항 15. enum 전략  **[P3]**

- **현재 상태**: 문자열 상수 사용 (adminYn="Y"/"N", status="success"/"fail")
- **선택지**:
  - **A. PostgreSQL ENUM 타입** — DB 레벨 강제, 변경 시 `ALTER TYPE` 필요
  - **B. TEXT + CHECK CONSTRAINT** — 유연, 변경 쉬움
  - **C. 별도 lookup 테이블** — 과도한 복잡성
- **추천안**: **B. TEXT + CHECK CONSTRAINT** — 초기에는 유연하게, 안정화 후 enum 전환 고려
- **이유**: ENUM은 값 추가/제거가 불편. TEXT + CHECK로 시작하면 변경 비용 낮음.
- **DB-2 반영**: 
  - `site_members.role TEXT CHECK (role IN ('owner','admin','member','viewer'))`
  - `ocr_runs.run_status TEXT CHECK (run_status IN ('pending','running','success','fail'))`
  - `users.status TEXT CHECK (status IN ('active','inactive','suspended'))`
- **후속 영향**: 값 범위 변경 시 CHECK CONSTRAINT만 수정

---

## 7. DB-2 반영 요약표

| 항목 | 추천안 | 우선순위 | DB-2 반영 방식 |
|---|---|---|---|
| 비밀번호 해시 | bcrypt, cost=12 | **P0** | `password_hash VARCHAR(60) NOT NULL` |
| 인증/토큰 | sessions 테이블 + UUID | **P0** | `sessions(session_id, user_id, expires_at, revoked_at)` |
| Primary Key | UUID v4 gen_random_uuid() | **P1** | `CREATE EXTENSION pgcrypto; DEFAULT gen_random_uuid()` |
| site 모델 | 독립 sites + site_members | **P1** | `sites`, `site_members(role TEXT CHECK(...))` |
| 파일 저장 | storage_key 추상화 | **P1** | `ocr_run_files.storage_key VARCHAR(512)` |
| template 정규화 | Hybrid (컬럼분리 + jsonb) | **P1** | `template_body JSONB` + `document_type`, `image_width/height` |
| region 좌표 | pixel 절대 좌표 유지 | **P1** | `image_width INT, image_height INT` + jsonb regions |
| history 단위 | run + file + result 분리 | **P1** | `ocr_runs`, `ocr_run_files`, `ocr_run_results` 3테이블 |
| OCR 결과 저장 | B. 중간 (필수 필드 + nullable debug) | **P1** | `receipt_fields JSONB`, `preprocessing_debug JSONB NULL` |
| GroundTruth | field 단위 (template_id, filename, field_key) | **P1** | `ocr_ground_truth` UNIQUE(template_id, filename, field_key) |
| preprocessingDebug | productionApplied=true 시만 | **P2** | `preprocessing_debug JSONB NULL` — 평소 NULL |
| tableRows | Hybrid (jsonb 안에 포함) | **P2** | `document_fields JSONB` 안에 포함 (P3 정규화 재평가) |
| soft delete | templates + runs만 | **P2** | `deleted_at TIMESTAMPTZ NULL` |
| audit_logs | 중간 (login + CRUD + run) | **P2** | `audit_logs(event_type, resource_type, resource_id, payload)` |
| enum 전략 | TEXT + CHECK CONSTRAINT | **P3** | CHECK (value IN (...)) |

---

## 8. 내일 DB-2 입력 기준

내일 DB-2 PostgreSQL schema.sql 작성 시 아래 기준을 입력값으로 사용한다.

```
DB 엔진: PostgreSQL 14+
확장: pgcrypto (gen_random_uuid), pg_stat_statements (옵션)

PK: UUID v4, DEFAULT gen_random_uuid()
timestamp: TIMESTAMPTZ (timezone-aware)
문자열: VARCHAR 길이 명시 (무제한 TEXT는 raw_text/payload만)

[users 테이블]
- user_id UUID PK
- user_nm VARCHAR(100) NOT NULL
- email VARCHAR(255) UNIQUE NULLABLE  -- 향후 이메일 로그인
- password_hash VARCHAR(60) NOT NULL  -- bcrypt 60자
- status TEXT CHECK (status IN ('active','inactive','suspended')) DEFAULT 'active'
- created_at TIMESTAMPTZ DEFAULT NOW()
- updated_at TIMESTAMPTZ DEFAULT NOW()

[sessions 테이블]
- session_id UUID PK DEFAULT gen_random_uuid()
- user_id UUID FK -> users
- created_at TIMESTAMPTZ DEFAULT NOW()
- expires_at TIMESTAMPTZ NOT NULL
- revoked_at TIMESTAMPTZ NULL

[sites 테이블]
- site_id UUID PK
- site_nm VARCHAR(200) NOT NULL
- comp_cd VARCHAR(50)  -- 현재 MYSUIT 마이그레이션
- created_at TIMESTAMPTZ DEFAULT NOW()

[site_members 테이블]
- site_id UUID FK -> sites
- user_id UUID FK -> users
- role TEXT CHECK (role IN ('owner','admin','member','viewer'))
- joined_at TIMESTAMPTZ DEFAULT NOW()
- PRIMARY KEY (site_id, user_id)

[ocr_templates 테이블]
- template_id UUID PK
- site_id UUID FK -> sites
- template_nm VARCHAR(200) NOT NULL
- document_type VARCHAR(50)  -- 'invoice_statement', 'card_receipt' 등
- image_width INT
- image_height INT
- template_body JSONB NOT NULL  -- regions[], colGuides[] 포함
- created_at TIMESTAMPTZ DEFAULT NOW()
- updated_at TIMESTAMPTZ DEFAULT NOW()
- deleted_at TIMESTAMPTZ NULL  -- soft delete

[ocr_runs 테이블]
- run_id UUID PK
- site_id UUID FK -> sites
- user_id UUID FK -> users NULLABLE
- template_id UUID FK -> ocr_templates NULLABLE
- run_status TEXT CHECK (run_status IN ('pending','running','success','fail'))
- created_at TIMESTAMPTZ DEFAULT NOW()
- deleted_at TIMESTAMPTZ NULL  -- soft delete

[ocr_run_files 테이블]
- file_id UUID PK
- run_id UUID FK -> ocr_runs
- storage_key VARCHAR(512) NOT NULL  -- 'local://uploads/xxx.jpg', 's3://bucket/key' 등
- original_filename VARCHAR(255)
- mime_type VARCHAR(64)
- file_size_bytes BIGINT
- file_type TEXT CHECK (file_type IN ('image','pdf'))

[ocr_run_results 테이블]
- result_id UUID PK
- file_id UUID FK -> ocr_run_files
- doc_type VARCHAR(50)
- run_status TEXT CHECK (run_status IN ('selected','suppressed','error'))
- receipt_fields JSONB NULL  -- {회사명, 사업자번호, 총합계금액, ...}
- document_fields JSONB NULL -- {tableRows, tableMeta, rowCount, ...}
- raw_text TEXT NULL
- processing_time_sec NUMERIC(8,3)
- preprocessing_debug JSONB NULL  -- productionApplied=true 시만 저장
- autofill_summary JSONB NULL
- created_at TIMESTAMPTZ DEFAULT NOW()

[ocr_ground_truth 테이블]
- gt_id UUID PK
- site_id UUID FK -> sites
- template_id UUID FK -> ocr_templates NULLABLE
- filename VARCHAR(255) NOT NULL
- field_key VARCHAR(100) NOT NULL  -- en 우선, 없으면 ko (lowercase)
- confirmed_value TEXT NOT NULL
- confirmed_by UUID FK -> users NULLABLE
- confirmed_at TIMESTAMPTZ DEFAULT NOW()
- UNIQUE(template_id, filename, field_key)

[user_preferences 테이블]
- pref_id UUID PK
- user_id UUID FK -> users UNIQUE
- prefs JSONB DEFAULT '{}'  -- {theme: 'dark', ...}
- updated_at TIMESTAMPTZ DEFAULT NOW()

[audit_logs 테이블]
- log_id UUID PK
- site_id UUID FK -> sites NULLABLE
- user_id UUID FK -> users NULLABLE
- event_type VARCHAR(50) NOT NULL  -- 'login','template_create','run_delete','gt_update' 등
- resource_type VARCHAR(50) NULL   -- 'template','run','ground_truth' 등
- resource_id UUID NULL
- payload JSONB NULL
- ip_address INET NULL
- created_at TIMESTAMPTZ DEFAULT NOW()

※ P2/P3 테이블 (초안에서 생략 가능)
- ocr_template_regions (P2): 정규화된 region별 행
- ocr_template_table_guides (P3): colGuides 정규화
- ocr_run_table_rows (P3): tableRows 정규화
- ocr_run_warnings (P3): 경고 정규화
```

---

## 9. 미결정/추가 확인 필요

| 항목 | 질문 | 판단 기준 |
|---|---|---|
| 이메일 로그인 | users 테이블에 email 컬럼 추가 여부 | 현재 user_id 기반. 미래 이메일 인증 필요 여부 |
| 기존 데이터 이전 | localStorage history, groundtruth를 DB로 이전 스크립트 작성 여부 | 기존 데이터 보존 필요 시 마이그레이션 스크립트 |
| review_log.jsonl 이전 | audit_logs로 이전 여부 | event_type='auto_extract' 행 수 확인 후 결정 |
| 파일 서버 구현 | local filesystem 경로 (`uploads/`) 구현 여부 | DB schema는 storage_key로 준비, 파일 서버는 별도 |
| ocr_template_regions P2 | 즉시 정규화 vs P3 | template 수가 많아지면 jsonb 검색 필요 시 전환 |
| 사용자 가입 흐름 | 관리자만 사용자 추가 vs 셀프 가입 | users INSERT 권한 설계에 영향 |
| OCR 모델 메타 | model_id('paddleocr','easyocr' 등) 저장 위치 | ocr_run_results 또는 ocr_runs 컬럼 추가 |
