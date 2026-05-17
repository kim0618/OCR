# ARCH-1 OCR 현재 데이터 흐름 분석

**작성일**: 2026-05-17  
**목적**: DB-2 PostgreSQL schema.sql 작업 전 현재 구조 문서화  
**범위**: Template / RunOCR / History / Login-Auth / Site / GroundTruth / localStorage / backend JSON  
**주의**: 분석/문서화 작업. 코드 수정 없음.

---

## 1. 생성 파일

- `mysuit-ocr/docs/architecture/ocr_current_data_flow_architecture_20260517.md`
- `mysuit-ocr/docs/architecture/ocr_current_data_flow_architecture_20260517.json`

---

## 2. 핵심 요약

| 저장소 | 현재 방식 | DB 전환 필요성 |
|---|---|---|
| 사용자 인증 | users.json (평문 비밀번호) | **필수** — 보안 위험 |
| 템플릿 | templates.json (backend) + localStorage | **필수** — 단일 사용자 제한 |
| OCR 실행 기록 | localStorage + history.json | **필수** — 50건 한계 |
| 필드 확정값 | localStorage | **필수** — 브라우저 한정 |
| 운영 로그 | review_log.jsonl (Append-only) | 권장 — 분석 불편 |
| 테마 | localStorage | 낮음 |
| 사이트 선택 | 컴포넌트 state만 (비기능) | DB 설계에서 중심 |

---

## 3. localStorage 구조

| key | 저장 데이터 | 사용 화면 | DB 전환 필요성 | 대응 후보 테이블 |
|---|---|---|---|---|
| `mysuit_ocr_login` | StoredLogin: accessToken, user_id, user_nm, adminYn, masterYn, comp_cd, comp_nm | 전체 (로그인 상태 유지) | 중 — 세션 쿠키 전환 권장 | users, sessions |
| `mysuit_ocr_templates` | TemplateItem[]: id, name, regions[], documentType, image 메타 | UploadWorkspace, OcrAnnotator, UnstructuredBuilder, template/page | **필수** — 백엔드 templates.json 중복 | ocr_templates, ocr_template_regions |
| `mysuit_ocr_history` | HistoryRunRecord[]: MAX 50건, 5MB 제한 | HistoryWorkspace | **필수** — 용량 한계 | ocr_runs, ocr_run_files, ocr_run_results |
| `mysuit_ocr_groundtruth` | `{template::file: {fieldKey: value}}` | HistoryWorkspace, autofillEngine | **필수** — 브라우저 범위 제한 | ocr_ground_truth |
| `mysuit_ocr_theme` | "light" \| "dark" | 전체 레이아웃 | 낮음 | user_preferences |

### `mysuit_ocr_login` 구조
```typescript
type StoredLogin = {
  accessToken?: string;    // UUID 토큰 (Bearer 접두 제거)
  user_id?: string;
  user_nm?: string;
  adminYn?: string;        // "Y" | "N"
  masterYn?: string;       // "Y" | "N"
  comp_cd?: string;
  comp_nm?: string;
  envMysuitUrl?: string;
  envMagellanVersion?: string;
};
```

### `mysuit_ocr_history` 구조 요약
```typescript
type HistoryRunRecord = {
  job_id: string;                    // "RUN-XXXXXXXX"
  file_name: string;
  template_name: string | null;
  processing_time: number;           // 초
  created_at: string;                // "YYYY-MM-DD HH:mm:ss"
  status: "success" | "fail";
  original_image_url?: string | null;
  processed_image_url?: string | null;
  image_storage_mode?: "legacy" | "url";
  ocr_fields?: HistoryOcrField[];
  output_fields?: HistoryOutputField[];
  autofill_summary?: HistoryAutofillRunSummary;
};
```

### `mysuit_ocr_groundtruth` 구조
```typescript
// Key: "${template_name ?? ''}::${file_name}"
// Value: { [fieldKey: string]: confirmedValue }
// fieldKey = en 우선, 없으면 ko, trim+lowercase
type GroundTruthStore = Record<string, Record<string, string>>;
```

