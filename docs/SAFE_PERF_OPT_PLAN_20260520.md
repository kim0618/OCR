# Safe Performance Optimization — Application Plan

**날짜**: 2026-05-20  
**도구**: Codex  
**상태**: 적용 플레이북 (코드 미수정)  
**선행 문서**: `docs/SAFE_PERF_OPT_PREFLIGHT_20260520.md`

## 0. 사전 필독 확인

아래 6개 문서를 읽고 본 계획에 반영했다.

| 문서 | 확인 |
|---|---|
| `d:/Free_Vue/OCR/CLAUDE.md` | 확인 완료 |
| `d:/Free_Vue/OCR/SESSION_SUMMARY.md` | 확인 완료 |
| `d:/Free_Vue/OCR/docs/BASELINE_LOCK_20260425.md` | 확인 완료 |
| `d:/Free_Vue/OCR/docs/GOOGLE_LOCK_20260425.md` | 확인 완료 |
| `d:/Free_Vue/OCR/docs/T28_PERF3_table_crop_ocr_defer_20260520.md` | 확인 완료 |
| `d:/Free_Vue/OCR/docs/SAFE_PERF_OPT_PREFLIGHT_20260520.md` | 확인 완료 |

이번 작업에서는 운영 코드, 설정, 백업, 서버 재기동, OCR 호출, pip install을 수행하지 않았다. 산출물은 이 보고서 1개뿐이다.

## 1. 적용 우선순위 (재확정)

- 1순위: ④ JPEG quality `95→85`
- 2순위: 기존 `_warmup_ocr()` 보강, 단 신규 startup hook 추가는 금지
- 별도 단계: ① `text_recognition_batch_size 30→64`
- 보류: ③ `enable_mkldnn False→True`

1차 분석의 결론은 유지한다. JPEG quality 변경은 OCR 입력이 아니라 response용 `processed_image` 인코딩만 줄이는 변경이므로 가장 안전하다. Warmup은 이미 존재하므로 “새 hook 추가”가 아니라 기존 hook의 안정화로만 다룬다.

## 2. ④ JPEG quality 적용 플레이북

### 2-1. Endpoint / API Contract 확정

백엔드 POST endpoint 목록:

| endpoint | 용도 |
|---|---|
| `/login` | 로그인 |
| `/templates` | 템플릿 저장 |
| `/ocrSelect`, `/ocrInsert`, `/ocrUpdate`, `/ocrDelete` | 기존 OCR 저장/조회 계열 |
| `/ocr/feedback` | 피드백 |
| `/preprocess` | 전처리 |
| `/preprocess/corners` | 코너 검출 |
| `/ocr/extract` | 실제 OCR 추출 주 경로 |
| `/ocr/revalidate` | bbox 영역 재검증용, RunOCR 전체 회귀 대상 아님 |

백엔드 실제 추출 endpoint:

```python
@app.post("/ocr/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    template_id: str = Form(""),
    regions: str = Form(""),
    corners: str = Form(""),
    model_id: str = Form(""),
    tableExpectedColumns: str = Form(""),
    tableBounds: str = Form(""),
    columnGuides: str = Form(""),
    documentType: str = Form(""),
    debugPreprocessing: str = Form("false"),
    qualityTagsJson: str = Form(""),
    autoApplyPreprocessing: str = Form("false"),
):
```

프론트 RunOCR 경로:

- `mysuit-ocr/src/components/upload/UploadWorkspace.tsx`
- endpoint:
  - `NEXT_PUBLIC_BACKEND_URL`이 있으면 `${NEXT_PUBLIC_BACKEND_URL}/ocr/extract`
  - 없으면 Next proxy `/api/ocr-extract`
- Next proxy:
  - `mysuit-ocr/src/app/api/ocr-extract/route.ts`
  - `BACKEND_URL` 기본값은 `http://localhost:8000`
  - 실제 forwarding endpoint는 `${BACKEND_URL}/ocr/extract`

RunOCR multipart field:

