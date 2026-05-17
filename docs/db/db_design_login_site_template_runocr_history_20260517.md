# DB-DESIGN-1 로그인/사이트/템플릿/RunOCR/히스토리 DB화 상세 설계

> 작성일: 2026-05-17
> 작성자: Claude Code (DB-DESIGN-1)
> 상태: 검토용 초안 (schema.sql 작성 전 단계)
> 선행 작업: ARCH-1 (localStorage/JSON 현황), OPS-1 (운영 완성도 분석)
> 후속 작업: DB-2 (schema.sql 작성), DB-3 (FastAPI 연동), DB-4 (마이그레이션)

---

## 1. 생성 파일

| 파일 | 용도 |
|---|---|
| `docs/db/db_design_login_site_template_runocr_history_20260517.md` | 사람이 검토하는 본 설계서. 모든 의사결정과 근거를 자연어로 기술 |
| `docs/db/db_design_login_site_template_runocr_history_20260517.json` | 머신 리더블 메타데이터. 후속 schema.sql 자동 생성/검증에 사용 가능 |

---

## 2. 전체 결론

### 2.1 필요한 테이블 수

- **MVP 필수 (P0~P1)**: 8개
  - users, sessions, sites, site_members, ocr_templates, ocr_runs, ocr_run_files, ocr_run_results
- **권장 운영 (P2)**: 4개
  - ocr_template_regions, ocr_template_table_guides, audit_logs, user_preferences
- **확장 후속 (P3)**: 2개
  - ocr_run_table_rows, ocr_run_warnings

**총 14개 (기존 계획 유지). 단, MVP 출시는 8개만으로 가능.**

### 2.2 핵심 설계 원칙

1. **사이트 중심 격리** — 업무 데이터(template/run/result/history)는 모두 `site_id`를 보유한다. 사용자가 아니라 사이트가 데이터의 소유자다.
2. **JSONB 우선, 정규화 보류** — template_body, document_fields, options, summary 등은 JSONB로 저장하고, 운영 안정화 이후 검색/집계 필요성이 확인된 항목만 별도 컬럼/테이블로 정규화한다.
3. **storage_key 추상화** — 원본 파일은 DB에 저장하지 않는다. `storage_key` 컬럼에 `local://…`, `s3://…` 형태의 URI만 저장하고, 실제 저장소는 어댑터로 추상화한다.
4. **세션은 서버 측 검증 가능해야 한다** — localStorage 토큰을 그대로 옮기지 않고, sessions 테이블 + httpOnly cookie 조합으로 전환할 수 있는 구조로 설계한다.
5. **super_admin은 사이트 멤버십 없이도 통과** — 마스터 계정은 `users.is_super_admin = true` 한 플래그로 모든 사이트 RLS를 우회한다.

### 2.3 가장 중요한 결정

| # | 결정 | 추천 |
|---|---|---|
| D1 | 템플릿 영역/표 가이드를 즉시 정규화할 것인가, JSONB로 둘 것인가 | **template_body JSONB 우선. regions/table_guides는 P2 후속.** |
| D2 | 비밀번호 저장 방식 | **bcrypt 해시 (`password_hash VARCHAR(60)`). 평문 즉시 폐기.** |
| D3 | 세션 토큰 저장 방식 | **`session_token_hash` (SHA-256) 저장. 평문 토큰은 클라이언트만 보유.** |
| D4 | super_admin 표현 | **`users.is_super_admin BOOLEAN`. 별도 role 테이블 만들지 않는다.** |
| D5 | run/file/result 관계 | **1 run → N files → 1:1 result (파일 1개당 결과 1건).** |
| D6 | preprocessing_debug 저장 시점 | **`debugPreprocessing=true` 또는 `productionApplied=true`일 때만 저장.** 항상 저장하면 용량 부담. |
| D7 | tableRows 별도 테이블 | **MVP는 `document_fields JSONB`에 포함. 행 단위 검색/수정 요구 발생 시 P3 분리.** |
| D8 | warnings 별도 테이블 | **MVP는 `warnings_summary JSONB`로 충분. 운영 분석 단계에서 P3 분리.** |
| D9 | audit_logs 우선순위 | **P2 권장. review_log.jsonl 대체 + 보안 감사. MVP 직후 즉시 도입 권장.** |
| D10 | user_preferences 우선순위 | **P2. theme 정도는 localStorage 유지해도 무방하나, "마지막 선택 사이트" 기능 위해 P2 권장.** |

---

## 3. 이번 DB화 범위

| 영역 | 포함 여부 | 이유 | 후속 여부 |
|---|---|---|---|
| Login / Auth | ✅ 포함 | users.json 평문 비밀번호 즉시 제거 필요. 가장 큰 보안 병목 (OPS-1) | - |
| Site / Workspace | ✅ 포함 | Sidebar 드롭다운 → 실제 격리 기능화. 모든 업무 데이터의 소유자 | - |
| Template 탭 | ✅ 포함 | templates.json + localStorage 이원화 해소. 사이트별 격리 필요 | - |
| RunOCR 탭 | ✅ 포함 | run 단위 추적, 다중 파일 처리 구조 필요 | - |
| History 탭 | ✅ 포함 | localStorage 50건/5MB 한계 해소. ocr_runs/files/results 기반 조회 | - |
| Test 탭 / TestWorkspace | ❌ 제외 | testset/manifest 구조가 별도. RunAll 결과는 DB 미저장이 합리적 | 후속 DB-FUTURE-TEST |
| testset manifest | ❌ 제외 | 정적 데이터셋 메타데이터. 파일 시스템 유지가 적절 | 후속 후보 |
| GroundTruth | ❌ 제외 | 현재 localStorage `template::file` key 기반. Template/History와 연결 가능성만 기록 | 후속 DB-FUTURE-GT |
| OCR 인식 로직 / parser / preprocessing | ❌ 제외 | CLAUDE.md "OCR 인식 로직 변경 금지" 정책 준수 | - |
| audit_logs | ⚠️ 운영 권장 (P2) | review_log.jsonl 대체. MVP 필수 아니나 보안 감사상 강력 권장 | P2 즉시 |
| user_preferences | ⚠️ 운영 권장 (P2) | theme/last_site 등. MVP 필수 아님 | P2 |

---

## 4. 전체 구조 요약 (텍스트 ERD)

```
[users] ──< [sessions]
   │
   ├──< [site_members] >── [sites]
   │                          │
   │                          ├──< [ocr_templates]
   │                          │        ├──< [ocr_template_regions]
   │                          │        └──< [ocr_template_table_guides]
   │                          │
   │                          ├──< [ocr_runs] ──< [ocr_run_files]
   │                          │        │              │
   │                          │        │              └──< [ocr_run_results]
   │                          │        │                          ├──< [ocr_run_table_rows]   (P3)
   │                          │        │                          └──< [ocr_run_warnings]    (P3)
   │                          │        │
   │                          │        └── (template_id nullable)
   │                          │
   │                          └──< [audit_logs] (site_id nullable)
   │
   └──< [user_preferences]
```

