# OCR 프로젝트 localStorage → DB 전환 분석 리포트

> 생성일: 2026-05-16  
> 작업: DB-1 분석 전용 (코드 수정 없음)

---

## 1. 결론 요약

### DB 전환이 필요한 핵심 이유

| 이유 | 현황 | 위험 |
|---|---|---|
| 보안 | accessToken·user 정보가 localStorage에 평문 저장 | XSS 공격으로 토큰 탈취 가능 |
| 보안 | users.json에 비밀번호 평문 저장 | 파일 노출 시 전체 계정 유출 |
| 데이터 손실 | 브라우저 캐시 삭제 시 templates/history 소멸 | 운영 불가 |
| 용량 한계 | localStorage 5~10MB 한도. templates.json 이미 2.6MB | quota exceeded 발생 중 |
| 멀티 디바이스 | 기기 간 데이터 공유 불가 | 협업 불가 |
| 감사 | review_log.jsonl 13MB 단일 파일 → 쿼리/필터 불가 | 운영 분석 어려움 |

### 우선 전환 대상 (Priority 순)

1. 🔴 **인증/사용자** — users.json 평문 비밀번호, localStorage accessToken
2. 🔴 **템플릿** — localStorage `mysuit_ocr_templates` + backend `data/templates.json`
3. 🟠 **OCR 실행 이력** — localStorage `mysuit_ocr_history` + backend `data/history.json`
4. 🟡 **Ground truth** — localStorage `mysuit_ocr_groundtruth`
5. 🟢 **사용자 설정** — localStorage `mysuit_ocr_theme` 등 UI 상태

### localStorage 유지 가능 대상

- 테마 설정 (`mysuit_ocr_theme`)
- 마지막 선택 탭, 필터 상태, 화면 접힘 상태 등 휘발성 UI 상태

---

## 2. localStorage / sessionStorage 사용처 전수 조사

### 5개 고유 storage key 발견, sessionStorage/IndexedDB 사용 없음

| 영역 | 파일 | Storage Key | 저장 데이터 | DB 전환 | 보안 | 비고 |
|---|---|---|---|---|---|---|
| Auth | `lib/login.ts` | `mysuit_ocr_login` | accessToken, user_id, user_nm, adminYn, masterYn, comp_cd, comp_nm, envMysuitUrl | ✅ 필수 | 🔴 위험 | XSS로 토큰 탈취 가능 |
| Template | `OcrAnnotator.tsx` `UnstructuredBuilder.tsx` `UploadWorkspace.tsx` `app/template/page.tsx` | `mysuit_ocr_templates` | template_id, template_name, template_json(regions, documentType, colGuides) | ✅ 필수 | 🟡 중간 | 2.6MB 이미 초과 위험 |
| History | `lib/historyStore.ts` | `mysuit_ocr_history` | job_id, file_name, template_name, OCR fields, table rows, 처리시간, status | ✅ 필수 | 🟡 중간 | Quota exceeded 핸들링 이미 구현됨 |
| Ground Truth | `lib/groundTruthStore.ts` `lib/autofillEngine.ts` | `mysuit_ocr_groundtruth` | template::file 복합키 → 확인된 필드값 맵 | ✅ 권장 | 🟢 낮음 | autofill 제안 소스 |
| UI 테마 | `lib/theme.ts` `app/layout.tsx` | `mysuit_ocr_theme` | "light" \| "dark" | ❌ 유지 | 🟢 없음 | 손실 영향 없음 |

---

## 3. 화면별 저장 데이터 분석

### 3-1. Template 탭

**현재 저장 방식:**
- Frontend: localStorage `mysuit_ocr_templates`
- Backend: `data/templates.json` (2.6MB, base64 이미지 내장)

**저장되는 핵심 구조:**
```json
{
  "template_id": "TPL-95328E52",
  "template_name": "거래_6",
  "updated_at": "2026-05-15 16:19:02",
  "template_json": {
    "templateName": "거래_6",
    "documentType": "invoice_statement",
    "file": { "name": "6.pdf" },
    "image": { "width": 1653, "height": 1167, "src": "data:image/jpeg;base64,..." },
    "regions": [
      { "id": "field_1", "fieldType": "field", "x": 939, "y": 399, "width": 112, "height": 46, "koField": "대표자명" },
      { "id": "table_1", "fieldType": "table", "x": 66, "y": 621, "width": 1515, "height": 277,
        "table": { "mode": "repeat", "colGuides": [...], "expectedColumns": {...} } }
    ]
  }
}
```