| field | 거래명세서 Template RunOCR | 영수증 비정형 템플릿 |
|---|---|---|
| `file` | 필수 | 필수 |
| `template_id` | 필수 | 필수 |
| `regions` | template mode가 `unstructured`가 아니고 regions가 있으면 전달 | 일반적으로 없음 |
| `model_id` | RunOCR 시 전달 | RunOCR 시 전달 |
| `documentType` | 템플릿 metadata에 있으면 전달. 거래명세서는 `invoice_statement` | 템플릿 metadata가 있으면 전달 |
| `corners` | 현재 UploadWorkspace에서 주석 처리됨 | 현재 UploadWorkspace에서 주석 처리됨 |
| `tableExpectedColumns` | TestWorkspace/manifest 경로에서만 사용 | 보통 없음 |
| `debugPreprocessing`, `autoApplyPreprocessing`, `qualityTagsJson` | TestWorkspace 전처리 옵션 경로 | TestWorkspace 전처리 옵션 경로 |

회귀 검증 대상 endpoint는 **백엔드 직접 호출 `http://localhost:9099/ocr/extract`**로 확정한다. `/ocr/auto`는 현재 백엔드 POST route에 없다.

### 2-2. 대상 템플릿 / 파일

거래명세서:

| templateName | templateId | file | expected rowCount |
|---|---|---|---:|
| 거래_1 | `TPL-31D13CF3` | `1.jpg` | 28 |
| 거래_2 | `TPL-5A8C2374` | `2.pdf` | 13 |
| 거래_3 | `TPL-E4B15A22` | `3.pdf` | 1 |
| 거래_4 | `TPL-FD07531C` | `4.pdf` | 1 |
| 거래_5 | `TPL-B8936EDE` | `5.pdf` | 6 |
| 거래_6 | `TPL-95328E52` | `6.pdf` | 6 |
| 거래_7 | `TPL-3AFD383E` | `7.pdf` | 1 |

영수증:

| templateName | templateId | files |
|---|---|---|
| 영수증 | `TPL-003` | `1.jpg`, `2.jpg`, `3.jpg`, `4.jpg`, `7.jpg`, `8.jpg`, `10.jpg`, `a1.jpg`, `a2.jpg` |

### 2-3. 적용 diff

다음 단계에서 적용할 정확한 diff:

```diff
diff --git a/ocr-server/main.py b/ocr-server/main.py
--- a/ocr-server/main.py
+++ b/ocr-server/main.py
@@
-        _, img_encoded = cv2.imencode('.jpg', ocr_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
+        _, img_encoded = cv2.imencode('.jpg', ocr_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
```

적용 대상 line:

```python
2283:         _, img_encoded = cv2.imencode('.jpg', ocr_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
2284:         processed_b64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
```

### 2-4. 추가 영향 범위

`IMWRITE_JPEG_QUALITY` 사용처:

| line | 값 | 용도 |
|---:|---:|---|
| `main.py:1935` | 80 | `original_image` 표시용 인코딩 |
| `main.py:2283` | 95 | `processed_image` response용 인코딩, 이번 변경 대상 |

확인 결과:

- `preprocess.py`, `preprocessing_policy.py`에는 별도 `cv2.imencode` quality 사용이 확인되지 않았다.
- preprocessingDebug 분기는 `_build_preprocessing_debug(...)`를 호출하지만, 별도 JPEG quality 인코딩 지점은 grep에서 확인되지 않았다.
- OCR은 base64 JPEG가 아니라 메모리상의 `ocr_img`로 실행된다.
- 따라서 JPEG quality 변경은 OCR 인식 결과보다 response size, network transfer, frontend preview/history 저장량에 영향을 준다.

Frontend 영향:

| 파일 | 사용 |
|---|---|
| `UploadWorkspace.tsx` | `runResult.processed_image`를 preview URL, history `image_url`, `processed_image_url`로 저장 |
| `TestWorkspace.tsx` | `data.processed_image ?? originalUrl`을 display URL로 사용 |
| `historyStore.ts` | `processed_image_url` 우선, legacy `image_url` fallback |
| `DetailHistoryView.tsx` | 하단 전처리 후 이미지 표시 |

품질 85는 OCR 결과 회귀보다 preview/history 시각 품질 확인이 핵심이다.

### 2-5. 백업 절차

다음 적용 단계에서 실행:

```bash
cp d:/Free_Vue/OCR/ocr-server/main.py \
   d:/Free_Vue/OCR/ocr-server/backup/main_20260520_HHMM_before_jpeg_quality.py
```

PowerShell:

```powershell
Copy-Item -LiteralPath d:\Free_Vue\OCR\ocr-server\main.py `
  -Destination d:\Free_Vue\OCR\ocr-server\backup\main_20260520_HHMM_before_jpeg_quality.py