관계 요약:
- `users 1 ── N sessions`
- `users N ── M sites` (via `site_members`)
- `sites 1 ── N ocr_templates`
- `ocr_templates 1 ── N ocr_template_regions`
- `ocr_template_regions 1 ── N ocr_template_table_guides` (또는 templates 직접)
- `sites 1 ── N ocr_runs`
- `ocr_runs 1 ── N ocr_run_files`
- `ocr_run_files 1 ── 1 ocr_run_results` (파일당 결과 1건 가정)
- `ocr_run_results 1 ── N ocr_run_table_rows` (P3)
- `ocr_run_results 1 ── N ocr_run_warnings` (P3)

---

## 5. 권한 구조

### 5.1 전역 권한 (users.is_super_admin)

- **super_admin**
  - 모든 사이트 접근 가능 (site_members 멤버십 없어도 통과)
  - 모든 사용자 관리 가능 (생성/비활성화/권한 변경)
  - 모든 템플릿/히스토리/OCR 결과 접근 가능
  - audit_logs 전체 조회 가능
  - 운영자/마스터 계정 (기존 `users.json`의 `masterYn=Y` 대체)

### 5.2 사이트별 권한 (site_members.role)

| role | 멤버 관리 | 사이트 설정 | 템플릿 관리 | RunOCR 실행 | History 조회 | History 삭제 |
|---|---|---|---|---|---|---|
| `owner` | ✅ 전체 | ✅ | ✅ | ✅ | ✅ 전체 | ✅ |
| `admin` | ⚠️ 제한 (owner 제외) | ⚠️ 일부 | ✅ | ✅ | ✅ 전체 | ✅ |
| `member` | ❌ | ❌ | ⚠️ 사용만 | ✅ | ⚠️ 본인 + 사이트 공개분 | ⚠️ 본인 |
| `viewer` | ❌ | ❌ | ❌ | ❌ | ⚠️ 조회만 | ❌ |

### 5.3 권한 적용 흐름

```
1. 요청자 = users.is_super_admin → 모든 사이트 통과
2. 요청자 ∈ site_members(site_id, user_id) → role 확인 후 권한 매핑
3. 그 외 → 403
```

---

## 6. 테이블별 상세 설계

### 6.1 users

- **용도**: 전역 사용자 마스터. 로그인 ID/비밀번호 해시/마스터 권한 보유.
- **사용 화면**: Login, 사용자 관리, Site 멤버 초대 시 user lookup
- **왜 필요한가**:
  - 현재 `users.json` 평문 비밀번호 즉시 폐기 (OPS-1 최대 병목)
  - admin 계정의 "마스터" 개념을 `is_super_admin`으로 표현
  - 사용자는 여러 사이트에 속할 수 있으므로 사이트와 분리된 전역 엔티티
- **site_id 필요 여부**: ❌ 불필요 (전역 엔티티)
- **주요 관계**:
  - `1 ── N sessions`
  - `1 ── N site_members`
  - `1 ── N audit_logs` (user_id, nullable)
  - `1 ── N user_preferences`
  - `1 ── N ocr_runs` (실행 주체)

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | `gen_random_uuid()` |
| `username` | VARCHAR(64) UNIQUE | ✅ | 로그인 ID (`admin`, `user`) | 기존 `user_id` 대응 |
| `email` | VARCHAR(255) UNIQUE | ❌ | 이메일 로그인/알림 확장 | nullable. MVP는 미사용해도 무방 |
| `display_name` | VARCHAR(128) | ✅ | UI 표시 이름 (`관리자`) | 기존 `user_nm` 대응 |
| `password_hash` | VARCHAR(60) | ✅ | bcrypt 해시 | bcrypt 결과는 정확히 60자 |
| `is_super_admin` | BOOLEAN | ✅ | 마스터 계정 여부 | 기존 `masterYn` 대응. 기본 `false` |
| `status` | VARCHAR(16) | ✅ | `active` / `disabled` / `pending` | 기본 `active` |
| `last_login_at` | TIMESTAMPTZ | ❌ | 마지막 로그인 시각 | UI 운영 표시용 |
| `created_at` | TIMESTAMPTZ | ✅ | 생성 시각 | `now()` |
| `updated_at` | TIMESTAMPTZ | ✅ | 갱신 시각 | trigger로 자동 갱신 |
| `deleted_at` | TIMESTAMPTZ | ❌ | soft delete | nullable. 즉시 hard delete 안 함 |

#### 권한/보안 메모

- 평문 비밀번호는 절대 저장하지 않는다.
- 마이그레이션 시 `users.json`의 평문 `user_pw`는 bcrypt 해시로 변환 후 즉시 폐기.
- `is_super_admin = true`인 사용자는 RLS/권한 체크에서 우선 통과.
- `comp_cd`, `comp_nm` (기존) → `users`에 두지 않고 `sites`/`site_members`로 표현한다.

#### 예시 데이터

```json
{
  "id": "8a2c...uuid",
  "username": "admin",
  "email": null,
  "display_name": "관리자",
  "password_hash": "$2b$12$...60chars",
  "is_super_admin": true,
  "status": "active",
  "last_login_at": "2026-05-17T09:00:00+09:00",
  "created_at": "2026-05-17T00:00:00+09:00",
  "updated_at": "2026-05-17T09:00:00+09:00",
  "deleted_at": null
}
```

#### 설계 메모

- **email은 nullable** — MVP에서 `admin` 계정은 이메일 없을 수 있음.
- **username UNIQUE** — 대소문자 구분은 citext 또는 `LOWER()` 인덱스로 정리.
- **지금 필수**: P0.

---

### 6.2 sessions

- **용도**: 로그인 세션 저장. localStorage accessToken 대체.
- **사용 화면**: Login, 모든 인증이 필요한 API 호출
- **왜 필요한가**:
  - 현재 localStorage token은 서버 측 검증/만료/강제 로그아웃 불가능
  - httpOnly cookie + 서버 측 세션 테이블로 전환 가능한 구조 필요
- **site_id 필요 여부**: ❌ 불필요. 단 `current_site_id`로 "현재 작업 중인 사이트"는 저장 가능.
- **주요 관계**: `N ── 1 users`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `user_id` | UUID FK→users.id | ✅ | 소유 사용자 | ON DELETE CASCADE |
| `session_token_hash` | VARCHAR(64) UNIQUE | ✅ | 토큰의 SHA-256 해시 | 평문 토큰은 클라이언트만 보유 |
| `expires_at` | TIMESTAMPTZ | ✅ | 만료 시각 | 일반 7~30일 |
| `revoked_at` | TIMESTAMPTZ | ❌ | 강제 만료 시각 | 로그아웃/관리자 강제 만료 |
| `ip_address` | INET | ❌ | 발급 시 IP | 감사/보안 |
| `user_agent` | TEXT | ❌ | 발급 시 UA | 감사/보안 |
| `current_site_id` | UUID FK→sites.id | ❌ | 현재 작업 중인 사이트 | nullable. UI 편의용 |
| `created_at` | TIMESTAMPTZ | ✅ | 발급 시각 | |
| `last_seen_at` | TIMESTAMPTZ | ❌ | 마지막 사용 시각 | 활성 세션 추적 |

#### 보안 권장