**문제점:**
- base64 이미지가 template_json 안에 내장되어 크기 급증
- templates.json 단일 파일이 2.6MB → 저장할수록 증가
- 사용자별 분리 없음 (전체 공유)

**DB 전환 시 분리 필요 테이블:**
- `ocr_templates` — 기본 정보
- `ocr_template_regions` — 각 region (field/table)
- `ocr_template_table_guides` — colGuides / tableExpectedColumns
- 이미지는 별도 파일 스토리지 (S3/MinIO) 또는 DB BLOB

---

### 3-2. RunOCR 탭

**현재 저장 방식:**
- 파일 업로드: 메모리만 (디스크 저장 없음)
- OCR 결과: JSON 응답으로만 반환 (영속 저장 없음)
- 실행 후 History에 기록

**저장/전달하는 데이터:**
- 업로드 파일 (multipart, in-memory)
- 선택한 template_id → `/ocr/extract` API 전달
- 선택한 model_id → API 전달
- documentType → API 전달
- regions JSON → API 전달
- OCR 결과: documentFields, tableRows, tableMeta, extractDebug

**DB 전환 포인트:**
- `ocr_runs` — 실행 자체 기록
- `ocr_run_files` — 업로드 파일 메타 (파일 자체는 스토리지)
- `ocr_run_results` — 결과 JSON 영구 저장

---

### 3-3. History 탭

**현재 저장 방식:**
- Frontend localStorage: `mysuit_ocr_history` (최대 50건, quota exceeded 시 자동 축소)
- Backend: `data/history.json` (단순 job 메타만, OCR 결과 없음)

**Frontend history 구조:**
```typescript
{
  job_id: string;           // OCR-XXXXXXXX
  file_name: string;
  template_name: string | null;
  processing_time: number;
  created_at: string;
  status: "success" | "fail";
  image_url?: string;       // 이미 deprecated
  ocr_fields?: HistoryOcrField[];    // 전체 필드
  output_fields?: HistoryOutputField[];
  autofill_summary?: object;
}
```

**문제점:**
- 브라우저 별도 관리 → 기기 간 공유 불가
- Quota exceeded로 자동 삭제 발생
- OCR 원문(base64 이미지) 포함 시 빠른 용량 초과

---

### 3-4. Login / Auth

**현재 저장 방식:**
```typescript
// localStorage 'mysuit_ocr_login'
{
  accessToken: string;  // JWT 또는 세션 토큰
  user_id: string;
  user_nm: string;
  adminYn: "Y" | "N";
  masterYn: "Y" | "N";
  comp_cd: string;
  comp_nm: string;
  envMysuitUrl: string;
  envMagellanVersion: string;
}
```

**Backend users.json:**
```json
[
  { "user_id": "admin", "user_pw": "1234", "user_nm": "관리자", "adminYn": "Y", "comp_cd": "MYSUIT" }
]
```

**보안 문제:**
1. 🔴 accessToken → localStorage 저장: XSS 취약
2. 🔴 users.json 평문 비밀번호: 파일 노출 시 즉시 탈취
3. 🟡 refreshToken 미사용: 장기 세션 관리 없음
4. 🟡 httpOnly 쿠키 미사용: CSRF 대비 없음

---

### 3-5. Site 탭

**현재 상태:** localStorage에 site 관련 키 없음. 사이트 개념이 `comp_cd`/`comp_nm`으로 암묵적으로 존재하지만 별도 site 관리 화면/테이블 없음.

**DB 설계 시 필요:**
- `sites` 테이블 — comp_cd를 site_code로 공식화
- `site_members` — 사용자-사이트 소속 관계
- template/history를 site 기준으로 분리

---

### 3-6. Test 탭 (후속 논의 필요)

**현재 상태:** Test 탭은 `/api/ocr-cache`, `/api/ground-truth`, `/api/autofill-cache` API를 통해 `public/data/testsets/*/` 파일을 직접 읽고 씁니다.