```

### 2-6. 적용 절차 (수정 단계에서 실행할 명령)

```bash
# 1. 백업
cp d:/Free_Vue/OCR/ocr-server/main.py \
   d:/Free_Vue/OCR/ocr-server/backup/main_20260520_HHMM_before_jpeg_quality.py

# 2. main.py에서 JPEG quality 95 -> 85 적용
#    적용은 에디터 또는 apply_patch로 수행

# 3. 정적 검증
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python -m py_compile d:/Free_Vue/OCR/ocr-server/main.py

# 4. 현재 9099 프로세스 확인
powershell -Command "Get-NetTCPConnection -LocalPort 9099 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess"
powershell -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<PID>' | Select-Object ProcessId,CommandLine"

# 5. 서버 재기동
#    환경 정합성 정리 전이면 현재 방식과 동일하게 재기동:
cd d:/Free_Vue/OCR/ocr-server
"C:/Users/jinsung/AppData/Local/Programs/Python/Python312/python.exe" main.py

#    환경 정합성을 먼저 정리한다면 venv 기준 재기동:
cd d:/Free_Vue/OCR/ocr-server
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python main.py

# 6. 회귀 스크립트 실행
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python tmp/verify_jpeg_quality_regression.py --phase after
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python tmp/verify_jpeg_quality_regression.py --compare
```

### 2-7. 회귀 검증 스크립트 (전체 본문)

다음 단계에서 `tmp/verify_jpeg_quality_regression.py`로 저장해 실행하는 것을 권장한다. 이번 작업에서는 파일로 생성하지 않았고 실행하지 않았다.

```python
import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path

import requests

ENDPOINT = "http://localhost:9099/ocr/extract"
TEMPLATES_ENDPOINT = "http://localhost:9099/templates"

ROOT = Path(r"D:/Free_Vue/OCR")
INVOICE_DIR = ROOT / "mysuit-ocr/public/data/testsets/invoice_statement"
BASELINE_DIR = ROOT / "mysuit-ocr/public/data/testsets/baseline"
OUT_DIR = ROOT / "tmp/safe_perf_jpeg_quality_regression"

INVOICE_CASES = [
    {"name": "거래_1", "template_id": "TPL-31D13CF3", "file": "1.jpg", "expected_rows": 28, "documentType": "invoice_statement"},
    {"name": "거래_2", "template_id": "TPL-5A8C2374", "file": "2.pdf", "expected_rows": 13, "documentType": "invoice_statement"},
    {"name": "거래_3", "template_id": "TPL-E4B15A22", "file": "3.pdf", "expected_rows": 1, "documentType": "invoice_statement"},
    {"name": "거래_4", "template_id": "TPL-FD07531C", "file": "4.pdf", "expected_rows": 1, "documentType": "invoice_statement"},
    {"name": "거래_5", "template_id": "TPL-B8936EDE", "file": "5.pdf", "expected_rows": 6, "documentType": "invoice_statement"},
    {"name": "거래_6", "template_id": "TPL-95328E52", "file": "6.pdf", "expected_rows": 6, "documentType": "invoice_statement"},
    {"name": "거래_7", "template_id": "TPL-3AFD383E", "file": "7.pdf", "expected_rows": 1, "documentType": "invoice_statement"},
]

RECEIPT_CASES = [
    {"name": "영수증_1", "template_id": "TPL-003", "file": "1.jpg"},
    {"name": "영수증_2", "template_id": "TPL-003", "file": "2.jpg"},
    {"name": "영수증_3", "template_id": "TPL-003", "file": "3.jpg"},
    {"name": "영수증_4", "template_id": "TPL-003", "file": "4.jpg"},
    {"name": "영수증_7", "template_id": "TPL-003", "file": "7.jpg"},
    {"name": "영수증_8", "template_id": "TPL-003", "file": "8.jpg"},
    {"name": "영수증_10", "template_id": "TPL-003", "file": "10.jpg"},
    {"name": "영수증_a1", "template_id": "TPL-003", "file": "a1.jpg"},
    {"name": "영수증_a2", "template_id": "TPL-003", "file": "a2.jpg"},
]

SEMANTIC_REMOVE_KEYS = {
    "processed_image",
    "original_image",
    "processing_time",
    "timings",
    "templatePerformanceDebug",
    "templateImageNormalization",
    "extract_debug",
}