- **토큰은 해시 저장 권장** — DB 유출 시에도 토큰 재사용 불가.
- **로그아웃** = `revoked_at = now()` (행 삭제하지 않음 — 감사 흔적 유지)
- **강제 만료** = 동일 (관리자가 특정 사용자의 모든 세션을 `revoked_at` 설정)
- **유효성 검사** = `revoked_at IS NULL AND expires_at > now()`

#### 설계 메모

- JWT를 채택하지 않는 이유: 강제 만료/세션 무효화가 어렵고, 현 구조에서 stateful 세션이 더 적합.
- **지금 필수**: P0.

---

### 6.3 sites

- **용도**: 사이트/워크스페이스 마스터. 모든 업무 데이터의 소유자.
- **사용 화면**: Sidebar 드롭다운, Site 설정 화면(미구현→구현 예정), 모든 업무 화면의 헤더
- **왜 필요한가**:
  - 현재 Sidebar에 드롭다운만 있고 실제 격리 기능 없음 (ARCH-1)
  - 템플릿/RunOCR/History를 사이트별로 분리해야 함
  - 멀티테넌시의 기준점
- **site_id 필요 여부**: 자기 자신이므로 N/A
- **주요 관계**:
  - `1 ── N site_members`
  - `1 ── N ocr_templates`
  - `1 ── N ocr_runs`
  - `1 ── N audit_logs`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `name` | VARCHAR(128) | ✅ | 사이트 표시 이름 | `MySuit`, `Acme Corp` |
| `slug` | VARCHAR(64) UNIQUE | ✅ | URL/식별자 | `mysuit`, `acme-corp` (kebab-case) |
| `owner_user_id` | UUID FK→users.id | ✅ | 사이트 소유자 | 최소 1명. site_members에도 owner role로 등록 |
| `status` | VARCHAR(16) | ✅ | `active` / `suspended` / `archived` | 기본 `active` |
| `settings` | JSONB | ❌ | 사이트 설정 | 기본 documentType, 보존기간, 전처리 정책 등 |
| `created_at` | TIMESTAMPTZ | ✅ | 생성 시각 | |
| `updated_at` | TIMESTAMPTZ | ✅ | 갱신 시각 | |
| `deleted_at` | TIMESTAMPTZ | ❌ | soft delete | |

#### settings JSONB 예시

```json
{
  "default_document_type": "invoice_statement",
  "retention_days": 90,
  "default_preprocessing_policy": "auto",
  "allow_debug_preprocessing": true,
  "max_run_files": 50
}
```

#### 설계 메모

- **owner_user_id는 반드시 site_members(role='owner')에도 동시 등록** — 트리거 또는 애플리케이션 책임.
- **slug 변경 정책**: 가급적 immutable. URL 일관성을 위함.
- 기존 `users.json`의 `comp_cd`, `comp_nm` → 첫 마이그레이션 시 `sites.slug`/`sites.name`으로 이관.
- **지금 필수**: P0.

---

### 6.4 site_members

- **용도**: 사용자-사이트 멤버십 + 사이트별 권한.
- **사용 화면**: Site 멤버 관리, 모든 권한 체크 미들웨어
- **왜 필요한가**:
  - 같은 사용자가 사이트마다 다른 role을 가질 수 있어야 함
  - `(site_id, user_id)` 조합으로 접근 가능 여부 즉시 확인
- **site_id 필요 여부**: ✅ 필수
- **주요 관계**: `N ── 1 sites`, `N ── 1 users`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | 소속 사이트 | ON DELETE CASCADE |
| `user_id` | UUID FK→users.id | ✅ | 사용자 | ON DELETE CASCADE |
| `role` | VARCHAR(16) | ✅ | `owner`/`admin`/`member`/`viewer` | CHECK 제약 |
| `invited_by` | UUID FK→users.id | ❌ | 초대한 사람 | 감사용. nullable (초기 가입) |
| `joined_at` | TIMESTAMPTZ | ✅ | 가입 확정 시각 | 초대 수락 시점 |
| `status` | VARCHAR(16) | ✅ | `active` / `invited` / `disabled` | 기본 `active` |
| `created_at` | TIMESTAMPTZ | ✅ | 행 생성 시각 | |
| `updated_at` | TIMESTAMPTZ | ✅ | 갱신 시각 | |

#### 제약

- `UNIQUE(site_id, user_id)` — 한 사용자는 한 사이트에 한 번만 등록.
- `CHECK (role IN ('owner','admin','member','viewer'))`

#### 권한 요약 (5.2와 동일, 재게재)

| role | 멤버 관리 | 사이트 설정 | 템플릿 관리 | RunOCR 실행 | History 조회 |
|---|---|---|---|---|---|
| owner | ✅ 전체 | ✅ | ✅ | ✅ | ✅ 전체 |
| admin | ⚠️ owner 제외 | ⚠️ 일부 | ✅ | ✅ | ✅ 전체 |
| member | ❌ | ❌ | ⚠️ 사용만 | ✅ | ⚠️ 본인 + 공개 |
| viewer | ❌ | ❌ | ❌ | ❌ | ⚠️ 조회만 |

#### 설계 메모

- **super_admin은 site_members 없이도 통과** — 단, UI 일관성을 위해 자동 멤버 행을 생성하는 옵션도 가능 (선택).
- **지금 필수**: P0.

---

### 6.5 ocr_templates

- **용도**: 템플릿 마스터. 사이트별 격리.
- **사용 화면**: Template 탭, RunOCR 탭(템플릿 선택), History 탭(템플릿명 표시)
- **왜 필요한가**:
  - 현재 templates.json + localStorage 이원화 해소
  - 사이트별 격리
  - documentType, image 크기 등 좌표 해석에 필수 정보 저장
- **site_id 필요 여부**: ✅ 필수
- **주요 관계**:
  - `N ── 1 sites`
  - `1 ── N ocr_template_regions` (P2 후속)
  - `1 ── N ocr_template_table_guides` (P2 후속)

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | 격리 키 | ON DELETE CASCADE |
| `name` | VARCHAR(128) | ✅ | 템플릿 이름 (`거래_6`) | 기존 `template_name` |
| `document_type` | VARCHAR(64) | ✅ | `invoice_statement`, `pos_receipt` 등 | CLAUDE.md 정의 따름 |
| `description` | TEXT | ❌ | 설명 | |
| `image_width` | INTEGER | ✅ | 원본 이미지 폭 | 좌표 해석 필수 |
| `image_height` | INTEGER | ✅ | 원본 이미지 높이 | 좌표 해석 필수 |
| `source_file_name` | VARCHAR(256) | ❌ | 원본 파일명 (`6.pdf`) | 참고용 |
| `source_storage_key` | VARCHAR(512) | ❌ | 원본 이미지 storage URI | base64 data URL 대신 |
| `template_body` | JSONB | ✅ | 전체 템플릿 구조 (regions, guides 포함) | 기존 `template_json` |
| `version` | INTEGER | ✅ | 버전 번호 | 기본 1. 수정 시 +1 또는 새 행 |
| `is_active` | BOOLEAN | ✅ | 활성 여부 | RunOCR 후보에서 제외 가능 |
| `created_by` | UUID FK→users.id | ✅ | 생성자 | |
| `updated_by` | UUID FK→users.id | ❌ | 최종 수정자 | |
| `created_at` | TIMESTAMPTZ | ✅ | | |
| `updated_at` | TIMESTAMPTZ | ✅ | | |
| `deleted_at` | TIMESTAMPTZ | ❌ | soft delete | |