**localStorage 사용:** Test 탭 자체는 localStorage를 사용하지 않음. 단, `mysuit_ocr_groundtruth`를 autofillEngine이 읽어 사용함.

**후속 논의:**
- testset manifest/ground_truth를 DB로 이전할지 파일 기반 유지할지 결정 필요
- Test 탭은 개발/검증 목적이므로 파일 기반 유지가 더 적합할 수 있음

---

## 4. DB 전환 대상 분류

| 분류 | 데이터 | 이유 |
|---|---|---|
| **A. 반드시 DB** | users.json 사용자/비밀번호 | 평문 저장 보안 위험 |
| **A. 반드시 DB** | localStorage accessToken → httpOnly 쿠키 전환 | XSS 방어 |
| **A. 반드시 DB** | templates (localStorage + templates.json) | 영구 보존 + 멀티 디바이스 |
| **A. 반드시 DB** | OCR history (localStorage + history.json) | 재조회 + 용량 한계 |
| **B. DB 권장** | groundtruth (localStorage) | 기기 간 공유, 자동학습 기반 |
| **B. DB 권장** | review_log.jsonl | 쿼리 가능한 구조 필요 |
| **B. DB 권장** | site 개념 (comp_cd → sites 테이블) | 멀티 사이트 확장 |
| **C. localStorage 유지** | mysuit_ocr_theme | 손실 영향 없음 |
| **C. localStorage 유지** | 탭 선택 상태, 필터 상태 | 휘발성 OK |
| **D. 저장 금지** | accessToken in localStorage | XSS 위험 |
| **D. 저장 금지** | users.json 평문 비밀번호 | 즉시 제거 필요 |
| **D. 저장 금지** | 대용량 base64 이미지 in localStorage | Quota 유발 |

---

## 5. ERD 초안

```
users ──────────────────────────────────┐
  id, email, user_id, name              │
  password_hash, salt                    │
  role(admin/user/viewer)               │
  comp_cd, created_at, last_login_at    │
        │                               │
        ├──────────────────┐            │
        │                  │            │
sites ──┘               site_members    │
  id, site_code           id            │
  site_name               site_id ──────┤
  owner_user_id ──────────user_id ──────┘
  settings JSON
  created_at
        │
        ├─────────────────────────────┐
        │                             │
ocr_templates ──────────────── ocr_runs
  id (TPL-XXXXXXXX)              id (OCR-XXXXXXXX)
  site_id                        site_id
  owner_user_id                  user_id
  template_name                  template_id ──→ ocr_templates.id
  document_type                  document_type
  is_active                      model_id
  image_ref (파일 경로)          status
  created_at, updated_at         started_at, completed_at
        │                        error_message
        │                               │
ocr_template_regions           ocr_run_files
  id                             id
  template_id                    run_id
  field_key                      original_filename
  field_label_ko/en              stored_path
  field_type (field/table)       file_type
  x, y, width, height            page_count
  page_no, sort_order                    │
  region_options JSON            ocr_run_results
        │                        id
ocr_template_table_guides        run_id
  id                             doc_type_detected
  region_id                      document_fields JSON
  col_guides JSON                table_meta JSON
  row_guide_type                 raw_response JSON
  table_expected_columns JSON    confidence_summary JSON
  table_profile                          │
                                 ocr_run_table_rows
                                   id, run_id
                                   row_index
                                   row_data JSON
                                   extraction_source
                                   warning_count
                                         │
                                 ocr_run_warnings
                                   id, run_id
                                   field_key
                                   warning_type
                                   message, severity

ocr_ground_truth
  id
  site_id
  template_id
  file_name
  field_key
  confirmed_value
  confirmed_at
  confirmed_by_user_id

user_preferences
  id, user_id
  pref_key (theme, last_tab, etc.)
  pref_value
  updated_at

audit_logs
  id, user_id, site_id
  action (template_save, ocr_run, login, etc.)
  target_type, target_id
  payload JSON
  created_at
```

---

## 6. 테이블별 컬럼 설계 초안