RECEIPT_FIELDS = ["회사명", "사업자번호", "대표자", "전화번호", "주소", "총합계금액"]


def safe_name(case):
    return case["name"].replace("/", "_").replace("\\", "_")


def load_templates():
    try:
        res = requests.get(TEMPLATES_ENDPOINT, timeout=20)
        res.raise_for_status()
        items = res.json()
    except Exception as exc:
        print(f"[WARN] template fetch failed; fallback to hardcoded ids only: {exc}")
        return {}

    by_id = {}
    for item in items:
        tid = str(item.get("template_id") or "")
        tpl = item.get("template_json") or {}
        if tid:
            by_id[tid] = tpl
    return by_id


def response_size_bytes(path):
    return path.stat().st_size if path.exists() else 0


def strip_for_semantic_compare(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in SEMANTIC_REMOVE_KEYS:
                continue
            out[k] = strip_for_semantic_compare(v)
        return out
    if isinstance(obj, list):
        return [strip_for_semantic_compare(v) for v in obj]
    return obj


def normalize_receipt_fields(resp):
    fields = resp.get("receipt_fields") or {}
    out = {}
    for key in RECEIPT_FIELDS:
        out[key] = fields.get(key, "")
    return out


def invoice_row_count(resp):
    doc = resp.get("document_fields") or {}
    rows = doc.get("tableRows") or []
    if isinstance(rows, list):
        return len(rows)
    return 0


def invoice_core(resp):
    doc = resp.get("document_fields") or {}
    return {
        "doc_type": resp.get("doc_type") or resp.get("documentType"),
        "supplierBusinessNo": doc.get("supplierBusinessNo", ""),
        "supplierName": doc.get("supplierName", ""),
        "buyerBusinessNo": doc.get("buyerBusinessNo", ""),
        "buyerName": doc.get("buyerName", ""),
        "totalAmount": doc.get("totalAmount", ""),
        "rowCount": invoice_row_count(resp),
    }


def post_case(case, kind, template_map):
    if kind == "invoice":
        file_path = INVOICE_DIR / case["file"]
    else:
        file_path = BASELINE_DIR / case["file"]

    tpl = template_map.get(case["template_id"], {})
    regions = tpl.get("regions") or []
    document_type = case.get("documentType") or tpl.get("documentType") or ""

    form = {
        "template_id": case["template_id"],
        "model_id": "paddleocr",
    }
    if document_type:
        form["documentType"] = document_type
    if kind == "invoice" and regions:
        form["regions"] = json.dumps(regions, ensure_ascii=False)

    start = time.perf_counter()
    with file_path.open("rb") as f:
        files = {"file": (case["file"], f)}
        res = requests.post(ENDPOINT, data=form, files=files, timeout=300)
    elapsed = time.perf_counter() - start
    res.raise_for_status()
    data = res.json()
    data["_regression_meta"] = {
        "case": case["name"],
        "kind": kind,
        "file": str(file_path),
        "wallClockSeconds": round(elapsed, 3),
        "responseSizeBytes": len(res.content),
    }
    return data


def run_phase(phase):
    if phase not in {"before", "after"}:
        raise ValueError("phase must be before or after")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    template_map = load_templates()
    summary = {"phase": phase, "endpoint": ENDPOINT, "invoice": [], "receipt": []}

    for case in INVOICE_CASES:
        print(f"[{phase}] invoice {case['name']} {case['file']}")
        data = post_case(case, "invoice", template_map)
        out_path = OUT_DIR / f"{phase}_invoice_{safe_name(case)}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        core = invoice_core(data)
        summary["invoice"].append({
            "case": case["name"],
            "file": case["file"],
            "expectedRows": case["expected_rows"],
            "actualRows": core["rowCount"],
            "rowCountPass": core["rowCount"] == case["expected_rows"],
            "processing_time": data.get("processing_time"),
            "wallClockSeconds": data["_regression_meta"]["wallClockSeconds"],
            "responseSizeBytes": data["_regression_meta"]["responseSizeBytes"],
            "core": core,
        })

    for case in RECEIPT_CASES:
        print(f"[{phase}] receipt {case['file']}")
        data = post_case(case, "receipt", template_map)
        out_path = OUT_DIR / f"{phase}_receipt_{safe_name(case)}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        fields = normalize_receipt_fields(data)
        filled = sum(1 for v in fields.values() if str(v).strip())
        summary["receipt"].append({
            "case": case["name"],
            "file": case["file"],
            "processing_time": data.get("processing_time"),
            "wallClockSeconds": data["_regression_meta"]["wallClockSeconds"],
            "responseSizeBytes": data["_regression_meta"]["responseSizeBytes"],
            "fields": fields,
            "filledCount": filled,
            "fillRate": round(filled / len(RECEIPT_FIELDS), 4),
        })

    summary_path = OUT_DIR / f"{phase}_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote {summary_path}")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def compare():
    before_summary = load_json(OUT_DIR / "before_summary.json")
    after_summary = load_json(OUT_DIR / "after_summary.json")
    result = {"invoice": [], "receipt": [], "sizes": {}, "pass": True}

    before_inv = {r["case"]: r for r in before_summary["invoice"]}
    after_inv = {r["case"]: r for r in after_summary["invoice"]}
    for case in INVOICE_CASES:
        name = case["name"]
        b = before_inv[name]
        a = after_inv[name]
        same_core = b["core"] == a["core"]
        row_ok = a["actualRows"] == case["expected_rows"] == b["actualRows"]
        ok = same_core and row_ok
        result["invoice"].append({
            "case": name,
            "file": case["file"],
            "sameCore": same_core,
            "rowCountOk": row_ok,
            "beforeRows": b["actualRows"],
            "afterRows": a["actualRows"],
            "beforeSizeBytes": b["responseSizeBytes"],
            "afterSizeBytes": a["responseSizeBytes"],
        })
        result["pass"] = result["pass"] and ok

    before_rec = {r["case"]: r for r in before_summary["receipt"]}
    after_rec = {r["case"]: r for r in after_summary["receipt"]}
    for case in RECEIPT_CASES:
        name = case["name"]
        b = before_rec[name]
        a = after_rec[name]
        same_fields = b["fields"] == a["fields"]
        same_fill = b["filledCount"] == a["filledCount"]
        ok = same_fields and same_fill
        result["receipt"].append({
            "case": name,
            "file": case["file"],
            "sameReceiptFields": same_fields,
            "sameFilledCount": same_fill,
            "beforeFillRate": b["fillRate"],
            "afterFillRate": a["fillRate"],
            "beforeSizeBytes": b["responseSizeBytes"],
            "afterSizeBytes": a["responseSizeBytes"],
        })
        result["pass"] = result["pass"] and ok

    before_total = sum(r["responseSizeBytes"] for r in before_summary["invoice"] + before_summary["receipt"])
    after_total = sum(r["responseSizeBytes"] for r in after_summary["invoice"] + after_summary["receipt"])
    reduction = 0.0 if before_total == 0 else (before_total - after_total) / before_total * 100.0
    result["sizes"] = {
        "beforeTotalBytes": before_total,
        "afterTotalBytes": after_total,
        "reductionPercent": round(reduction, 2),
    }

    out_path = OUT_DIR / "compare_summary.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[OK] wrote {out_path}")
    if not result["pass"]:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["before", "after"])
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    if args.phase:
        run_phase(args.phase)
    if args.compare:
        compare()
    if not args.phase and not args.compare:
        parser.error("use --phase before, --phase after, or --compare")