#### 제약

- `UNIQUE(site_id, name, version)` — 사이트 내 (이름, 버전) 유일.
- `CHECK (document_type IN ('card_receipt','pos_receipt','food_cafe_receipt','finance_slip','medical_receipt','invoice_statement','tax_invoice','transaction_statement','unknown'))` — 단, ENUM/CHECK는 확장성을 고려해 application-level 검증으로도 충분.

#### template_body JSONB 구조 (현재 templates.json의 `template_json` 그대로 보존)

```json
{
  "templateName": "거래_6",
  "documentType": "invoice_statement",
  "file": { "name": "6.pdf" },
  "image": { "width": 1653, "height": 1167, "src": "data:image/jpeg;base64,..." },
  "regions": [ { "key": "...", "type": "text|table", "x": 100, "y": 200, "width": 300, "height": 50, ... } ],
  "tableConfig": { "colGuides": [ ... ], "rowGuides": [ ... ] }
}
```

#### 정규화 vs JSONB 의사결정 (D1)

| 방식 | 장점 | 단점 |
|---|---|---|
| **template_body JSONB 단일 보관 (추천)** | 마이그레이션 단순. 기존 코드 변경 최소. 형상 변경 자유. | 영역 단위 검색/통계 어려움. 인덱싱 한계. |
| regions/table_guides 즉시 정규화 | 영역 단위 쿼리/수정 용이. 데이터 무결성 강함. | 마이그레이션 복잡. 코드 대규모 변경. 형상 변경 시 마이그레이션 필요. |

**추천: MVP는 JSONB 단일. P2에서 사용 패턴 보고 정규화 결정.**
단, `image_width`/`image_height`/`document_type`/`name`처럼 쿼리에 자주 쓰는 항목은 별도 컬럼으로도 중복 보관 (read-time 편의).

#### 설계 메모

- **버전 관리**: 기존 row를 update할지, 새 row(version+1)를 insert할지는 P1에서 결정. MVP는 update 권장 (단순성).
- **base64 src 처리**: template_body 안의 거대한 base64 문자열은 별도 `source_storage_key`로 분리 권장 (DB 크기/IO 부담).
- **지금 필수**: P1.

---

### 6.6 ocr_template_regions (P2 후속)

- **용도**: 템플릿 내 영역(필드/표) 박스 정규화.
- **사용 화면**: Template 탭, RunOCR 결과 매핑
- **왜 필요한가**:
  - 영역 단위 통계 (사용 빈도, 인식률) 분석
  - 영역 단위 부분 수정 시 무결성
- **site_id 필요 여부**: ✅ 필수 (조회 성능/RLS 일관성)
- **주요 관계**: `N ── 1 ocr_templates`, `1 ── N ocr_template_table_guides`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | 격리 | template과 일치 |
| `template_id` | UUID FK→ocr_templates.id | ✅ | 상위 템플릿 | ON DELETE CASCADE |
| `field_key` | VARCHAR(64) | ✅ | 내부 키 (`total_amount`) | |
| `field_label` | VARCHAR(128) | ✅ | UI 표시 라벨 (`합계금액`) | |
| `field_type` | VARCHAR(32) | ✅ | `text` / `table` / `number` / `date` / `barcode` | |
| `x` | INTEGER | ✅ | 좌상 x (pixel) | template.image_width 기준 |
| `y` | INTEGER | ✅ | 좌상 y | |
| `width` | INTEGER | ✅ | 폭 | |
| `height` | INTEGER | ✅ | 높이 | |
| `region_order` | INTEGER | ✅ | 표시 순서 | |
| `options` | JSONB | ❌ | regex, mapping, validators 등 | |
| `created_at` | TIMESTAMPTZ | ✅ | | |
| `updated_at` | TIMESTAMPTZ | ✅ | | |

#### 의사결정

- **MVP는 template_body JSONB로 충분**. 본 테이블은 **P2에서 정규화 결정 시 도입**.
- 도입 시 `template_body`에서 regions를 추출해 본 테이블로 분리하고, `template_body`에서는 regions 제거 또는 view로 합성.

---

### 6.7 ocr_template_table_guides (P2 후속)

- **용도**: 표 영역의 컬럼/행 가이드 좌표 정규화 (`colGuides[]`, `rowGuides[]`)
- **사용 화면**: Template 탭 (표 빌더), invoice_statement 파서
- **왜 필요한가**:
  - T-10 header-skip 등 표 처리 로직에서 가이드별 통계/조정
  - 가이드 단위 부분 수정
- **site_id 필요 여부**: ✅ 필수
- **주요 관계**: `N ── 1 ocr_template_regions` (또는 ocr_templates 직접)

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | 격리 | |
| `template_id` | UUID FK→ocr_templates.id | ✅ | 상위 템플릿 | |
| `region_id` | UUID FK→ocr_template_regions.id | ❌ | 표 영역 | nullable: regions 미정규화 시 직접 template에 매다는 fallback |
| `guide_type` | VARCHAR(16) | ✅ | `col` / `row` | |
| `guide_key` | VARCHAR(64) | ❌ | 컬럼명 (`수량`, `단가`, `금액`) | row일 때 nullable |
| `guide_value` | NUMERIC | ✅ | 좌표 (col=x px, row=y px) | |
| `guide_order` | INTEGER | ✅ | 순서 | |
| `options` | JSONB | ❌ | header_skip, dtype 등 | T-10 header-like 처리 옵션 |
| `created_at` | TIMESTAMPTZ | ✅ | | |
| `updated_at` | TIMESTAMPTZ | ✅ | | |

#### 의사결정

- **MVP는 template_body.tableConfig JSONB로 충분**. P2~P3에서 정규화.
- **즉시 필요한 신호**: 가이드별 통계 또는 부분 수정 UI가 생기면 도입. 현재는 없음.

---

### 6.8 ocr_runs

- **용도**: RunOCR 실행 1회 단위 상위 테이블.
- **사용 화면**: RunOCR 탭(실행 시 기록), History 탭(목록)
- **왜 필요한가**:
  - 다중 파일을 한 번의 실행으로 묶음
  - 실행 상태(`running`/`succeeded`/`failed`/`partial`) 추적
  - 옵션/모델/사용자/사이트 메타데이터 통합 보관
- **site_id 필요 여부**: ✅ 필수
- **주요 관계**:
  - `N ── 1 sites`, `N ── 1 users`, `N ── 1 ocr_templates` (nullable)
  - `1 ── N ocr_run_files`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK = `job_id` 대체 | 기존 `OCR-A1B2C3D4` 형식 폐기 |
