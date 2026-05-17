# DB-MVP-7TABLE-REVIEW 7개 테이블 MVP 구조 검토 리포트

> 작성일: 2026-05-17
> 작성자: Claude Code (DB-REVIEW-1)
> 선행 작업: DB-DESIGN-1 (14테이블 상세 설계), ARCH-1 (현황), OPS-1 (운영 완성도)
> 후속 작업: DB-2 (schema.sql 작성)
> 검토 범위: 사용자가 확정 후보로 선정한 MVP 7개 테이블

---

## 1. 생성 파일

| 파일 | 용도 |
|---|---|
| [docs/db/db_mvp_7table_review_20260517.md](docs/db/db_mvp_7table_review_20260517.md) | 사람이 검토하는 본 리포트 |
| [docs/db/db_mvp_7table_review_20260517.json](docs/db/db_mvp_7table_review_20260517.json) | 머신 리더블 메타데이터 (DB-2 자동 생성용) |

---

## 2. 전체 결론

### 2.1 현재 7개 테이블 적합 여부

✅ **결론: B안 — 7개 테이블 유지 + 컬럼 보완 필요**

7개 테이블 골격은 현재 화면(로그인/사이트/템플릿/RunOCR/히스토리/사업자기준값매칭/상세보기 수정)을 **모두 커버 가능**. 단, 다음 8개 컬럼 보완이 반드시 필요:

| # | 테이블 | 누락 컬럼 | 이유 |
|---|---|---|---|
| 1 | `ocr_templates` | `template_type` | 코드에 `template`/`unstructured`/`btemplate` 3종 분기 존재 (UploadWorkspace.runOcrTemplateMode, BTemplate 페이지) |
| 2 | `ocr_templates` | `output_fields` JSONB 별도 | 출력 필드 정의 (no/en/ko) vs 좌표(regions)를 분리해야 상세보기 출력필드 화면 채울 수 있음 |
| 3 | `ocr_runs` | `processing_time` NUMERIC | 히스토리 리스트 화면에 표시됨 (`HistoryWorkspace` 컬럼) |
| 4 | `ocr_runs` | `autofill_summary` JSONB | 현재 `HistoryRunRecord.autofill_summary`가 존재 (사업자번호 매칭 결과 요약) |
| 5 | `ocr_run_results` | `original_image_storage_key` / `processed_image_storage_key` 둘 다 | DetailHistoryView 좌측이 전처리 전/후 2장 동시 표시 |
| 6 | `ocr_run_results` | `autofill_run_status` 또는 `autofill_summary` JSONB | history detail에서 자동완성 상태 표시 필요 |
| 7 | `business_references` | `business_no_normalized` UNIQUE 컬럼 | `bizNumber.ts.normalizeBizNumber()` 결과 (`138-81-68468` 표준형)로 매칭 — 별도 컬럼 + UNIQUE 인덱스 필수 |
| 8 | `site_members` | `joined_at` TIMESTAMPTZ | 가입 시점 추적 (감사/UI용 기본 정보) |

### 2.2 수정 필요 여부

- **테이블 수 변경 없음** (7개 유지)
- **컬럼 8개 추가**
- 일부 컬럼 명칭 명확화 (`status` → 의미별 분리)

### 2.3 가장 중요한 보완점

**1순위**: `ocr_templates.template_type` 추가 — 현재 코드에 이미 3종 구분 로직(`template` / `unstructured` / `btemplate`) 존재. 누락 시 RunOCR 시 어떤 빌더 결과인지 구분 불가.

**2순위**: `business_references.business_no_normalized` — 사업자번호 정규화 형식(`138-81-68468`)로 UNIQUE 인덱스. 이 컬럼 없으면 매칭 성능 저하 + 중복 가능.

**3순위**: `ocr_run_results`에 original/processed image 둘 다 필요. 현재 `HistoryRunRecord`가 이미 `original_image_url`/`processed_image_url` 분리 구조.

### 2.4 schema.sql 작성 가능 여부