if __name__ == "__main__":
    main()
```

권장 실행 순서:

```bash
# 적용 전 baseline 수집
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python tmp/verify_jpeg_quality_regression.py --phase before

# JPEG quality 적용 + 서버 재기동 후
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python tmp/verify_jpeg_quality_regression.py --phase after

# 비교
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python tmp/verify_jpeg_quality_regression.py --compare
```

### 2-8. 합격 기준

필수 PASS 기준:

- 거래명세서 7개 모두 `document_fields.tableRows` rowCount가 before와 after에서 동일.
- 거래명세서 expected rowCount 유지:
  - `28/13/1/1/6/6/1`
- 거래명세서 핵심 필드 semantic compare 동일:
  - `supplierBusinessNo`, `supplierName`, `buyerBusinessNo`, `buyerName`, `totalAmount`
- 영수증 9개 `receipt_fields` 핵심 6필드 byte-for-byte 동일:
  - `회사명`, `사업자번호`, `대표자`, `전화번호`, `주소`, `총합계금액`
- 영수증 9개 fillRate 하락 없음.
- `processing_time`은 JPEG 인코딩 영향이 작을 수 있으므로 PASS 필수 기준이 아니라 참고값으로 본다.
- response size 평균 감소 목표:
  - 최소 목표: 평균 5% 이상 감소
  - 기대 목표: processed image 비중이 큰 응답에서 10% 이상 감소
- Preview/History/TestWorkspace processed image 시각 품질은 수동 확인 필요.

FAIL 기준:

- 핵심 필드가 하나라도 달라짐.
- 거래명세서 rowCount가 하나라도 달라짐.
- 영수증 fillRate가 하나라도 하락.
- preview 이미지가 UI 확인에 부적합할 정도로 열화.

### 2-9. 롤백 절차

```bash
cp d:/Free_Vue/OCR/ocr-server/backup/main_20260520_HHMM_before_jpeg_quality.py \
   d:/Free_Vue/OCR/ocr-server/main.py