| `site_id` | UUID FK→sites.id | ✅ | 격리 | |
| `user_id` | UUID FK→users.id | ✅ | 실행자 | |
| `template_id` | UUID FK→ocr_templates.id | ❌ | 사용된 템플릿 | nullable (템플릿 없는 자유 실행 가능) |
| `run_mode` | VARCHAR(16) | ✅ | `upload` / `template` / `batch` / `test` | test는 향후 |
| `status` | VARCHAR(16) | ✅ | `pending`/`running`/`succeeded`/`failed`/`partial` | |
| `model_id` | VARCHAR(64) | ❌ | OCR 엔진/모델 식별자 | `tesseract-5.3`, `google-vision-2024-q4` 등 |
| `options` | JSONB | ❌ | 실행 옵션 | debugPreprocessing, autoApplyPreprocessing, selectedModel 등 |
| `summary` | JSONB | ❌ | 집계 결과 | totalFiles, successCount, failureCount, documentTypes |
| `started_at` | TIMESTAMPTZ | ❌ | 실행 시작 | |
| `finished_at` | TIMESTAMPTZ | ❌ | 실행 종료 | |
| `duration_ms` | INTEGER | ❌ | 총 소요 ms | finished_at - started_at, 또는 별도 계측 |
| `created_at` | TIMESTAMPTZ | ✅ | 행 생성 시각 | |
| `updated_at` | TIMESTAMPTZ | ✅ | | |
| `deleted_at` | TIMESTAMPTZ | ❌ | soft delete | History 삭제 시 |

#### options JSONB 예시

```json
{
  "debugPreprocessing": false,
  "autoApplyPreprocessing": "limited",
  "selectedModel": "default",
  "rotateAttempts": [0, 90, 180, 270],
  "skipPostprocess": false
}
```

#### summary JSONB 예시

```json
{
  "totalFiles": 5,
  "successCount": 4,
  "failureCount": 1,
  "documentTypes": { "invoice_statement": 3, "pos_receipt": 2 }
}
```

#### 설계 메모

- **History 탭의 기본 목록 = `SELECT * FROM ocr_runs WHERE site_id=? ORDER BY created_at DESC`**
- **지금 필수**: P1.

---

### 6.9 ocr_run_files

- **용도**: 실행에 포함된 파일 단위 메타데이터.
- **사용 화면**: RunOCR 진행 표시, History 상세
- **왜 필요한가**:
  - 한 run에 여러 파일이 있을 수 있고, 각 파일이 별도 결과를 가짐
  - 파일 메타데이터(MIME, 크기, checksum) 보관
  - storage_key로 실제 파일과 추상화된 연결
- **site_id 필요 여부**: ✅ 필수 (조회 성능)
- **주요 관계**: `N ── 1 ocr_runs`, `1 ── 1 ocr_run_results`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | 격리 | |
| `run_id` | UUID FK→ocr_runs.id | ✅ | 상위 run | ON DELETE CASCADE |
| `original_file_name` | VARCHAR(512) | ✅ | 사용자가 업로드한 원본명 | `invoice_2024_01.pdf` |
| `mime_type` | VARCHAR(64) | ✅ | `application/pdf`, `image/jpeg` 등 | |
| `size_bytes` | BIGINT | ✅ | 파일 크기 | |
| `storage_key` | VARCHAR(512) | ✅ | 추상화된 저장 위치 | `local://uploads/2026/05/abc.pdf`, `s3://bucket/key` |
| `checksum_sha256` | CHAR(64) | ❌ | 무결성 검증/중복 검출 | |
| `page_count` | INTEGER | ❌ | PDF 페이지 수 | nullable (이미지 = 1) |
| `image_width` | INTEGER | ❌ | 이미지 원본 폭 | PDF의 첫 페이지 또는 단일 이미지 |
| `image_height` | INTEGER | ❌ | 이미지 원본 높이 | |
| `file_order` | INTEGER | ✅ | run 내 순서 (1부터) | UI 표시 순서 |
| `metadata` | JSONB | ❌ | 부가 메타 (EXIF, PDF 메타 등) | |
| `created_at` | TIMESTAMPTZ | ✅ | | |

#### 설계 메모

- **원본 파일은 DB에 저장하지 않는다** — `storage_key`만 보관.
- **로컬 개발**: `local://` 어댑터로 `ocr-server/uploads/` 등 디렉토리에 저장.
- **운영 확장**: `s3://`, `azure://`, `gcs://` 어댑터.
- **MIME/size_bytes는 업로드 시점에 즉시 기록 — 필수**.
- **지금 필수**: P1.

---

### 6.10 ocr_run_results

- **용도**: OCR 결과 핵심 테이블. 파일 1개에 대한 추출/분류 결과.
- **사용 화면**: RunOCR 결과 패널, History 상세
- **왜 필요한가**:
  - 영수증/거래명세서 등 모든 결과의 단일 컨테이너
  - JSONB 구조로 doctype별 유연성 보장
- **site_id 필요 여부**: ✅ 필수
- **주요 관계**: `1 ── 1 ocr_run_files`, `N ── 1 ocr_runs`, `1 ── N ocr_run_table_rows`, `1 ── N ocr_run_warnings`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | 격리 | |
| `run_id` | UUID FK→ocr_runs.id | ✅ | 상위 run | |
| `file_id` | UUID FK→ocr_run_files.id UNIQUE | ✅ | 1:1 매핑 | UNIQUE 제약 |
| `template_id` | UUID FK→ocr_templates.id | ❌ | 사용된 템플릿 (스냅샷용) | nullable |
| `document_type` | VARCHAR(64) | ✅ | 최종 documentType | 사용자 지정 또는 분류 결과 |
| `detected_doc_type` | VARCHAR(64) | ❌ | classifier가 추정한 타입 | document_type과 다를 수 있음 |
| `status` | VARCHAR(16) | ✅ | `succeeded`/`failed`/`partial`/`needs_review` | |
| `receipt_fields` | JSONB | ❌ | 영수증 계열 결과 (`total_amount`, `vat`, ...) | doctype=receipt 계열일 때 |
| `document_fields` | JSONB | ❌ | 일반 문서 결과 (invoice_statement.tableRows 포함) | doctype별 자유 형식 |
| `normalized_fields` | JSONB | ❌ | 후처리 정규화 (날짜, 사업자번호 등) | 검색용 |
| `table_meta` | JSONB | ❌ | 표 메타 (rowCount, colCount, colGuides snapshot) | invoice_statement |
| `preprocessing_debug` | JSONB | ❌ | 전처리 디버그 정보 | debug/auto-apply 시에만 |
| `raw_text` | TEXT | ❌ | OCR raw text 전체 | 디버그/검색 |
| `confidence` | NUMERIC(5,4) | ❌ | 전체 신뢰도 (0~1) | |
| `parser_version` | VARCHAR(32) | ❌ | 파서 버전 (`T-23`, `parser-2026-05-17`) | 재처리 추적 |
| `ocr_engine` | VARCHAR(64) | ❌ | OCR 엔진 식별자 | `tesseract-5.3` 등 |
| `warnings_summary` | JSONB | ❌ | 경고 요약 (count by severity) | warnings 별도 테이블 미도입 시 main 보관 |
| `created_at` | TIMESTAMPTZ | ✅ | | |
| `updated_at` | TIMESTAMPTZ | ✅ | | |

#### document_fields JSONB 예시 (invoice_statement)