---

## 4. backend JSON 파일 구조

| file | 경로 | 역할 | 읽기/쓰기 | 문제점 | DB 대응 |
|---|---|---|---|---|---|
| `users.json` | `ocr-server/data/users.json` | 사용자 인증 | POST /login | **⚠ 평문 비밀번호** | users (bcrypt 해시) |
| `templates.json` | `ocr-server/data/templates.json` | 템플릿 CRUD | GET/POST/DELETE /templates | 파일 동시성 없음 | ocr_templates |
| `history.json` | `ocr-server/data/history.json` | OCR 실행 기록 (최소 메타만) | POST /ocrSelect/Insert/Update/Delete | 필드 매우 단순, 상세 없음 | ocr_runs |
| `review_log.jsonl` | `ocr-server/data/review_log.jsonl` | OCR 자동추출 감사 로그 | Append-only (auto_extract 이벤트) | JSONL 라인 검색 불편, 빠른 누적 | audit_logs |
| `drive_timings_latest.json` | `ocr-server/data/drive_timings_latest.json` | 드라이브 벤치마크 결과 | 읽기 | 운영 참고용 | — |

### users.json 구조 (보안 위험)
```json
[
  {
    "user_id": "admin",
    "user_pw": "1234",    // ⚠ 평문 비밀번호
    "user_nm": "관리자",
    "adminYn": "Y",
    "masterYn": "Y",
    "comp_cd": "MYSUIT",
    "comp_nm": "MySuit"
  }
]
```

### templates.json 구조
```json
{
  "template_id": "TPL-XXXXXXXX",
  "template_name": "거래_6",
  "template_json": {
    "regions": [...],
    "documentType": "invoice_statement",
    "colGuides": [...],
    "image": { "width": 1200, "height": 1700 }
  },
  "updated_at": "2026-05-17 10:00:00"
}
```

### history.json 구조 (백엔드 — 메타만)
```json
{
  "job_id": "OCR-A1B2C3D4",
  "file_name": "invoice_2024_01.pdf",
  "template_name": "세금계산서",
  "processing_time": 3.2,
  "created_at": "2026-05-17 10:00:00"
}
```

### review_log.jsonl 구조 (1라인 = 1 auto_extract 이벤트)
```json
{
  "ts": "2026-04-22T15:39:45",
  "event_type": "auto_extract",
  "image_id": "1.jpg",
  "doc_type": "receipt_card",
  "status": "selected",
  "review_required": false,
  "total_amount": { "selected_value": "10,560", "source": "amount_block", "score": 56.93 },
  "fields": { "회사명": {...}, "사업자번호": {...}, "총합계금액": {...} },
  "full_text": "...",
  "processing_time_sec": 43.3
}
```

---

## 5. Template 탭 데이터 흐름

| 데이터 | 현재 저장 위치 | 생성 위치 | 사용 위치 | DB 후보 |
|---|---|---|---|---|
| 템플릿 기본 정보 | `templates.json` + `mysuit_ocr_templates` | TemplateWorkspace (POST /templates) | UploadWorkspace, OcrAnnotator | ocr_templates |
| region 목록 | `template_json.regions` (JSON blob) | TemplateWorkspace canvas | RunOCR FormData에 JSON으로 전달 | ocr_template_regions |
| columnGuides | `template_json.colGuides` | TemplateWorkspace (T-6j) | invoice extractor | ocr_template_table_guides |
| documentType | `template_json.documentType` | TemplateWorkspace 드롭다운 | backend doc_type override | ocr_templates.document_type |
| 원본 이미지 크기 | `template_json.image.width/height` | TemplateWorkspace | region 좌표 스케일링 | ocr_templates |

### 흐름
```
[사용자] 이미지 업로드 → TemplateWorkspace canvas 편집
  → region/colGuides/documentType 설정
  → POST /templates (backend)
  → templates.json에 저장 (server)
  → localStorage mysuit_ocr_templates에 캐시 (client)

[RunOCR 사용 시]
  → GET /templates → template 목록 표시
  → 선택 → template_id + regions + documentType FormData 전달
  → POST /ocr/extract
```