d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python -m py_compile d:/Free_Vue/OCR/ocr-server/main.py

# 서버 재기동 후 회귀 재확인
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python tmp/verify_jpeg_quality_regression.py --phase after
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python tmp/verify_jpeg_quality_regression.py --compare
```

PowerShell:

```powershell
Copy-Item -LiteralPath d:\Free_Vue\OCR\ocr-server\backup\main_20260520_HHMM_before_jpeg_quality.py `
  -Destination d:\Free_Vue\OCR\ocr-server\main.py -Force
```

## 3. `_warmup_ocr()` 보강 분석

### 3-1. 현재 코드

```python
558: @app.on_event("startup")
559: def _warmup_ocr():
560:     """서버 시작 시 OCR 엔진 미리 로드 (첫 요청 지연 방지)"""
561:     import threading
562:     def _load():
563:         engine = get_ocr_engine()
564:         import numpy as np
565:         dummy = np.ones((100, 100, 3), dtype=np.uint8) * 255
566:         engine.ocr(dummy)
567:         print("[OCR] Engine warmed up")
568:     threading.Thread(target=_load, daemon=True).start()
```

관련 싱글톤:

```python
989: _ocr_engine = None

992: def get_ocr_engine():
993:     global _ocr_engine
994:     if _ocr_engine is None:
995:         import os
996:         from paddleocr import PaddleOCR
997:         _ocr_engine = PaddleOCR(
...
1010:             text_recognition_batch_size=30,
1011:         )
1012:     return _ocr_engine
```

### 3-2. 현재 동작 위험 시나리오

- 시나리오 1: warmup thread 내부에서 PaddleOCR import/model load/`engine.ocr(dummy)` 실패
  - 현재는 예외를 잡지 않아 background thread traceback이 출력될 수 있다.
  - daemon thread 예외라 서버 startup 자체를 중단시키지는 않을 가능성이 높다.
- 시나리오 2: warmup 진행 중 첫 OCR 요청 유입
  - `_ocr_engine is None` 체크와 생성 구간에 lock이 없다.
  - warmup thread와 request thread가 동시에 `get_ocr_engine()`에 들어가면 중복 초기화 가능성이 있다.
- 시나리오 3: startup hook 중복 추가
  - 1차 분석에서 제안된 신규 hook을 추가하면 warmup thread가 둘 이상 생길 수 있다.
  - 중복 초기화 가능성이 커진다.
- 시나리오 4: daemon thread와 서버 종료
  - daemon thread는 서버 종료 시 완료를 보장하지 않는다.
  - warmup은 best-effort 성격이므로 괜찮지만, 종료 중 traceback/log noise 가능성은 있다.

### 3-3. 보강 옵션 비교

| 옵션 | 변경 규모 | 위험 | 효과 | 권고 |
|---|---:|---|---|---|
| A: `_load()`에 `try/except`만 추가 | 최소 | 매우 낮음 | warmup 실패 traceback을 non-fatal 로그로 정리 | 🟢 Go |
| B: A + `_warmup_done` idempotent guard | 소 | 낮음 | startup hook 중복 호출 시 warmup 반복 방지 | 🟡 Conditional |
| C: A + `_engine_lock`으로 `get_ocr_engine()` double-checked locking | 중 | 낮음~중 | warmup/첫 요청 race 차단 | 🟡 Conditional |

권고:

- 다음 JPEG quality 적용과 같은 단계에서는 **옵션 A만 적용**하는 것이 가장 안전하다.
- 옵션 B는 `_warmup_done` 전역 상태를 추가하므로 효과 대비 필요성이 낮다. startup hook은 현재 하나뿐이다.
- 옵션 C는 race를 가장 잘 막지만 `get_ocr_engine()` 공통 경로를 바꾸는 변경이다. batch size 변경 또는 warmup 안정화 전용 작업에서 별도 적용하는 편이 낫다.