```json
{
  "supplier": "주식회사 ABC",
  "buyer": "MySuit",
  "issue_date": "2026-05-10",
  "tableRows": [
    { "no": 1, "item": "옷걸이", "qty": 10, "unit_price": 1000, "amount": 10000 },
    { "no": 2, "item": "행거", "qty": 5, "unit_price": 2000, "amount": 10000 }
  ],
  "total_amount": 20000
}
```

#### preprocessing_debug 저장 정책 (D6)

| 정책 | 추천 |
|---|---|
| 항상 저장 | ❌ 용량 부담 |
| 저장 안 함 | ❌ 운영 분석 불가 |
| **debug mode (`options.debugPreprocessing=true`) 시 저장** | ✅ |
| **production auto-apply (`options.autoApplyPreprocessing` 결과 `productionApplied=true`) 시 저장** | ✅ |
| 위 두 조건 OR | **✅ 추천** |

#### 설계 메모

- **`file_id` UNIQUE** — 파일 1개당 결과 1건 가정. 재실행은 새 run을 만든다.
- **JSONB 인덱싱**: 자주 조회하는 키(`document_fields->>'supplier'`, `normalized_fields->>'business_number'`)는 GIN 또는 expression index.
- **`raw_text`는 TEXT** — pgvector/FTS 확장 시 검색 인덱스 대상.
- **지금 필수**: P1.

---

### 6.11 ocr_run_table_rows (P3 후속)

- **용도**: 거래명세서 등 표 row 단위 정규화 저장.
- **사용 화면**: History 상세에서 행 단위 편집/검색
- **왜 필요한가**:
  - 행 단위 검색/집계 (예: "공급가액 합계 > 100만원 row만 조회")
  - 행 단위 수정/승인 워크플로
- **site_id 필요 여부**: ✅ 필수
- **주요 관계**: `N ── 1 ocr_run_results`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | 격리 | |
| `result_id` | UUID FK→ocr_run_results.id | ✅ | 상위 결과 | ON DELETE CASCADE |
| `row_index` | INTEGER | ✅ | 0-based 행 번호 | |
| `row_data` | JSONB | ✅ | 컬럼명→값 | `{"qty":10,"item":"옷걸이"}` |
| `source_bboxes` | JSONB | ❌ | 행 내 셀별 bbox | 시각화/디버그 |
| `confidence` | NUMERIC(5,4) | ❌ | 행 신뢰도 | |
| `row_status` | VARCHAR(16) | ❌ | `auto`/`reviewed`/`corrected`/`rejected` | 향후 검토 워크플로 |
| `metadata` | JSONB | ❌ | 부가 정보 | |
| `created_at` | TIMESTAMPTZ | ✅ | | |

#### 의사결정 (D7)

- **MVP: `ocr_run_results.document_fields.tableRows` JSONB로 충분.** invoice_statement E2E 7/7 exact 이미 달성.
- **별도 테이블 도입 신호**: 행 단위 검색/편집 UI가 명세화될 때 (현재 없음). P3 후속.

---

### 6.12 ocr_run_warnings (P3 후속)

- **용도**: OCR/파서/전처리 경고 누적 저장.
- **사용 화면**: 운영 품질 모니터링 대시보드, History 상세 경고 패널
- **왜 필요한가**:
  - 경고 유형별 빈도/추세 분석
  - severity 기반 알림
- **site_id 필요 여부**: ✅ 필수
- **주요 관계**: `N ── 1 ocr_run_results`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `site_id` | UUID FK→sites.id | ✅ | | |
| `result_id` | UUID FK→ocr_run_results.id | ✅ | | ON DELETE CASCADE |
| `warning_type` | VARCHAR(64) | ✅ | `value_mapping`/`source_missing`/`preprocessing`/`parser` | |
| `field_key` | VARCHAR(64) | ❌ | 관련 필드 | |
| `severity` | VARCHAR(16) | ✅ | `info`/`warning`/`error` | |
| `message` | TEXT | ✅ | | |
| `metadata` | JSONB | ❌ | | |
| `created_at` | TIMESTAMPTZ | ✅ | | |

#### 의사결정 (D8)

- **MVP: `ocr_run_results.warnings_summary` JSONB로 충분** (예: `{"error":0,"warning":2,"info":1}`)
- **별도 테이블 도입 신호**: 경고 추세 분석 대시보드 또는 알림 시스템 도입 시. P3 후속.

---

### 6.13 user_preferences (P2 권장)

- **용도**: 사용자별 UI/운영 환경 설정.
- **사용 화면**: 모든 화면 (theme, last_site, default_options)
- **왜 필요한가**:
  - `mysuit_ocr_theme` localStorage 대체
  - 사용자가 마지막에 선택한 사이트 복원
  - 사용자별 기본 OCR 옵션
- **site_id 필요 여부**: ❌ 사용자 기준 → 불필요. 단 `preference_key='last_site_id'`의 value에 site_id를 넣는 식.
- **주요 관계**: `N ── 1 users`

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | UUID | ✅ | PK | |
| `user_id` | UUID FK→users.id | ✅ | | |
| `preference_key` | VARCHAR(64) | ✅ | `theme`/`last_site_id`/`default_options` 등 | |
| `preference_value` | JSONB | ✅ | 자유 형식 | |
| `created_at` | TIMESTAMPTZ | ✅ | | |
| `updated_at` | TIMESTAMPTZ | ✅ | | |

#### 제약

- `UNIQUE(user_id, preference_key)`

#### 의사결정 (D10)

- **MVP 필수 아님**. theme 정도는 localStorage 유지 가능.
- **P2 즉시 권장 이유**: "사용자별 마지막 작업 사이트 복원"이 멀티사이트 UX의 핵심.

---

### 6.14 audit_logs (P2 권장)

- **용도**: 운영/감사 이벤트 로그. review_log.jsonl 대체 및 확장.
- **사용 화면**: 운영자 대시보드, 보안 감사
- **왜 필요한가**:
  - 로그인/로그아웃, 템플릿 변경, OCR 실행, 권한 변경 등 추적
  - 보안 감사 (`who did what when from where`)
  - review_log.jsonl 단점(파일 IO, 검색 어려움) 해소
- **site_id 필요 여부**: ⚠️ nullable. 사이트 무관 이벤트(로그인, 사용자 생성) 존재.
- **주요 관계**: `N ── 1 users` (nullable), `N ── 1 sites` (nullable)

#### 컬럼 상세

| 컬럼 | 타입 | 필수 | 용도 | 비고 |
|---|---|---|---|---|
| `id` | BIGSERIAL | ✅ | PK | 대량 append 고려 BIGSERIAL |
| `site_id` | UUID FK→sites.id | ❌ | 사이트 컨텍스트 | nullable |
| `user_id` | UUID FK→users.id | ❌ | 행위자 | nullable (시스템 이벤트) |
| `action` | VARCHAR(64) | ✅ | `auth.login`, `template.create`, `run.execute` 등 | dot.notation |
| `entity_type` | VARCHAR(64) | ❌ | `user`/`site`/`template`/`run`/`result` | |
| `entity_id` | UUID | ❌ | 대상 ID | |
| `ip_address` | INET | ❌ | | |
| `user_agent` | TEXT | ❌ | | |
| `metadata` | JSONB | ❌ | 이벤트별 부가 정보 | before/after 등 |
| `created_at` | TIMESTAMPTZ | ✅ | | 인덱싱 필수 |