### users

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID / BIGINT PK | 내부 식별자 |
| user_id | VARCHAR(50) UNIQUE | 로그인 ID (admin, user 등) |
| email | VARCHAR(255) UNIQUE | 이메일 (OAuth 연동 시) |
| user_nm | VARCHAR(100) | 표시명 |
| password_hash | VARCHAR(255) | bcrypt/argon2 해시 |
| password_salt | VARCHAR(64) | 솔트 |
| role | ENUM('admin','user','viewer') | 전역 역할 |
| comp_cd | VARCHAR(50) | 소속 회사 코드 |
| created_at | TIMESTAMP | 생성일 |
| last_login_at | TIMESTAMP | 최근 로그인 |

인덱스: `user_id`, `email`

---

### sites

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID / BIGINT PK | |
| site_code | VARCHAR(50) UNIQUE | comp_cd 마이그레이션 대상 |
| site_name | VARCHAR(200) | 표시명 |
| owner_user_id | FK → users.id | 소유자 |
| settings | JSON/JSONB | 사이트별 설정 |
| created_at | TIMESTAMP | |

---

### site_members

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT PK | |
| site_id | FK → sites.id | |
| user_id | FK → users.id | |
| role | ENUM('admin','member','viewer') | |
| status | ENUM('active','invited','suspended') | |
| joined_at | TIMESTAMP | |

UNIQUE(site_id, user_id)

---

### ocr_templates

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | VARCHAR(20) PK | "TPL-XXXXXXXX" 기존 형식 유지 |
| site_id | FK → sites.id | |
| owner_user_id | FK → users.id | |
| template_name | VARCHAR(200) | |
| document_type | VARCHAR(50) | invoice_statement, tax_invoice 등 |
| version | INT DEFAULT 1 | |
| is_active | BOOLEAN | |
| original_filename | VARCHAR(500) | 기준 이미지 파일명 |
| image_ref | VARCHAR(1000) | 파일 스토리지 경로 (base64 제거) |
| image_width | INT | |
| image_height | INT | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| deleted_at | TIMESTAMP NULL | soft delete |

인덱스: `site_id`, `document_type`, `is_active`

---

### ocr_template_regions

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| template_id | FK → ocr_templates.id | |
| region_id | VARCHAR(50) | "field_1", "table_1" 기존 ID |
| field_type | ENUM('field','table','text') | |
| field_key | VARCHAR(100) | koField 매핑 key |
| field_label_ko | VARCHAR(200) | |
| field_label_en | VARCHAR(200) | |
| x | FLOAT | |
| y | FLOAT | |
| width | FLOAT | |
| height | FLOAT | |
| page_no | INT DEFAULT 1 | |
| sort_order | INT | |
| region_options | JSON/JSONB | 기타 옵션 |

인덱스: `template_id`, `field_type`

---

### ocr_template_table_guides

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| region_id | FK → ocr_template_regions.id | |
| table_profile | VARCHAR(50) | multi_item_table 등 |
| table_mode | ENUM('repeat','fixed') | |
| col_guides | JSON/JSONB | colGuides 배열 |
| col_x | JSON/JSONB | colX 배열 |
| table_expected_columns | JSON/JSONB | required/optional/display |
| termination_keywords | JSON/JSONB | 종료 키워드 |

---

### ocr_runs

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | VARCHAR(20) PK | "OCR-XXXXXXXX" |
| site_id | FK → sites.id | |
| user_id | FK → users.id | |
| template_id | FK → ocr_templates.id NULL | |
| document_type | VARCHAR(50) | |
| model_id | VARCHAR(100) | |
| status | ENUM('running','success','fail','timeout') | |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP NULL | |
| processing_time_sec | FLOAT | |
| error_message | TEXT NULL | |

인덱스: `site_id`, `user_id`, `template_id`, `status`, `started_at`

---

### ocr_run_files

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| run_id | FK → ocr_runs.id | |
| original_filename | VARCHAR(500) | |
| stored_path | VARCHAR(1000) NULL | 파일 스토리지 경로 |
| file_type | VARCHAR(20) | jpg/pdf/png 등 |
| file_size | BIGINT | bytes |
| page_count | INT NULL | PDF 페이지 수 |
| checksum | VARCHAR(64) NULL | SHA-256 |

---