### 3-4. 권고 옵션 정확한 diff (적용 안 함)

옵션 A:

```diff
diff --git a/ocr-server/main.py b/ocr-server/main.py
--- a/ocr-server/main.py
+++ b/ocr-server/main.py
@@
 @app.on_event("startup")
 def _warmup_ocr():
     """서버 시작 시 OCR 엔진 미리 로드 (첫 요청 지연 방지)"""
     import threading
     def _load():
-        engine = get_ocr_engine()
-        import numpy as np
-        dummy = np.ones((100, 100, 3), dtype=np.uint8) * 255
-        engine.ocr(dummy)
-        print("[OCR] Engine warmed up")
+        try:
+            engine = get_ocr_engine()
+            import numpy as np
+            dummy = np.ones((100, 100, 3), dtype=np.uint8) * 255
+            engine.ocr(dummy)
+            print("[OCR] Engine warmed up")
+        except Exception as e:
+            print(f"[OCR] warmup failed (non-fatal): {e}")
     threading.Thread(target=_load, daemon=True).start()
```

옵션 C를 별도 단계에서 적용한다면 권장 diff:

```diff
diff --git a/ocr-server/main.py b/ocr-server/main.py
--- a/ocr-server/main.py
+++ b/ocr-server/main.py
@@
-_ocr_engine = None
+_ocr_engine = None
+_engine_lock = threading.Lock()
@@
 def get_ocr_engine():
     global _ocr_engine
     if _ocr_engine is None:
-        import os
-        from paddleocr import PaddleOCR
-        _ocr_engine = PaddleOCR(
+        with _engine_lock:
+            if _ocr_engine is None:
+                import os
+                from paddleocr import PaddleOCR
+                _ocr_engine = PaddleOCR(
```

주의: 옵션 C는 파일 상단 또는 해당 scope에 `threading` import가 필요하다. 현재 warmup 함수 안에서만 `import threading`을 하므로, 이 변경은 A보다 범위가 크다.

### 3-5. 회귀 검증 시 추가 확인 항목

- 서버 재기동 로그에서 `[OCR] Engine warmed up` 또는 `[OCR] warmup failed (non-fatal): ...` 확인.
- warmup 로그가 뜨기 전 첫 요청을 넣었을 때도 정상 응답하는지 별도 단계에서 확인.
- 첫 요청과 두 번째 요청의 wall time 차이 기록.
- 중복 startup hook이 추가되지 않았는지 `rg -n "@app.on_event\\(\"startup\"\\)" ocr-server/main.py`로 확인.

## 4. 9099 기동 방식 정합성

### 4-1. 현재 환경 비교

| 환경 | paddleocr | paddlepaddle | PyMuPDF | 비고 |
|---|---|---|---|---|
| 시스템 Python 3.12, 현재 9099 command | 조회 안 됨 | 조회 안 됨 | `1.27.2.3` | `pip show` 기준 OCR 핵심 패키지가 보이지 않음 |
| `.venv` | `3.4.1` | `3.3.1` CPU build | `1.27.2.2` | 1차 분석 기준 OCR 실행 의존성 존재 |

현재 9099 기동 명령:

```text
"C:\Users\jinsung\AppData\Local\Programs\Python\Python312\python.exe" main.py
```

문제점:

- 현재 프로세스 command line은 시스템 Python이지만, 시스템 Python의 `pip show`에서는 `paddleocr/paddlepaddle`이 조회되지 않았다.
- 실제 프로세스가 어떤 `sys.path`/환경변수로 의존성을 찾는지 불명확하다.
- 적용 전/후 비교에서 Python 환경이 바뀌면 JPEG quality 변경의 효과와 환경 변경 효과가 섞인다.
- `ocr-server/requirements.txt`에는 현재 `paddleocr`, `paddlepaddle`, `PyMuPDF`가 명시되어 있지 않다.

### 4-2. 권고 방향

권고: **venv로 통일**

사유:

- 프로젝트 경로에 전용 `.venv`가 있고, 해당 venv에는 OCR 핵심 패키지가 확인된다.
- 적용/롤백/회귀 검증을 재현 가능하게 만들려면 실행 Python을 하나로 고정해야 한다.
- 현재 시스템 Python은 `pip show` 기준으로 OCR 핵심 패키지가 보이지 않아 운영 표준으로 삼기 어렵다.