✅ **컬럼 보완 결정 8개 확정 후 즉시 작성 가능.**
단, [12. 사용자 최종 결정 항목](#12-사용자가-최종-결정해야-할-항목) 5개 확인 필요.

---

## 3. 최종 테이블 목록

| table | purpose | MVP 필수 여부 |
|---|---|---|
| `users` | 로그인 계정 + 마스터 권한 | ✅ 필수 |
| `sites` | 사이트/워크스페이스 마스터 | ✅ 필수 |
| `site_members` | 사용자-사이트 권한 매핑 | ✅ 필수 |
| `business_references` | 사업자번호 기준값 매칭 | ✅ 필수 |
| `ocr_templates` | 템플릿 정의 + 출력 필드 + 영역 좌표 | ✅ 필수 |
| `ocr_runs` | RunOCR 실행 히스토리 리스트 | ✅ 필수 |
| `ocr_run_results` | 히스토리 상세보기 전체 데이터 | ✅ 필수 |

---

## 4. 테이블별 상세 검토

### 4.1 users

#### 검토 결과
✅ **적합. 컬럼 보완 필요 없음.** (단 `email`은 nullable로 두는 게 유리)

#### 현재 대체 대상
- `ocr-server/data/users.json` (평문 비밀번호 즉시 폐기)
- localStorage `mysuit_ocr_login` (일부 — 사용자 식별 부분)

#### 현재 users.json 구조 vs DB 매핑
| 기존 (`users.json`) | DB (`users`) | 변환 |
|---|---|---|
| `user_id` | `username` | 그대로 |
| `user_pw` (평문) | `password_hash` | **bcrypt 변환 + 즉시 폐기** |
| `user_nm` | `display_name` | 그대로 |
| `adminYn=Y/N` | (별도 보관 안 함) | `site_members.role`로 표현 |
| `masterYn=Y` | `is_super_admin=true` | 마스터 1명만 true |
| `comp_cd`, `comp_nm` | (users에서 제거) | `sites.site_code`/`sites.site_name`으로 이관 |

#### user_sessions 제외 리스크
- **MVP 데모용으로는 허용 가능** — 단 다음 리스크 명시:
  - 서버 측 세션 강제 만료 불가
  - 토큰 무효화 불가
  - 다중 디바이스 로그인 추적 불가
  - localStorage 토큰 노출 시 보안 위험
- **외부 POC 직전에는 반드시 도입 권장**. 그 전까지 MVP 단계는 OK.

#### 권장 컬럼 확정

| 컬럼 | 타입 | 필수 | 메모 |
|---|---|---|---|
| `id` | UUID PK | ✅ | gen_random_uuid() |
| `username` | VARCHAR(64) UNIQUE | ✅ | 로그인 ID |
| `password_hash` | VARCHAR(60) | ✅ | bcrypt |
| `display_name` | VARCHAR(128) | ✅ | UI 표시명 |
| `is_super_admin` | BOOLEAN DEFAULT false | ✅ | 마스터 |
| `status` | VARCHAR(16) DEFAULT 'active' | ✅ | active/disabled |
| `last_login_at` | TIMESTAMPTZ | ❌ | 화면 표시용 |
| `created_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |

**email 제외** — MVP에서 `admin`/`user` 두 계정만 쓰는 데모. 후속에서 추가.

---

### 4.2 sites

#### 검토 결과
✅ **적합. 컬럼 보완 필요 없음.**

#### 현재 대체 대상
- Sidebar.tsx 하드코딩 옵션 (`사이트 A`, `사이트 B`, `사이트 C`)
- `users.json`의 `comp_cd`, `comp_nm` (사용자 → 사이트로 이관)

#### 운영 흐름
- 사용자가 직접 DB INSERT로 사이트 생성 가능 (MVP에서는 관리자가 SQL로 추가 OK)
- `site_code`는 식별자/URL용 (예: `mysuit`, `demo-a`)
- 이후 사이트 생성 UI 추가 시 재사용

#### parent_site_id 검토
- **MVP에서는 불필요**. 모회사/지점 구조는 현재 요구에 없음.
- 향후 필요 시 ALTER로 추가 가능.

#### settings JSONB 후보값
```json
{
  "default_document_type": "invoice_statement",
  "default_ocr_model": "paddleocr",
  "history_retention_days": 365,
  "allow_debug_preprocessing": false
}
```

#### 권장 컬럼 확정

| 컬럼 | 타입 | 필수 | 메모 |
|---|---|---|---|
| `id` | UUID PK | ✅ | |
| `site_name` | VARCHAR(128) | ✅ | 표시명 (`MySuit`) |
| `site_code` | VARCHAR(64) UNIQUE | ✅ | 식별자 (`mysuit`) |
| `status` | VARCHAR(16) DEFAULT 'active' | ✅ | active/suspended/archived |
| `settings` | JSONB | ❌ | 사이트 옵션 |
| `created_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `deleted_at` | TIMESTAMPTZ | ❌ | soft delete |

---

### 4.3 site_members

#### 검토 결과
✅ **적합. `joined_at` 컬럼 1개 추가 권장.**

#### 권한 흐름 (검토 결과: 충분)

```
1. Login (users 검증)
2. 토큰 발급 → localStorage 또는 cookie
3. 사이트 접근 시:
   if users.is_super_admin = true:
     모든 사이트 통과 (site_members 조회 생략 가능)
   else:
     SELECT * FROM site_members WHERE user_id = ? AND site_id = ?
     찾으면 role 확인 → 허용
     없으면 403
4. 사이트 선택 후 모든 쿼리에 WHERE site_id = ? 첨가
```

#### role 구분 — MVP에서 어디까지?

| role | MVP 데모 단계 |
|---|---|
| `owner` | 등록만 — 권한 분기는 미구현 OK |
| `admin` | 등록만 |
| `member` | 등록만 |
| `viewer` | 미사용 |

**추천**: MVP에서는 role 컬럼만 두고, 권한 분기 로직은 후속 (`is_super_admin` + `site_members 존재 여부`만 검증).

#### 권장 컬럼 확정

| 컬럼 | 타입 | 필수 | 메모 |
|---|---|---|---|
| `id` | UUID PK | ✅ | |
| `site_id` | UUID FK→sites.id ON DELETE CASCADE | ✅ | |
| `user_id` | UUID FK→users.id ON DELETE CASCADE | ✅ | |
| `role` | VARCHAR(16) DEFAULT 'member' | ✅ | owner/admin/member/viewer (CHECK) |
| `status` | VARCHAR(16) DEFAULT 'active' | ✅ | active/disabled |
| **`joined_at`** | TIMESTAMPTZ DEFAULT now() | ✅ | **신규 추가 권장** |
| `created_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |

**제약**: `UNIQUE(site_id, user_id)`, `CHECK (role IN ('owner','admin','member','viewer'))`

---

### 4.4 business_references

#### 검토 결과
⚠️ **적합 — 단 `business_no_normalized` 컬럼 추가 필수.**

#### 현재 흐름 분석 (코드 기반)

현재는 **별도 마스터 테이블 없이** `autofillEngine.collectInternalAutofillCandidates()`가 다음 두 소스를 reverse-derive:

1. **History 사용자 수정 데이터** ([autofillEngine.ts:297-328](mysuit-ocr/src/lib/autofillEngine.ts#L297-L328))
   - `readHistoryRuns()` 순회 → 각 run의 `output_fields` 중 `source="text"` 또는 modified ≠ original 인 행만 추출
   - 사업자번호 기준으로 필드 모음 빌드
2. **GroundTruth (사용자 정답값)** ([autofillEngine.ts:269-295](mysuit-ocr/src/lib/autofillEngine.ts#L269-L295))
   - localStorage `mysuit_ocr_groundtruth`에서 직접 읽음

`AUTOFILLABLE_FIELDS = ["회사명","사업자번호","대표자","tel","전화번호","주소"]`

#### 사업자번호 정규화 ([bizNumber.ts](mysuit-ocr/src/lib/bizNumber.ts))

- 입력: `138-81-68468`, `1388168468`, `138 81 68468`, `138.81.68468`, 또는 OCR 오인식 (`I→1`, `O→0` 등)
- 정규화 결과: 항상 `XXX-XX-XXXXX` 형식 (예: `138-81-68468`)
- 체크섬 검증 포함 (10번째 자리)

→ **DB에서도 동일 정규화 결과를 컬럼화하고 UNIQUE 인덱스 필수.**

#### 사이트별 격리 vs 전역

**추천: 사이트별 격리 (`site_id` 컬럼 보유)**.
이유:
- 같은 사업자번호도 사이트별로 기준값(회사명/주소)이 다를 수 있음 (지점/부서)
- 사이트 간 데이터 누수 방지
- 단, 향후 전역 마스터가 필요해지면 별도 `global_business_references` 추가 가능

#### 기준값 없을 때 흐름

- OCR이 사업자번호 인식 → `business_references` 매칭 시도
- 없으면 → autofill 후보 0 → output_fields는 OCR 원본값 그대로
- 사용자가 detail에서 수정 후 저장 → ocr_run_results.output_fields_result에 누적
- 향후 같은 사업자번호로 OCR 실행 시 → autofill 후보로 history 검색 (DB는 `ocr_run_results` 또는 신규 마스터 행 추가)

#### 권장 컬럼 확정

| 컬럼 | 타입 | 필수 | 메모 |
|---|---|---|---|
| `id` | UUID PK | ✅ | |
| `site_id` | UUID FK→sites.id ON DELETE CASCADE | ✅ | 사이트별 격리 |
| `business_no` | VARCHAR(32) | ✅ | 원본 입력 (참고용) |
| **`business_no_normalized`** | VARCHAR(12) | ✅ | **`138-81-68468` 형식 — UNIQUE 인덱스 키** |
| `company_name` | VARCHAR(256) | ❌ | 회사명/상호 |
| `ceo_name` | VARCHAR(128) | ❌ | 대표자 |
| `phone` | VARCHAR(32) | ❌ | 전화번호 |
| `address` | TEXT | ❌ | 주소 |
| `metadata` | JSONB | ❌ | 부가 필드 (업태/종목 등) |
| `is_active` | BOOLEAN DEFAULT true | ✅ | |
| `created_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |

**제약**: `UNIQUE(site_id, business_no_normalized)`

#### 자동완성과의 역할 분담

| 데이터 소스 | 우선순위 | 비고 |
|---|---|---|
| `business_references` (마스터) | **1순위** | 사이트 운영자가 정제한 기준값 — confidence 0.95+ |
| `ocr_run_results` 안 사용자 수정 데이터 (history) | 2순위 | autofillEngine처럼 누적 추출 — confidence 0.90+ |
| OCR 원본 | 3순위 | 매칭 없을 때 그대로 |

→ **마스터(`business_references`)가 있으면 즉시 매칭, 없으면 ocr_run_results JSONB 누적값에서 검색하는 2-tier 구조**. 두 소스 모두 사이트별 격리.

---

### 4.5 ocr_templates

#### 검토 결과
⚠️ **적합 — 단 다음 2개 컬럼 보완 필수.**

#### 보완 사항

##### 1. `template_type` 컬럼 신규 추가

[UploadWorkspace.tsx:117](mysuit-ocr/src/components/upload/UploadWorkspace.tsx#L117)에서 `runOcrTemplateMode: "template" | "unstructured"`로 분기.
[Sidebar.tsx:59](mysuit-ocr/src/components/layout/Sidebar.tsx#L59)에 `BTemplate`, `BHistory` 메뉴 존재.

→ 템플릿 종류:
- `template` — 영역 좌표 기반 (`TemplateBuilder.tsx`)
- `unstructured` — 비정형 (`UnstructuredBuilder.tsx`)
- `btemplate` — BTemplate 페이지 전용

##### 2. `output_fields` JSONB 별도 컬럼

현재 `templates.json` 구조는 영역(regions) 안에 `koField`/`enField`가 섞여 있고, 출력 필드 정의는 따로 명시되지 않음. 하지만 **상세보기 출력필드 화면**(영문/한글/원본/수정/정확도/일치)을 채우려면:

- **출력 필드 정의** (no, en, ko 매핑) — 사용자가 정의한 출력 스키마
- **영역 좌표** (regions/tableConfig) — 박스 위치

두 가지를 명확히 분리하는 게 매핑 단순화에 유리.

```json
// output_fields 예시
[
  {"no": 1, "en": "businessNo",   "ko": "사업자번호"},
  {"no": 2, "en": "companyName",  "ko": "회사명"},
  {"no": 3, "en": "ceoName",      "ko": "대표자"},
  {"no": 4, "en": "totalAmount",  "ko": "총합계금액"}
]
```

```json
// template_body 예시 (regions/tableConfig)
{
  "regions": [
    {"id":"field_1","type":"text","x":210,"y":224,"width":178,"height":51,"koField":"주문일자"},
    {"id":"table_1","type":"table","x":66,"y":621,"width":1515,"height":277,"koField":"품목표","options":{"colGuides":[...]}}
  ]
}
```

#### 현재 templates.json 구조 무손실 매핑 가능 여부

✅ **가능**. 매핑:

| 기존 (`templates.json`) | DB (`ocr_templates`) |
|---|---|
| `template_id` | `id` (UUID로 재발급) |
| `template_name` | `template_name` |
| `template_json.templateName` | `template_name` (중복 — DB는 컬럼만 사용) |
| `template_json.documentType` | `document_type` |
| `template_json.file.name` | `image_file_name` |
| `template_json.image.width` | `image_width` |
| `template_json.image.height` | `image_height` |
| `template_json.image.src` (base64) | **`image_storage_key`로 외부 분리** ⚠️ |
| `template_json.regions` | `template_body.regions` JSONB |
| (없음 — 신규) | `template_type` |
| (없음 — 신규) | `output_fields` |

##### ⚠️ image.src base64 문제

현재 `templates.json` 단일 파일이 **수십~수백 MB** 까지 커지는 원인은 각 템플릿의 `image.src` base64 데이터. DB JSONB에 그대로 넣으면:
- 행 1개당 수 MB
- WAL/replication 부담
- JSON 조회 시 매번 디스코딩

→ **`image_storage_key`로 외부 파일/객체스토리지 분리 필수**. `template_body`에서는 src 제거.

#### 권장 컬럼 확정

| 컬럼 | 타입 | 필수 | 메모 |
|---|---|---|---|
| `id` | UUID PK | ✅ | |
| `site_id` | UUID FK→sites.id ON DELETE CASCADE | ✅ | 사이트별 격리 |
| `template_name` | VARCHAR(128) | ✅ | 표시명 |
| **`template_type`** | VARCHAR(32) | ✅ | **`template`/`unstructured`/`btemplate`** |
| `document_type` | VARCHAR(64) | ✅ | invoice_statement, pos_receipt 등 |
| **`output_fields`** | JSONB | ❌ | **`[{no,en,ko}]` 출력 필드 정의** |
| `template_body` | JSONB | ✅ | regions/tableConfig 좌표 |
| `image_file_name` | VARCHAR(256) | ❌ | 원본 파일명 |
| `image_storage_key` | VARCHAR(512) | ❌ | base64 분리 저장 위치 |
| `image_width` | INTEGER | ✅ | 좌표 해석 |
| `image_height` | INTEGER | ✅ | 좌표 해석 |
| `is_active` | BOOLEAN DEFAULT true | ✅ | |
| `created_by` | UUID FK→users.id | ❌ | |
| `updated_by` | UUID FK→users.id | ❌ | |
| `created_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `deleted_at` | TIMESTAMPTZ | ❌ | soft delete |

**제약**: `UNIQUE(site_id, template_name)`, `CHECK (template_type IN ('template','unstructured','btemplate'))`

---

### 4.6 ocr_runs

#### 검토 결과
⚠️ **적합 — 단 `processing_time`, `autofill_summary` 2개 컬럼 보완 필수.**

#### 히스토리 리스트 화면 컬럼 매핑

| 화면 컬럼 | DB 컬럼 |
|---|---|
| No | (행 순번, 별도 컬럼 없음) |
| 템플릿명 | `template_name_snapshot` |
| 요청일시 | `request_at` 또는 `created_at` |
| 상태 | `status` |
| 파일명 | `file_name` |
| **(처리시간)** | **`processing_time`** ⚠️ |
| 상세보기 | (UI 액션) |
| 삭제 | (UI 액션) |

→ **`processing_time` 컬럼 신규 추가 필요** ([HistoryRunRecord.processing_time](mysuit-ocr/src/lib/historyStore.ts#L66)).

#### autofill_summary 누락 ⚠️

[HistoryRunRecord.autofill_summary](mysuit-ocr/src/lib/historyStore.ts#L76)에 다음 정보 보존:

```typescript
{
  status: "not_run" | "no_business_number" | "no_candidates" | "confirmed" | "corrected" | "applied",
  businessNumber?: string,
  candidateCount: number,
  confirmedCount: number,
  correctedCount: number,
  filledCount: number,
  skippedCount?: number,
  message?: string
}
```

→ **MVP에서 누락 불가**. 사업자번호 매칭 결과 요약은 운영/디버그에 필수.
**저장 위치 추천**: `ocr_runs.autofill_summary JSONB` (실행 단위 요약). 추가로 `ocr_run_results.autofill_summary`에 결과 단위 상세 저장 가능.

#### 다중 파일 처리

[UploadWorkspace.tsx](mysuit-ocr/src/components/upload/UploadWorkspace.tsx)는 `selectedFile: File | null` 단일 파일 흐름이 기본.
[HistoryRunRecord.file_name](mysuit-ocr/src/lib/historyStore.ts#L65) 단일 string.

→ **MVP는 1 run = 1 file로 충분**. `file_count` 컬럼은 운영 표시용으로만 (기본 1).

#### template_name_snapshot 필요성

- 템플릿이 나중에 이름 변경되거나 삭제되어도 히스토리는 당시 이름 그대로 표시해야 함
- `template_id` FK는 nullable + `template_name_snapshot`은 NOT NULL 권장

#### run_options JSONB 후보

```json
{
  "selected_model": "paddleocr",
  "template_mode": "template",
  "preprocessing": {
    "debug": false,
    "auto_apply": "limited"
  }
}
```

#### status 값

| 값 | 의미 |
|---|---|
| `pending` | 큐 대기 |
| `running` | OCR 진행 중 |
| `success` | 성공 (기존 RunStatus와 매핑) |
| `fail` | 실패 |
| `partial` | 일부 성공 (다중 파일 시) |

**참고**: 기존 `historyStore.RunStatus = "success"|"fail"` → DB의 `success`/`fail`로 1:1 매핑. running/pending은 신규 도입.

#### 권장 컬럼 확정

| 컬럼 | 타입 | 필수 | 메모 |
|---|---|---|---|
| `id` | UUID PK | ✅ | 기존 job_id 대체 |
| `site_id` | UUID FK→sites.id | ✅ | |
| `user_id` | UUID FK→users.id | ✅ | 실행자 |
| `template_id` | UUID FK→ocr_templates.id | ❌ | nullable (템플릿 없는 자유 실행) |
| `template_name_snapshot` | VARCHAR(128) | ❌ | 삭제/이름변경 대비 |
| `request_at` | TIMESTAMPTZ DEFAULT now() | ✅ | 요청 시각 |
| `status` | VARCHAR(16) | ✅ | pending/running/success/fail/partial |
| `file_name` | VARCHAR(512) | ❌ | 대표 파일명 |
| `file_count` | INTEGER DEFAULT 1 | ✅ | 다중 파일 대비 |
| `document_type` | VARCHAR(64) | ❌ | |
| **`processing_time`** | NUMERIC(8,3) | ❌ | **초 단위, 화면 표시용** |
| `run_options` | JSONB | ❌ | preprocessing/모델 옵션 |
| **`autofill_summary`** | JSONB | ❌ | **사업자번호 매칭 결과 요약** |
| `summary` | JSONB | ❌ | totalFiles/successCount 등 |
| `created_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `deleted_at` | TIMESTAMPTZ | ❌ | soft delete |

---

### 4.7 ocr_run_results

#### 검토 결과
⚠️ **적합 — 단 image storage key 분리 + autofill_summary 보완 필수.**

#### 상세보기 화면 매핑

| 화면 위치 | 데이터 | DB 컬럼 |
|---|---|---|
| 좌측 상단 | 전처리 전 이미지 | **`original_image_storage_key`** ⚠️ |
| 좌측 하단 | 전처리 후 이미지 | **`processed_image_storage_key`** ⚠️ |
| 우측 상단 (출력 필드) | no/en/ko/original/modified/confidence/일치 | `output_fields_result` JSONB |
| 우측 하단 (OCR 데이터) | name/en/ko/value/confidence/bbox | `raw_ocr_data` JSONB |

기존 [HistoryRunRecord](mysuit-ocr/src/lib/historyStore.ts#L61-L77)가 이미 `original_image_url`/`processed_image_url` 분리 + `image_storage_mode` 구조 — **DB에서는 두 storage_key 둘 다 컬럼화 필수**.

#### output_fields_result JSONB 구조

[HistoryOutputField](mysuit-ocr/src/lib/historyStore.ts#L20-L43) 그대로:

```json
[
  {
    "no": 1,
    "en": "businessNo",
    "ko": "사업자번호",
    "original": "138-81-68468",
    "modified": "138-81-68468",
    "confidence": 0.97,
    "source": "ocr" | "biz" | "gt" | "text",
    "applied": "138-81-68468",
    "autofillAction": "filled" | "corrected" | "confirmed" | "none",
    "suggestions": [
      {
        "source": "biz",
        "value": "138-81-68468",
        "confidence": 0.95,
        "sourceType": "history" | "groundTruth" | "cache",
        "fileName": "6.pdf",
        "templateName": "거래_6",
        "hitCount": 3
      }
    ]
  }
]
```

#### raw_ocr_data JSONB 구조

[HistoryOcrField](mysuit-ocr/src/lib/historyStore.ts#L10-L18):

```json
[
  {
    "name": "field_1",
    "en": "businessNo",
    "ko": "사업자번호",
    "field_type": "text",
    "value": "138-81-68468",
    "confidence": 0.97,
    "bbox": [x, y, w, h]
  }
]
```

#### 거래명세서 tableRows

invoice_statement의 표 row는 `output_fields_result` 또는 `table_data` JSONB.
**MVP에서는 `table_data` JSONB로 분리 권장** (검색 시 명확):

```json
{
  "tableMeta": { "rowCount": 7, "colCount": 5 },
  "tableRows": [
    {"no":1, "item":"옷걸이", "qty":10, "unit_price":1000, "amount":10000},
    ...
  ]
}
```

#### 검색용 일반 컬럼 (정규화)

| 컬럼 | 이유 |
|---|---|
| `business_no` | 사업자번호 매칭 인덱스. JSONB에서 풀면 GIN/expression index 필요 |
| `primary_name` | 회사명/거래처명. 운영 검색용 |
| `total_amount` | 합계금액. 통계/필터 |

→ **추출하기 쉬운 핵심값만 일반 컬럼으로 빼고, 나머지는 JSONB 그대로**.

#### 다중 파일 시 행 개수

- 1 run에 여러 파일 → 파일 1개당 `ocr_run_results` 1행 (`run_id` FK + N개 행)
- MVP는 1 run = 1 file이라 N=1
- 다중 파일 지원해도 같은 구조로 확장 가능 — **별도 ocr_run_files 불필요**

#### 권장 컬럼 확정

| 컬럼 | 타입 | 필수 | 메모 |
|---|---|---|---|
| `id` | UUID PK | ✅ | |
| `site_id` | UUID FK→sites.id | ✅ | |
| `run_id` | UUID FK→ocr_runs.id ON DELETE CASCADE | ✅ | |
| `template_id` | UUID FK→ocr_templates.id | ❌ | |
| `original_file_name` | VARCHAR(512) | ✅ | |
| **`original_image_storage_key`** | VARCHAR(512) | ❌ | **전처리 전 이미지** |
| **`processed_image_storage_key`** | VARCHAR(512) | ❌ | **전처리 후 이미지** |
| `document_type` | VARCHAR(64) | ❌ | |
| `detected_doc_type` | VARCHAR(64) | ❌ | classifier 추정 |
| `status` | VARCHAR(16) | ✅ | success/fail/partial/needs_review |
| `business_no` | VARCHAR(12) | ❌ | 검색 인덱스 |
| `primary_name` | VARCHAR(256) | ❌ | 회사명/거래처명 |
| `total_amount` | NUMERIC(18,2) | ❌ | 합계금액 |
| `raw_text` | TEXT | ❌ | OCR raw text 전체 |
| `error_message` | TEXT | ❌ | 실패 시 |
| `output_fields_result` | JSONB | ❌ | **출력필드 (수정 데이터 포함)** |
| `raw_ocr_data` | JSONB | ❌ | **OCR 원본 필드들** |
| `table_data` | JSONB | ❌ | tableRows + tableMeta |
| `preprocessing_debug` | JSONB | ❌ | debug/auto-apply 시에만 |
| **`autofill_summary`** | JSONB | ❌ | **상세보기에서 자동완성 상태 표시** |
| `warnings_summary` | JSONB | ❌ | {error:0,warning:2,info:1} |
| `metadata` | JSONB | ❌ | 부가 정보 |
| `created_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | ✅ | |

**제약**: `UNIQUE(run_id, original_file_name)` (1 run에서 같은 파일명 중복 방지)
**인덱스**: `INDEX(site_id, business_no)`, `INDEX(site_id, created_at DESC)`, `GIN(output_fields_result)`

#### 사용자 수정값 저장 흐름

```
1. RunOCR 실행 → ocr_run_results INSERT
   output_fields_result = [{original: "ABC", modified: "ABC", source: "ocr"}, ...]
2. 사용자가 상세보기에서 수정
   output_fields_result[i].modified = "수정값"
   output_fields_result[i].source = "text"
3. 저장 클릭 → UPDATE ocr_run_results SET output_fields_result = ?
4. (선택) 사용자 수정값을 business_references 마스터에 반영하는 별도 UI/API 가능
   → MVP는 자동 반영 안 함. 사용자가 의도적으로 마스터에 등록할 때만.
```

→ **별도 ocr_corrected_fields 테이블 불필요. JSONB 안에서 처리 가능.**

---

## 5. 컬럼 최종 후보 (요약)

상세는 [4장](#4-테이블별-상세-검토) 참조. 각 테이블 새 컬럼만 강조:

| 테이블 | 추가 컬럼 | 타입 | 이유 |
|---|---|---|---|
| `users` | (변경 없음) | - | - |
| `sites` | (변경 없음) | - | - |
| `site_members` | `joined_at` | TIMESTAMPTZ | 가입 시점 추적 |
| `business_references` | `business_no_normalized` | VARCHAR(12) | UNIQUE 매칭 키 |
| `ocr_templates` | `template_type` | VARCHAR(32) | template/unstructured/btemplate 구분 |
| `ocr_templates` | `output_fields` | JSONB | 출력 필드 정의 분리 |
| `ocr_runs` | `processing_time` | NUMERIC(8,3) | 화면 표시 |
| `ocr_runs` | `autofill_summary` | JSONB | 매칭 결과 요약 |
| `ocr_run_results` | `original_image_storage_key` | VARCHAR(512) | 전처리 전 이미지 |
| `ocr_run_results` | `processed_image_storage_key` | VARCHAR(512) | 전처리 후 이미지 |
| `ocr_run_results` | `autofill_summary` | JSONB | 자동완성 상태 |

---

## 6. JSONB 컬럼 사용 기준

⚠️ **중요**: 여기서 말하는 JSONB는 **PostgreSQL JSONB 컬럼**입니다 — 별도 JSON 파일 저장이 아닙니다. SQL로 직접 조회/수정 가능하며, GIN 인덱스 지원.

### 6.1 일반 컬럼 vs JSONB 판단 기준

| 데이터 | 일반 컬럼/JSONB | 이유 |
|---|---|---|
| id, 이름, 상태, 시각 | 일반 컬럼 | 항상 필요한 핵심값, 인덱싱 표준 |
| 사업자번호(검색) | 일반 컬럼 (`business_no`) | 검색/매칭 빈도 매우 높음 |
| 회사명(검색) | 일반 컬럼 (`primary_name`) | 운영 검색 |
| 합계금액 | 일반 컬럼 (`total_amount`) | 정렬/필터 자주 |
| 사용자 수정 출력 필드 | JSONB (`output_fields_result`) | 행 수 가변 + 필드별 메타가 풍부 (suggestions[] 등) |
| OCR raw fields | JSONB (`raw_ocr_data`) | bbox 등 가변 |
| 표 row 데이터 | JSONB (`table_data`) | rowCount 가변, doctype별 다름 |
| 템플릿 좌표 | JSONB (`template_body`) | 형상 변경 자유 |
| 사이트/실행 옵션 | JSONB (`settings`, `run_options`) | 자주 확장됨 |
| 자동완성 요약 | JSONB (`autofill_summary`) | 작은 객체, 자주 변경 |
| 전처리 디버그 | JSONB (`preprocessing_debug`) | 가끔 저장, 가변 구조 |
| 경고 요약 | JSONB (`warnings_summary`) | `{error:0,warning:2}` 작음 |

### 6.2 JSONB 검색/수정 가능 여부

```sql
-- 검색
SELECT * FROM ocr_run_results
WHERE output_fields_result @> '[{"en": "businessNo", "modified": "138-81-68468"}]';

-- 부분 업데이트 (수정 데이터만 변경)
UPDATE ocr_run_results
SET output_fields_result = jsonb_set(
  output_fields_result,
  '{0,modified}',
  '"새로운값"'
)
WHERE id = ?;

-- 인덱스
CREATE INDEX ON ocr_run_results USING GIN (output_fields_result);
```

→ **JSONB는 검색/수정 모두 가능**. 단, 매우 빈번한 필드는 일반 컬럼으로 빼는 게 빠름.

### 6.3 MVP JSONB 시작 → 후속 정규화 전략

- **MVP**: JSONB 단일 컬럼 (스키마 변경 자유)
- **운영 중 발견되면**: 자주 쓰는 필드를 별도 컬럼/테이블로 정규화
  - 예: tableRows 검색 빈번 → `ocr_run_table_rows` 후속 테이블
  - 예: template regions 단위 통계 필요 → `ocr_template_regions` 후속 테이블
- **남용 위험**: 모든 데이터를 JSONB로 두면 검색 어렵고 인덱스 어려움 → **검색/정렬/필터에 자주 쓰는 핵심값은 일반 컬럼**

---

## 7. 화면별 DB 매핑

| 화면/기능 | 조회 테이블 | 저장/수정 테이블 | 설명 |
|---|---|---|---|
| **로그인** | `users` | (선택) `users.last_login_at` UPDATE | username + password_hash 검증 |
| **사이트 드롭다운** | `sites`, `site_members` | - | `is_super_admin=true`면 sites 전체, 아니면 site_members로 필터 |
| **템플릿 목록** | `ocr_templates` | - | `WHERE site_id = $current_site_id AND deleted_at IS NULL` |
| **템플릿 생성/수정** | `ocr_templates` | INSERT/UPDATE `ocr_templates` | template_body JSONB 통째 갱신 |
| **RunOCR 실행** | `sites`, `ocr_templates`, `business_references` | INSERT `ocr_runs` + `ocr_run_results` | run 1행, result 파일당 1행 |
| **사업자번호 매칭** | `business_references` (1순위), `ocr_run_results.output_fields_result` (2순위) | - | normalized 키로 매칭 |
| **히스토리 리스트** | `ocr_runs` JOIN `ocr_run_results`(파일명) | - | site_id 필터 + 페이지네이션 |
| **히스토리 상세보기** | `ocr_runs`, `ocr_run_results` | - | run_id로 result 조회 |
| **상세보기 수정 저장** | `ocr_run_results` | UPDATE `ocr_run_results.output_fields_result` | JSONB partial update |
| **히스토리 삭제** | - | UPDATE `ocr_runs.deleted_at` (soft) | 또는 hard delete |

---

## 8. 권한/사이트 격리 흐름

### 8.1 흐름

```
1. POST /auth/login → users.username/password_hash 검증
2. 토큰 발급 (MVP: localStorage, 후속: cookie + user_sessions)
3. GET /sites → 
   if users.is_super_admin: SELECT * FROM sites
   else: SELECT s.* FROM sites s JOIN site_members m ON m.site_id=s.id WHERE m.user_id=$me
4. 사이트 선택 → current_site_id (localStorage 또는 메모리)
5. 모든 후속 쿼리에 WHERE site_id = $current_site_id 첨가
   if super_admin: site_id 조건 우회 가능
```

### 8.2 MVP role 분기 권장

- **MVP**: `site_members` 존재 여부만 검증 (있으면 통과). role 분기 미구현 OK.
- **후속**: owner/admin/member/viewer별 권한 매트릭스 구현.
- **데모 admin 사이트**: admin 계정 1개 + super_admin = true → site_members 없어도 모든 사이트 접근. 사실상 권한 분기 없이 동작.

---

## 9. 사업자번호 기준값 매칭 흐름

```
[RunOCR 실행]
  ↓
[OCR이 사업자번호 인식: bizNumber.extractBizNumber()]
  ↓
[정규화: "138-81-68468" 형식]
  ↓
[1순위] business_references 마스터 조회
  SELECT * FROM business_references
  WHERE site_id=? AND business_no_normalized='138-81-68468' AND is_active=true;
  ↓ 매칭 성공
  output_fields_result[i].suggestions += {source:"biz", confidence:0.95, sourceType:"groundTruth"}
  AUTOFILLABLE_FIELDS 자동 채움 (회사명/대표자/전화/주소)

[2순위] history 누적 데이터 조회 (마스터 매칭 실패 또는 보강)
  SELECT output_fields_result FROM ocr_run_results
  WHERE site_id=? AND business_no='138-81-68468'
  ORDER BY created_at DESC LIMIT 20;
  → 사용자 수정 데이터 (source="text") 추출
  → suggestions[i].sourceType = "history", hitCount 누적
  → 동일 키 값별 confidence 가중

[적용]
  ↓
[ocr_runs.autofill_summary 저장: status/candidateCount/filledCount...]
[ocr_run_results.output_fields_result 저장: 매칭된 값을 modified에 채움]
[ocr_run_results.autofill_summary 저장: detail 화면 표시용]
```

→ **business_references 마스터 + ocr_run_results 누적값** 2-tier로 충분. 별도 cache 테이블 불필요.

---

## 10. 상세보기 수정값 저장 흐름

```
[히스토리 상세보기 진입]
  ↓
[GET /sites/:siteId/history/:runId → ocr_run_results 조회]
  ↓
[화면 렌더: output_fields_result → 우측 상단 출력 필드 표]
[화면 렌더: raw_ocr_data → 우측 하단 OCR 데이터 표]
[화면 렌더: original/processed_image_storage_key → 좌측 이미지 2장]
  ↓
[사용자가 수정 데이터 input 변경]
  ↓ (DetailHistoryView.handleModify)
  outputs[idx].modified = newValue
  outputs[idx].source = "text"
  ↓ (사용자 "저장" 클릭)
  PUT /sites/:siteId/history/:runId/results/:resultId
    body: { output_fields_result: [...수정된 배열...] }
  ↓
  UPDATE ocr_run_results
    SET output_fields_result = $jsonb,
        updated_at = now()
    WHERE id = ? AND site_id = ?;
  ↓
[(선택) business_references에 반영하는 별도 UI 제공 가능]
  - MVP: 자동 반영 안 함 (사용자가 의도적으로 마스터 등록 버튼 누를 때만)
  - 자동 반영 도입은 후속 (학습 데이터 누적 정책 결정 필요)
```

→ **별도 `ocr_corrected_fields` 테이블 불필요**. JSONB partial update로 충분.

---

## 11. 제외한 테이블 검토

| excluded table | 제외 이유 | 리스크 | 다시 필요한 시점 |
|---|---|---|---|
| `user_sessions` | MVP 데모용은 localStorage 토큰으로 충분 | 강제 만료/무효화 불가, XSS 위험 | **외부 POC 직전 즉시** |
| `ocr_corrected_fields` | output_fields_result JSONB로 처리 | 행 단위 수정 이력 추적 어려움 | 감사/학습 데이터 명세 시 |
| `ocr_run_files` | 1 run = 1 file 흐름이라 ocr_run_results 행 하나로 충분 | 다중 파일 + 파일별 메타(MIME/checksum) 분리 어려움 | 다중 파일 업로드 운영 도입 시 |
| `ocr_template_regions` | template_body JSONB로 처리 | 영역 단위 통계/부분 수정 어려움 | 영역별 분석 UI 도입 시 |
| `ocr_template_table_guides` | template_body JSONB로 처리 | colGuides 단위 운영 분석 어려움 | T-10 후속 표 분석 도입 시 |
| `ocr_run_table_rows` | table_data JSONB로 처리 | 행 단위 검색/편집 어려움 | 행 단위 검토 워크플로 도입 시 |
| `ocr_run_warnings` | warnings_summary JSONB로 처리 | 경고 추세 분석 어려움 | 품질 대시보드 도입 시 |
| `audit_logs` | review_log.jsonl 유지 (현재 작동 중) | 보안 감사 한계 | **MVP 직후 P2 즉시** |
| `user_preferences` | localStorage `mysuit_ocr_theme` 유지 | 마지막 선택 사이트 영구 보존 불가 | 멀티사이트 UX 정착 시 |

### 제외 가능 여부 종합 판단

✅ **MVP 단계(데모)에서는 모두 제외 가능**.
⚠️ 단 외부 POC 직전에는 `user_sessions`, `audit_logs` 최소 2개 도입 권장.

---

## 12. 사용자가 최종 결정해야 할 항목

| # | 항목 | 추천 | 대안 | 영향 |
|---|---|---|---|---|
| **R1** | `ocr_templates.template_type` 컬럼 추가 | ✅ 추가 (`template`/`unstructured`/`btemplate`) | 통합 컬럼 없이 `template_body.kind`로만 보관 | 누락 시 RunOCR 분기 어려움 — **반드시 결정** |
| **R2** | `ocr_templates.output_fields` 컬럼 분리 | ✅ 분리 (JSONB 별도) | `template_body` 안에 포함 | 분리하면 상세보기 출력필드 매핑 단순. **추천** |
| **R3** | `business_references.business_no_normalized` UNIQUE | ✅ 필수 | 정규화 없이 raw `business_no` UNIQUE | 정규화 안 하면 `138-81-68468` vs `1388168468` 중복 발생 |
| **R4** | 이미지 storage 추상화 prefix | `local://` / `s3://` 추상화 | 단순 경로 문자열 | 후속 객체스토리지 전환 용이성 |
| **R5** | 사이트별 `business_references` 격리 vs 전역 | ✅ 사이트별 (site_id 보유) | 전역 마스터 | 사이트 간 데이터 누수 방지. 향후 전역 마스터 별도 가능 |
| **R6** | 사용자 수정값 → business_references 자동 반영 | ❌ MVP는 자동 반영 안 함 | 자동 학습 (history 누적 → 마스터 자동 갱신) | 자동 학습은 정책 정의 후 후속 |
| **R7** | history 삭제 정책 | soft delete (`deleted_at`) | hard delete | 복구 가능 vs 디스크 절약 |
| **R8** | run-result 관계 | 1 run = 1 file (MVP) | 1 run = N files (다중 업로드) | MVP는 1:1로 가도 무방. 향후 N으로 확장 시 같은 구조 |

---

## 13. 다음 작업 판단

### 13.1 schema.sql 작성 가능 여부

✅ **가능. 단 12장 R1~R5 5개 항목 확정 후 진행.**

R6~R8은 운영 정책에 가깝고, 컬럼 자체에는 영향 없음 (deleted_at은 이미 포함).

### 13.2 schema 작성 전 사용자 확인 필요 항목

1. **R1**: `template_type` 컬럼명/값 셋 확정 (현재 코드와 일치하는지)
2. **R2**: `output_fields`를 `ocr_templates`에서 분리할지, `template_body`에 포함할지
3. **R3**: `business_no_normalized` 컬럼명/길이 (VARCHAR(12) 권장)
4. **R4**: storage_key URI 형식 (`local://`/`s3://`)
5. **R5**: `business_references` 사이트별 격리 (`site_id NOT NULL`) 확정

### 13.3 DB-2 (schema.sql)에서 해야 할 일

1. PostgreSQL 16+ 기준 DDL 작성
2. 모든 PK는 `UUID DEFAULT gen_random_uuid()`
3. 모든 timestamp는 `TIMESTAMPTZ DEFAULT now()`
4. JSONB 컬럼에 GIN 인덱스 (자주 검색하는 키만)
5. `UNIQUE`/`CHECK` 제약 모두 명시
6. `updated_at` 자동 갱신 트리거 1개
7. 마이그레이션 시드 SQL 별도:
   - 기본 super_admin 1명
   - 기본 사이트 1개 (`mysuit` 또는 `demo`)
   - admin → 기본 사이트 owner로 `site_members` 등록
8. 인덱스 권장:
   - `users(username)` UNIQUE
   - `sites(site_code)` UNIQUE
   - `site_members(site_id, user_id)` UNIQUE
   - `business_references(site_id, business_no_normalized)` UNIQUE
   - `ocr_templates(site_id, template_name)` UNIQUE
   - `ocr_runs(site_id, created_at DESC)`
   - `ocr_run_results(site_id, business_no)`, `(run_id)`
   - GIN: `ocr_run_results(output_fields_result)`, `(raw_ocr_data)`

### 13.4 DB-3 이후 마이그레이션 작업

- `users.json` → `users` (bcrypt 변환)
- `templates.json` → `ocr_templates` (base64 src → image_storage_key 분리)
- `history.json` + localStorage history → `ocr_runs` + `ocr_run_results`
- localStorage `mysuit_ocr_groundtruth` → 사용자 수정 데이터로 `ocr_run_results.output_fields_result`에 반영 (또는 별도 검토)