### ocr_run_results

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| run_id | FK → ocr_runs.id UNIQUE | 1:1 |
| doc_type_detected | VARCHAR(50) | OCR이 분류한 타입 |
| doc_type_source | ENUM('explicit','template','classified') | |
| document_fields | JSON/JSONB | 상단 필드 (회사명, 금액 등) |
| table_meta | JSON/JSONB | extractionSource, rowCount 등 |
| row_count | INT | |
| raw_response | JSON/JSONB | 전체 OCR API 응답 |
| confidence_summary | JSON/JSONB | |

---

### ocr_run_table_rows

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| run_id | FK → ocr_runs.id | |
| row_index | INT | |
| item_code | VARCHAR(200) NULL | |
| item_name | VARCHAR(500) NULL | |
| quantity | VARCHAR(50) NULL | |
| unit_price | VARCHAR(50) NULL | |
| amount | VARCHAR(50) NULL | |
| row_data | JSON/JSONB | 전체 row (canonical columns) |
| extraction_source | VARCHAR(100) | template_colguides 등 |
| warning_count | INT DEFAULT 0 | |

인덱스: `run_id`, `row_index`

---

### ocr_run_warnings

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| run_id | FK → ocr_runs.id | |
| field_key | VARCHAR(100) | insuranceCode 등 |
| warning_type | VARCHAR(100) | ocr_source_missing 등 |
| warning_key | VARCHAR(200) | "insuranceCode:ocr_source_missing" |
| message | TEXT | 전체 경고 문자열 |
| severity | ENUM('info','warn','error') DEFAULT 'warn' | |

인덱스: `run_id`, `warning_type`

---

### ocr_ground_truth

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| site_id | FK → sites.id | |
| template_id | FK → ocr_templates.id NULL | |
| file_name | VARCHAR(500) | |
| composite_key | VARCHAR(700) | template_name::file_name |
| field_key | VARCHAR(100) | |
| confirmed_value | TEXT | |
| confirmed_at | TIMESTAMP | |
| confirmed_by | FK → users.id | |

UNIQUE(composite_key, field_key)

---

### user_preferences

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| user_id | FK → users.id | |
| pref_key | VARCHAR(100) | theme, last_tab 등 |
| pref_value | TEXT | JSON 문자열 또는 단순값 |
| updated_at | TIMESTAMP | |

UNIQUE(user_id, pref_key)

---

### audit_logs

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| user_id | FK → users.id NULL | |
| site_id | FK → sites.id NULL | |
| action | VARCHAR(100) | template_save, ocr_run, login 등 |
| target_type | VARCHAR(50) | template, run, user 등 |
| target_id | VARCHAR(100) | 대상 ID |
| payload | JSON/JSONB | 상세 변경 정보 |
| ip_address | VARCHAR(45) | |
| created_at | TIMESTAMP | |

인덱스: `user_id`, `site_id`, `action`, `created_at`

---

## 7. API 설계 초안

### Auth

```
POST /api/auth/login
  body: { user_id, password }
  response: { accessToken (httpOnly cookie 또는 응답 body), user }
  ⚠ accessToken은 httpOnly 쿠키로 전환 권장

POST /api/auth/logout
  응답: 쿠키 삭제

GET  /api/auth/me
  응답: 현재 사용자 정보

POST /api/auth/refresh
  응답: 새 accessToken
```

### Site

```
GET  /api/sites
GET  /api/sites/:siteId
POST /api/sites
PUT  /api/sites/:siteId
GET  /api/sites/:siteId/members
POST /api/sites/:siteId/members
```

### Template

```
GET    /api/sites/:siteId/templates          (목록)
GET    /api/templates/:templateId            (상세)
POST   /api/templates                        (생성)
PUT    /api/templates/:templateId            (수정)
DELETE /api/templates/:templateId            (삭제, soft)
POST   /api/templates/:templateId/duplicate  (복제)
GET    /api/templates/:templateId/regions    (region 목록)
```

### OCR Run

```
POST /api/ocr/runs                         (실행, multipart)
GET  /api/ocr/runs/:runId                  (결과 조회)
GET  /api/sites/:siteId/ocr-runs           (이력 목록, 필터/페이지)
DELETE /api/ocr-runs/:runId                (삭제)
POST /api/ocr-runs/:runId/retry            (재실행)
```

### Ground Truth

```
GET  /api/ground-truth?templateId=&fileName=
POST /api/ground-truth
DELETE /api/ground-truth?compositeKey=&fieldKey=
```