#### 의사결정 (D9)

- **MVP 직후 P2 즉시 도입 권장**. 보안 감사 요구가 운영 단계에서 즉시 발생.
- review_log.jsonl의 자동분류/검토 이력은 별도 review_history 테이블로 분리하거나 audit_logs에 흡수 가능 (후속 결정).

---

## 7. 화면별 테이블 매핑

| 화면 | 조회 테이블 | 저장/생성 테이블 | 수정 테이블 | 비고 |
|---|---|---|---|---|
| **Login** | users, sessions | sessions, audit_logs | users.last_login_at | password 검증 |
| **Logout** | sessions | audit_logs | sessions.revoked_at | |
| **사이트 선택 (Sidebar)** | sites, site_members | - | sessions.current_site_id, user_preferences | |
| **Site 설정** | sites, site_members | site_members (초대), audit_logs | sites.settings | owner/admin |
| **Template 목록** | ocr_templates | - | - | site_id 필터 |
| **Template 생성/수정** | ocr_templates | ocr_templates, audit_logs | ocr_templates | (P2: regions/guides 추가) |
| **RunOCR 실행** | sites, ocr_templates | ocr_runs, ocr_run_files, ocr_run_results, audit_logs | ocr_runs.status | (P3: table_rows/warnings) |
| **History 목록** | ocr_runs, ocr_run_files | - | - | site_id 필터, 페이지네이션 |
| **History 상세** | ocr_runs, ocr_run_files, ocr_run_results | - | - | (P3: rows/warnings) |
| **History 삭제** | - | audit_logs | ocr_runs.deleted_at | soft delete |

---

## 8. site_id 격리 기준

| 테이블 | site_id 필요 | 이유 |
|---|---|---|
| users | ❌ | 전역 엔티티. 여러 사이트에 속함 |
| sessions | ❌ | 사용자 기준. `current_site_id`는 단순 hint |
| sites | (self) | 사이트 자신 |
| site_members | ✅ | 사이트-사용자 매핑 자체 |
| ocr_templates | ✅ | 템플릿은 사이트 소유 |
| ocr_template_regions | ✅ | 조회 성능/RLS 일관성 |
| ocr_template_table_guides | ✅ | 동일 |
| ocr_runs | ✅ | 실행은 사이트 컨텍스트에서 |
| ocr_run_files | ✅ | 조회 성능 |
| ocr_run_results | ✅ | 동일 |
| ocr_run_table_rows | ✅ | 동일 |
| ocr_run_warnings | ✅ | 동일 |
| user_preferences | ❌ | 사용자 기준. 사이트별 preference는 `last_site_id`로 표현 |
| audit_logs | ⚠️ nullable | 사이트 무관 이벤트(로그인) 존재 |

### 격리 원칙

1. **template 이하 모든 업무 테이블은 site_id를 직접 보유한다** (FK chain만으로 가능해도 중복 보관 → 조회 성능/RLS 단순화).
2. **모든 쿼리는 `WHERE site_id = $current_site_id`를 기본 첨가**. super_admin만 우회 가능.
3. **Row-Level Security (RLS)** 도입 시 site_id 기반 정책 일관 적용 가능.

---

## 9. History 저장 구조

History 탭은 다음 3-tier 구조로 조회:

### 9.1 List (목록)

```sql
SELECT r.id, r.created_at, r.status, r.run_mode, r.summary,
       u.display_name AS executor,
       t.name AS template_name,
       (SELECT COUNT(*) FROM ocr_run_files WHERE run_id = r.id) AS file_count
FROM ocr_runs r
LEFT JOIN users u ON u.id = r.user_id
LEFT JOIN ocr_templates t ON t.id = r.template_id
WHERE r.site_id = $site_id AND r.deleted_at IS NULL
ORDER BY r.created_at DESC
LIMIT 50 OFFSET $offset;
```

### 9.2 Detail (run 상세)

```sql
-- run 메타
SELECT * FROM ocr_runs WHERE id = $run_id AND site_id = $site_id;

-- files
SELECT * FROM ocr_run_files WHERE run_id = $run_id ORDER BY file_order;

-- results
SELECT * FROM ocr_run_results WHERE run_id = $run_id;
```

### 9.3 Row/Warning Drilldown (P3)

```sql
SELECT * FROM ocr_run_table_rows WHERE result_id = $result_id ORDER BY row_index;
SELECT * FROM ocr_run_warnings WHERE result_id = $result_id ORDER BY severity DESC;
```

### 9.4 보존 정책

- `ocr_runs.deleted_at` soft delete.
- 사이트 설정 `settings.retention_days`에 따라 백그라운드 작업으로 hard delete 후보 식별.
- 파일은 `storage_key`에 따라 별도 어댑터에서 정리.

---

## 10. Template 저장 구조

### 10.1 Template Master만 (MVP, 추천)

```
ocr_templates
  ├─ template_body JSONB ← regions, tableConfig, image src 모두 포함
  └─ source_storage_key   ← base64 src는 외부 분리
```

### 10.2 정규화 (P2 후속)

```
ocr_templates              (메타 + tableConfig만)
  └─ ocr_template_regions  (영역 단위)
       └─ ocr_template_table_guides (가이드 단위)
```

### 10.3 비교

| 항목 | template_body JSONB | regions/guides 정규화 |
|---|---|---|
| 마이그레이션 난이도 | 낮음 (현재 구조 그대로) | 높음 (분해 필요) |
| 코드 변경 | 최소 | 큼 |
| 영역 단위 쿼리 | GIN/expression index 필요 | 자연스러움 |
| 영역 통계/리포트 | 어려움 | 쉬움 |
| 형상 변경 자유도 | 매우 높음 | 낮음 (DDL 필요) |
| 무결성 강제 | 약함 | 강함 |
| 추천 시점 | MVP (P1) | P2~P3 (사용 패턴 확인 후) |

**최종 추천: MVP는 JSONB. P2에서 사용 패턴 보고 정규화 결정.** 단, name/document_type/image_width/image_height/source_storage_key 등 자주 쓰는 항목은 별도 컬럼으로 동시 보관.

---

## 11. Auth/Security 설계

### 11.1 password_hash

- **알고리즘**: bcrypt cost=12 (운영 환경에 맞춰 조정).
- **컬럼**: `VARCHAR(60)`.
- **마이그레이션**: `users.json`의 평문 `user_pw` → bcrypt 해시 변환 → 즉시 폐기.
- **운영**: 비밀번호 정책 (최소 길이, 복잡도)은 application 레벨.

### 11.2 sessions

- **저장**: `session_token_hash` (SHA-256). 평문 토큰은 클라이언트만 보유.
- **전달**:
  - **권장**: httpOnly + Secure + SameSite=Lax 쿠키
  - 호환: Authorization Bearer (단, XSS 위험 존재)
- **만료**: `expires_at` + sliding (`last_seen_at` 갱신 시 연장 옵션).
- **강제 만료**: `revoked_at` 설정.
- **로그아웃 전파**: 동일 사용자의 모든 활성 세션 무효화 옵션 제공.