### 현재 문제
- templates.json은 단일 파일 → 동시 쓰기 위험
- 사이트별 분리 없음 (전체 공유)
- localStorage 캐시와 서버 동기화 로직 없음

---

## 6. RunOCR 탭 데이터 흐름

| 단계 | 입력 | 처리 | 출력 | 저장 여부 |
|---|---|---|---|---|
| 파일 선택 | 이미지/PDF | 브라우저 File API | File 객체 | ✗ |
| 템플릿 선택 | template_id (localStorage/서버) | 템플릿 regions/docType 로드 | FormData 준비 | ✗ |
| OCR 실행 | FormData (file, template_id, regions, documentType, model_id) | POST /ocr/extract | OcrResult 객체 | ✓ (history에 저장) |
| 결과 표시 | OcrResult (fields, receipt_fields, document_fields) | UploadWorkspace 렌더링 | 필드 카드 표시 | ✗ |
| 자동채움 | OcrResult + GroundTruth | autofillEngine | suggestions | ✗ |
| History 저장 | OcrResult + autofill summary | historyStore.addRecord() | localStorage mysuit_ocr_history | ✓ |
| Backend History | job_id + 메타 | POST /ocrInsert | history.json | ✓ (메타만) |

### RunOCR FormData (현재)
```
file: File
template_id: string      // 선택된 경우
regions: JSON string     // template.regions 배열
documentType: string     // 예: "invoice_statement"
model_id: string         // "paddleocr" 기본
tableExpectedColumns: JSON string (T-6f)
tableBounds: JSON string (T-6i, 조건부)
columnGuides: JSON string (T-6j, 조건부)
debugPreprocessing: ❌ 미전달 (기본 false)
autoApplyPreprocessing: ❌ 미전달 (기본 false)
```

---

## 7. History 탭 데이터 흐름

| 데이터 | 현재 구조 | 한계 | DB 대응 |
|---|---|---|---|
| 실행 기록 목록 | localStorage: MAX 50건, FIFO 삭제 | 50건 초과 시 이전 기록 소실 | ocr_runs |
| 이미지 URL | processed_image_url (base64 또는 URL) | 대용량 시 localStorage 5MB 초과 → 이미지 자동 제거 | ocr_run_files (파일 서버 참조) |
| OCR 상세 필드 | ocr_fields[] + output_fields[] | JSON blob으로 저장, 검색 불가 | ocr_run_results |
| autofill 요약 | autofill_summary (HistoryAutofillRunSummary) | JSON blob | ocr_run_results |
| 삭제 | localStorage 직접 삭제 + POST /ocrDelete | 백엔드 history.json과 동기화 필요 | CASCADE DELETE |
| 재실행 | 현재 없음 | job_id로 재실행 불가 | ocr_runs.source_file_path |

### 히스토리 저장 로직
```
RunOCR 완료
  → historyStore.addRecord(record)
  → localStorage.setItem("mysuit_ocr_history", JSON)
  → quota 초과 시: 이미지 제거 시도 → 오래된 기록 삭제 (FALLBACK_RECORD_LIMITS)
  → 동시에: POST /ocrInsert (job_id + file_name + template_name + processing_time)
```

---

## 8. Login/Auth 데이터 흐름

| 항목 | 현재 방식 | 문제점 | DB/Auth 개선 방향 |
|---|---|---|---|
| 비밀번호 저장 | users.json 평문 | **⚠ 심각한 보안 위험** | bcrypt 해시 저장 |
| 인증 방식 | POST /login → UUID 토큰 생성 | 토큰 서버 미저장 (검증 불가) | JWT + refresh token 또는 session table |
| 토큰 저장 | localStorage `mysuit_ocr_login.accessToken` | XSS 취약 | HttpOnly cookie 권장 |
| 세션 관리 | 토큰 만료 없음 | 로그아웃해도 서버에서 무효화 불가 | sessions 테이블 + 만료 시간 |
| 사용자 수 | 2명 (admin, user) | 하드코딩 | users 테이블 (DB) |
| 권한 | adminYn, masterYn 필드 | 역할 확장성 없음 | roles/permissions 테이블 |
| 사이트-사용자 관계 | comp_cd 필드만 (미구현) | 실제 사이트 격리 없음 | site_members 테이블 |