---

## 8. localStorage → DB migration 전략

### Phase 1: DB Schema 준비 (DB-2)
- PostgreSQL 또는 MySQL 선택 확정
- 테이블 생성 SQL 작성 및 실행
- 기존 `data/*.json` 파일 백업

### Phase 2: Backend API 구현 (DB-3)
- FastAPI 기존 JSON 읽기/쓰기 → DB 읽기/쓰기로 전환
- `/templates` API → ocr_templates 테이블
- `/login` API → users 테이블 (비밀번호 해시화)
- `/ocrSelect|Insert|Update|Delete` → ocr_runs/results 테이블

### Phase 3: Frontend Template 탭 DB 연동 (DB-4)
- localStorage `mysuit_ocr_templates` → API 호출로 전환
- 읽기: `GET /api/sites/:siteId/templates`
- 쓰기: `POST /api/templates`, `PUT /api/templates/:id`

### Phase 4: History / Auth / GT DB 연동 (DB-5)
- `mysuit_ocr_history` → API 호출
- `mysuit_ocr_login` accessToken → httpOnly 쿠키
- `mysuit_ocr_groundtruth` → DB

### Phase 5: 기존 localStorage 데이터 Import (DB-6)
- 로그인 시 localStorage 잔존 데이터 감지
- 서버 import API 제공 → 일회성 이전
- 이전 완료 후 localStorage key 삭제
- 실패 시 fallback: localStorage 읽기 우선 임시 유지

### 중복 처리 전략
- template_name + site_id UNIQUE 충돌 → "복사본 (날짜)" 자동 생성
- history job_id 충돌 → 최신 것 유지

---

## 9. 보안/개인정보 고려

| 항목 | 현재 위험 | 해결 방안 |
|---|---|---|
| accessToken in localStorage | 🔴 XSS 탈취 가능 | httpOnly 쿠키 + CSRF 방어 |
| users.json 평문 비밀번호 | 🔴 즉시 파일 노출 시 전계정 유출 | bcrypt/argon2 해시화 |
| 개인정보 포함 OCR 결과 | 🟡 브라우저에 장기 보관 | 보존 기간 정책 (90일/1년) |
| base64 이미지 in localStorage | 🟡 대용량 + 캐시 클리어 취약 | 파일 스토리지 분리 |
| refreshToken 없음 | 🟡 세션 만료 처리 없음 | refreshToken 구현 권장 |

---

## 10. 우선순위 제안

### Priority 1 (즉시) — 보안 위험
- users.json 비밀번호 해시화 (bcrypt)
- accessToken → httpOnly 쿠키 전환

### Priority 2 (단기) — 데이터 안전성
- Template DB화 (ocr_templates, ocr_template_regions, ocr_template_table_guides)
- templates.json에서 base64 이미지 분리

### Priority 3 (중기) — 기능 확장
- OCR History DB화 (ocr_runs, ocr_run_results, ocr_run_table_rows, ocr_run_warnings)
- Ground Truth DB화

### Priority 4 (장기) — 운영 개선
- Site 개념 공식화 (sites, site_members)
- review_log.jsonl → audit_logs DB
- user_preferences DB화

### Priority 5 (후속 논의)
- Test 탭 testset metadata DB화 여부 결정
- OCR 결과 파일 스토리지 (S3/MinIO) 연동

---

## 11. 다음 구현 단계

| 작업 | 설명 |
|---|---|
| DB-2 | DB 선택 확정 + Schema SQL 작성 |
| DB-3 | Backend API DB 연동 (FastAPI + SQLAlchemy/asyncpg) |
| DB-4 | Frontend Template 탭 API 전환 |
| DB-5 | History/RunOCR/Auth API 전환 |
| DB-6 | localStorage → DB import 도구 |
| DB-7 | 보안 강화 (httpOnly 쿠키, 비밀번호 해시) |

---

## 부록: 코드 수정 없음 확인

이번 DB-1 작업은 분석 전용으로 코드 수정이 없습니다.

**생성 파일:**
- `mysuit-ocr/docs/db_migration_analysis_ocr_project_20260516.md` (이 파일)
- `mysuit-ocr/docs/db_migration_analysis_ocr_project_20260516.json`

**수정된 소스 파일:** 없음