### 11.3 super_admin

- `users.is_super_admin = true` 한 플래그.
- 모든 권한 체크에서 우선 통과 (RLS 정책 또는 미들웨어).
- 별도 role 테이블/super_admin 테이블 만들지 않음 (단순성).

### 11.4 localStorage token 제거 방향

| 항목 | 기존 (localStorage) | 신규 (DB sessions + cookie) |
|---|---|---|
| 저장 위치 | localStorage `mysuit_ocr_login` | httpOnly cookie |
| 서버 검증 | 불가 | sessions 테이블 조회 |
| 만료 관리 | 클라이언트만 | 서버 측 `expires_at` |
| 강제 만료 | 불가 | `revoked_at` |
| XSS 노출 | 있음 | httpOnly로 차단 |
| CSRF | 없음 | SameSite=Lax + CSRF token 권장 |

---

## 12. 이번 범위에서 제외한 것

| 항목 | 제외 이유 | 후속 후보 |
|---|---|---|
| **Test 탭 / TestWorkspace** | testset/manifest 구조 별도. RunAll 결과는 DB 미저장이 합리적 (파일 기반 리포트 충분) | DB-FUTURE-TEST |
| **testset manifest** | 정적 메타데이터. `public/data/testsets/*/manifest.json` 유지 | - |
| **GroundTruth (`mysuit_ocr_groundtruth`)** | Template/History와 연결 가능성만 기록. 현재 localStorage `template::file` key 기반 | DB-FUTURE-GT (ocr_ground_truth 테이블 후보, template_id + file_id ref) |
| **preprocessing 로직 변경** | CLAUDE.md 정책 준수 (OCR 인식 로직 변경 금지) | - |
| **RunOCR 자동 적용 Phase 3** | T-20 limited auto-apply에서 멈춤. DB 저장 정책만 본 설계에 반영 (D6) | 후속 |
| **finance_slip / tax_invoice / transaction_statement parser 확장** | OCR/parser 변경 금지 | 후속 |
| **review_log.jsonl 직접 마이그레이션** | audit_logs로 흡수 가능 여부 P2에서 별도 분석 | 후속 |

---

## 13. 사용자가 검토해야 할 결정사항

| # | 결정 사항 | 추천 | 대안 | 영향 |
|---|---|---|---|---|
| D1 | template 영역/가이드 정규화 시점 | JSONB 우선 (P1), 정규화는 P2 | 즉시 정규화 | MVP 출시 속도 vs 영역 단위 분석 |
| D2 | password 저장 방식 | bcrypt cost=12 | argon2id | bcrypt가 라이브러리 호환성 우수 |
| D3 | session 토큰 저장 | SHA-256 해시 | 평문 / JWT | 해시가 안전. JWT는 강제 만료 어려움 |
| D4 | super_admin 표현 | `users.is_super_admin BOOLEAN` | 별도 role 테이블 | 플래그가 단순 |
| D5 | run-file-result 관계 | 1 run → N files → 1:1 result | 1 file → N results (재처리 이력) | MVP는 1:1, 재처리 이력은 새 run으로 |
| D6 | preprocessing_debug 저장 | debug OR production-applied 시 | 항상 / 안 함 | 용량 vs 분석 |
| D7 | tableRows 별도 테이블 | MVP는 JSONB, P3에서 분리 | 즉시 분리 | 행 단위 검색 요구 시점 |
| D8 | warnings 별도 테이블 | MVP는 JSONB summary, P3에서 분리 | 즉시 분리 | 운영 분석 시점 |
| D9 | audit_logs 도입 | MVP 직후 P2 | MVP 포함 / 더 후속 | 보안 감사 요구 강도 |
| D10 | user_preferences 도입 | P2 | localStorage 유지 | 멀티사이트 UX |
| D11 | sessions에 `current_site_id` 포함 | ✅ 포함 (nullable) | user_preferences로 분리 | 세션 종료 시 자동 소실 vs 영구 저장 |
| D12 | template 버전 관리 | update (단순) | insert-new-row (이력 보존) | 이력 요구 여부 |
| D13 | storage_key URI scheme | `local://`, `s3://` 추상화 | 단일 경로 문자열 | 어댑터 확장성 |
| D14 | document_type CHECK 제약 | application-level 검증 | DB CHECK | 신규 doctype 추가 유연성 |
| D15 | RLS 즉시 적용 | 미적용 (application-level) | 즉시 RLS | RLS는 신중히 도입 (디버깅 난이도) |

---

## 14. 추천 최종 테이블 목록

| 우선순위 | 테이블 | 이유 |
|---|---|---|
| **P0** | users | 평문 비밀번호 즉시 제거 (OPS-1 최대 병목) |
| **P0** | sessions | 서버 측 세션 검증 필수 |
| **P0** | sites | 멀티사이트 격리의 중심 |
| **P0** | site_members | 사이트별 권한 |
| **P1** | ocr_templates | 템플릿 이원화 해소 |
| **P1** | ocr_runs | RunOCR 실행 단위 |
| **P1** | ocr_run_files | 다중 파일 처리 |
| **P1** | ocr_run_results | OCR 결과 보존 |
| **P2** | audit_logs | 보안 감사 (MVP 직후 즉시) |
| **P2** | user_preferences | 멀티사이트 UX (last_site) |
| **P2** | ocr_template_regions | 영역 단위 분석 (사용 패턴 확인 후) |
| **P2** | ocr_template_table_guides | 가이드 단위 분석 |
| **P3** | ocr_run_table_rows | 행 단위 검색/편집 요구 시 |
| **P3** | ocr_run_warnings | 운영 품질 모니터링 |

---

## 15. 다음 작업

### 15.1 사용자가 해야 할 일

1. 본 문서 검토 → 13장 D1~D15 결정사항 확정.
2. 14장 우선순위에서 MVP 범위(P0+P1) 확정 또는 조정.
3. 컬럼 추가/제거/이름 변경 요청.

### 15.2 후속 작업 (DB-2 이후)

| 작업 | 내용 | 선행 조건 |
|---|---|---|
| **DB-2** | schema.sql 작성 (P0+P1 기준) | 본 설계 검토 완료 |
| **DB-3** | FastAPI + asyncpg/SQLAlchemy 연동 | DB-2 |
| **DB-4** | 마이그레이션 스크립트 (users.json/templates.json/history.json → DB) | DB-3 |
| **DB-5** | localStorage 제거 + cookie 기반 세션 | DB-3 |
| **DB-6** | P2 도입 (audit_logs, user_preferences, regions/guides) | MVP 안정화 |
| **DB-FUTURE-GT** | GroundTruth DB화 | 별도 설계 |
| **DB-FUTURE-TEST** | Test 탭 DB화 검토 | 별도 설계 |

### 15.3 검증 권장

- DB-2 작성 후: `psql --dry-run` + `EXPLAIN ANALYZE` 주요 쿼리.
- DB-4 마이그레이션: dry-run 모드로 기존 JSON과 100% 무손실 변환 검증.
- DB-5 전환: localStorage 기반과 병행 운영 가능한 dual-write 기간 권장.