### 로그인 흐름
```
[사용자] user_id + user_pw 입력
  → POST /api/login (Next.js route)
  → 프록시: POST {BACKEND_URL}/login
  → users.json 평문 비교
  → 성공: UUID 토큰 생성 (서버 미저장)
  → localStorage mysuit_ocr_login에 저장
  → 이후 API 호출 시 Bearer 헤더 (현재 검증 없음)
```

---

## 9. Site/Workspace 구조

| 항목 | 현재 상태 | 향후 DB 설계 의미 |
|---|---|---|
| Site 선택 UI | Sidebar.tsx:84 — `const [selectedSite, setSelectedSite] = useState("")` | 드롭다운 렌더링만, 비기능 |
| Site 목록 | 하드코딩: "사이트 A", "사이트 B", "사이트 C" | sites 테이블 필요 |
| Site 저장 | 없음 (컴포넌트 state만) | sites.id FK 전체 테이블 연결 |
| 템플릿 격리 | 없음 (전체 공유) | ocr_templates.site_id |
| 히스토리 격리 | 없음 (전체 공유) | ocr_runs.site_id |
| 사용자-사이트 관계 | 없음 | site_members (user_id, site_id, role) |
| 단일 org | 현재 MYSUIT 단일 comp_cd | 멀티 사이트 설계 준비 |

### 현재 Site 비기능 상태
```typescript
// Sidebar.tsx:84
const [selectedSite, setSelectedSite] = useState(""); 
// → 아무 API도 호출하지 않음
// → Template/History에 site_id 전달 없음
// → 완전히 미연결
```

---

## 10. GroundTruth/confirmed fields 구조

| 데이터 | 현재 저장 | 사용 위치 | DB 후보 |
|---|---|---|---|
| 사용자 확정 필드값 | `mysuit_ocr_groundtruth` localStorage | autofillEngine 자동채움 제안 | ocr_ground_truth |
| 키 패턴 | `"${template_name}::${file_name}"` | groundTruthStore.compositeKey() | (template_id, file_name) 복합 키 |
| 필드 키 | en 우선, 없으면 ko (trim+lowercase) | fieldKey() 함수 | field_key 컬럼 |
| 값 | 사용자가 수정한 값 (비어있으면 저장 안 함) | autofill 제안 source: "gt" | confirmed_value |
| 삭제 | clearGroundTruth(template, file) | — | DELETE WHERE |

### Testset ground_truth.json과 비교

| 구분 | `mysuit_ocr_groundtruth` (localStorage) | `testsets/{ds}/ground_truth.json` |
|---|---|---|
| 목적 | 사용자 RunOCR 확정값 (자동채움 재사용) | 개발/검증용 정답 기준값 |
| 범위 | 브라우저 로컬 | 공유 testset 파일 |
| 키 패턴 | `template::file` | `filename` 단독 |
| 구조 | `{fieldKey: value}` flat | `{fields: Entry, type, updated_at}` |
| 자동채움 | 사용됨 (autofillEngine) | 사용 안 됨 (TestWorkspace 비교용) |
| 관리 | 사용자 직접 수정 → 자동 저장 | 수동 편집 또는 TestWorkspace GT탭 |

---

## 11. DB 테이블 대응표