단, JPEG quality 1차 적용만 빠르게 검증한다면 다음 중 하나를 선택해야 한다.

- 보수안: 현재 9099와 같은 시스템 Python 방식으로 before/after를 모두 실행한다.
- 정리안: 적용 전에 venv 기동으로 전환하고, venv 기준 before를 새로 수집한 뒤 JPEG quality를 적용한다.

비교 정확도는 정리안이 더 좋다.

### 4-3. 마이그레이션 절차

다음 적용 단계에서만 실행:

```powershell
# 현재 9099 PID 확인
$conn = Get-NetTCPConnection -LocalPort 9099 -State Listen -ErrorAction Stop
$pid = $conn.OwningProcess
Get-CimInstance Win32_Process -Filter "ProcessId=$pid" | Select-Object ProcessId,CommandLine

# 현재 프로세스 stop
Stop-Process -Id $pid -Force

# venv 기준 start
Set-Location d:\Free_Vue\OCR\ocr-server
$out = Join-Path (Get-Location) "safe_perf_backend.out.log"
$err = Join-Path (Get-Location) "safe_perf_backend.err.log"
Start-Process -FilePath d:\Free_Vue\OCR\ocr-server\.venv\Scripts\python.exe `
  -ArgumentList @("main.py") `
  -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $out `
  -RedirectStandardError $err
```

requirements.txt 보강 권고:

현재 `ocr-server/requirements.txt`:

```text
fastapi==0.115.0
uvicorn==0.30.6
python-multipart==0.0.9
opencv-python-headless==4.10.0.84
numpy==1.26.4
Pillow==10.4.0
```

추가 검토 필요:

- `paddleocr==3.4.1`
- `paddlepaddle==3.3.1`
- `PyMuPDF==1.27.2.2` 또는 현재 표준 버전
- 기타 `main.py` import 의존성

이번 단계에서는 requirements를 수정하지 않는다.

## 5. 다음 적용 단계 권장 진행 순서

1. 9099 기동 방식 정합성 결정
   - 권장: venv 기준으로 전환 후 before baseline 재수집.
   - 단, 빠른 적용이 목표라면 현재 시스템 Python 방식으로 before/after를 모두 맞춘다.
2. `tmp/verify_jpeg_quality_regression.py --phase before` 실행.
3. `main.py` 백업.
4. JPEG quality `95→85` 단독 적용.
5. `py_compile`.
6. 서버 재기동.
7. `tmp/verify_jpeg_quality_regression.py --phase after` 실행.
8. `tmp/verify_jpeg_quality_regression.py --compare` 실행.
9. Preview/History/TestWorkspace processed image 수동 확인.
10. 별도 단계에서 `_warmup_ocr()` 옵션 A 적용 여부 결정.
11. batch size `30→64`는 별도 플레이북과 메모리 계측 후 진행.

## 6. 미해결 / 추가 필요 사항

- 현재 9099 시스템 Python 프로세스가 `paddleocr`를 어떻게 로드하고 있는지 확인 필요. `pip show` 결과와 실행 상태가 맞지 않는다.
- `requirements.txt`가 실제 OCR 실행 의존성을 충분히 담고 있지 않다.
- JPEG quality 85의 response size 감소율은 before/after JSON 수집 후 확정해야 한다.
- Preview 이미지 열화 여부는 자동화보다 수동 확인이 안전하다.
- `_warmup_ocr()` race 완전 차단은 옵션 C가 필요하지만, JPEG quality 적용과 묶기보다는 별도 안정화 단계가 적절하다.

## 7. 최종 판단

| 항목 | 판단 |
|---|---|
| JPEG quality 95→85 | 다음 적용 단계 진행 가능 |
| 기존 `_warmup_ocr()` 보강 | 옵션 A만 가벼운 안정화로 권장. 신규 hook 추가 금지 |
| 9099 환경 정합성 | venv 통일 권장. 최소한 before/after는 같은 Python 환경에서 수행 |
| 회귀 자동화 | 본 문서의 `verify_jpeg_quality_regression.py` 본문 사용 권장 |
| batch size 64 | 이번 적용 범위 밖. 별도 메모리/성능 검증 필요 |
| enable_mkldnn True | 계속 No-go |