| 현재 데이터 | 후보 테이블 | 우선순위 | 비고 |
|---|---|---|---|
| users.json | `users` | **P1** | bcrypt 해시 필수 |
| comp_cd / site 구조 | `sites` | **P1** | 멀티사이트 기반 |
| user-site 관계 + adminYn/masterYn | `site_members` | P2 | role enum 설계 |
| templates.json 기본 | `ocr_templates` | **P1** | site_id FK |
| template_json.regions[] | `ocr_template_regions` | P2 | JSON blob or normalized |
| colGuides / tableBounds | `ocr_template_table_guides` | P3 | |
| history.json 기본 + localStorage 상세 | `ocr_runs` | **P1** | job_id PK, site_id FK |
| 이미지 URL/메타 | `ocr_run_files` | P2 | original/processed URL |
| receipt_fields / document_fields | `ocr_run_results` | P2 | JSON 컬럼 |
| tableRows | `ocr_run_table_rows` | P3 | invoice 전용 |
| tableMeta.valueMappingWarnings | `ocr_run_warnings` | P3 | |
| mysuit_ocr_groundtruth | `ocr_ground_truth` | **P1** | (template_id, file_name, field_key) |
| mysuit_ocr_theme | `user_preferences` | P4 | JSON JSONB |
| review_log.jsonl | `audit_logs` | P3 | event_type, image_id 인덱스 |

---

## 12. 보안/운영 리스크

| 리스크 | 수준 | 현재 위치 | 개선 방향 |
|---|---|---|---|
| 평문 비밀번호 | **⚠ 심각** | users.json:4,13 | bcrypt + salt |
| 토큰 서버 미저장 (검증 불가) | 높음 | main.py:725 — uuid 생성 후 반환만 | sessions 테이블 + 만료 |
| localStorage XSS | 중간 | mysuit_ocr_login | HttpOnly cookie |
| JSON 파일 동시 쓰기 경쟁 | 중간 | templates.json, history.json | DB ACID 보장 |
| 히스토리 5MB 한계 | 중간 | historyStore.ts:5 | DB + 파일 서버 |
| 사이트 격리 미구현 | 중간 | Sidebar.tsx:84 | sites + site_members |
| review_log.jsonl 무제한 누적 | 낮음 | data/review_log.jsonl | DB + 파티션/로테이션 |

---

## 13. DB-2로 넘길 결정사항

1. **비밀번호 해시 방식**: bcrypt 권장 (bcrypt.js 또는 passlib)
2. **토큰 방식**: JWT + 서버 세션 또는 session UUID table
3. **sites 구조**: 단일 comp_cd 계층 유지 vs 독립 site 엔티티
4. **template_json 저장**: JSON blob (jsonb) vs 테이블 정규화
5. **이미지 저장**: base64 제거 → 파일 서버 URL 참조
6. **review_log**: DB 이전 vs JSONL 유지 + 주기적 임포트
7. **ground_truth**: 독립 테이블 vs ocr_run_results에 통합
8. **역할(role)**: adminYn/masterYn → enum('admin','member','viewer') 전환
9. **auto-apply 이력**: preprocessingDebug 저장 여부 (ocr_run_results 확장)
10. **히스토리 마이그레이션**: 기존 localStorage 데이터 이전 스크립트 필요

---

## API 엔드포인트 요약

| endpoint | method | 설명 | 현재 저장 |
|---|---|---|---|
| `/login` | POST | 사용자 인증 | users.json 읽기 |
| `/templates` | GET | 템플릿 목록 | templates.json 읽기 |
| `/templates` | POST | 템플릿 저장 | templates.json 쓰기 |
| `/templates/{id}` | DELETE | 템플릿 삭제 | templates.json 쓰기 |
| `/ocr/extract` | POST | OCR 실행 | — (stateless) |
| `/ocrSelect` | POST | 히스토리 조회 | history.json 읽기 |
| `/ocrInsert` | POST | 히스토리 삽입 | history.json 쓰기 |
| `/ocrUpdate` | POST | 히스토리 수정 | history.json 쓰기 |
| `/ocrDelete` | POST | 히스토리 삭제 | history.json 쓰기 |
| `/ocr/feedback` | POST | 사용자 수정 로그 | review_log.jsonl Append |
| `/ocr/revalidate` | POST | 특정 영역 재OCR | — (stateless) |
| `/detect_corners` | POST | 코너 감지 | — (stateless) |
