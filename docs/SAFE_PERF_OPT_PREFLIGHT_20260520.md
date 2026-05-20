# Safe Performance Optimization — Preflight Analysis

**날짜**: 2026-05-20  
**도구**: Codex  
**상태**: 분석 단계 (코드 미수정)

## 0. 사전 필독 확인

아래 5개 문서를 읽고 본 사전 분석에 반영했다.

| 문서 | 확인 |
|---|---|
| `d:/Free_Vue/OCR/CLAUDE.md` | 확인 완료 |
| `d:/Free_Vue/OCR/SESSION_SUMMARY.md` | 확인 완료 |
| `d:/Free_Vue/OCR/docs/BASELINE_LOCK_20260425.md` | 확인 완료 |
| `d:/Free_Vue/OCR/docs/GOOGLE_LOCK_20260425.md` | 확인 완료 |
| `d:/Free_Vue/OCR/docs/T28_PERF3_table_crop_ocr_defer_20260520.md` | 확인 완료 |

주요 전제:

- `main.py`, OCR/parser 로직, testset, lock 문서는 이번 작업에서 수정하지 않았다.
- baseline/google lock은 회귀 방지 기준으로 유지되어야 한다.
- T28-PERF3 table crop OCR defer는 별도 최적화 이력으로 존재하며, 이번 4개 후보와 충돌 가능성을 별도 점검해야 한다.

## 1. 환경 검증 결과

| 항목 | 결과 |
|---|---|
| 백업 디렉토리 | 존재 확인: `d:/Free_Vue/OCR/ocr-server/backup/` |
| 백업 디렉토리 권한 | ACL상 현재 사용자에 Modify 권한 있음. 실제 쓰기 테스트는 지시상 수행하지 않음 |
| 거래명세서 7개 파일 | 존재 확인: `1.jpg`, `2.pdf`, `3.pdf`, `4.pdf`, `5.pdf`, `6.pdf`, `7.pdf` |
| 영수증 9개 파일 (9.jpg 제외) | 존재 확인: `1.jpg`, `2.jpg`, `3.jpg`, `4.jpg`, `7.jpg`, `8.jpg`, `10.jpg`, `a1.jpg`, `a2.jpg` |
| `invoice_statement/ground_truth.json` | 존재 확인. 7개 대상 entry 모두 있음 |
| `baseline/ground_truth.json` | 존재 확인. 9개 대상 entry 모두 있음. `9.jpg` entry도 있으나 제외 가능 |
| 9099 포트 백엔드 | 떠 있음. `http://localhost:9099/docs` HTTP 200 |
| 9099 PID | `23196` |
| 9099 기동 명령 | `"C:\Users\jinsung\AppData\Local\Programs\Python\Python312\python.exe" main.py` |
| paddleocr 버전 | `3.4.1` |
| paddlepaddle | `3.3.1` CPU build |
| paddlepaddle-gpu | 설치 안 됨 |

추가 메모:

- 환경 정보에는 venv Python이 `d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python`으로 지정되어 있으나, 현재 9099 프로세스는 시스템 Python 3.12로 `main.py`를 실행 중이다. 실제 적용/재기동 단계에서는 같은 방식으로 띄울지, venv로 통일할지 먼저 결정하는 것이 안전하다.
- 이번 사전 점검에서는 OCR API 호출, 서버 재기동, 백업 파일 생성, 운영 코드 수정은 수행하지 않았다.

## 2. 코드 위치 검증

### 변경 후보 ① `text_recognition_batch_size=30` → `64`

- 실제 line: `ocr-server/main.py:1010`
- 지시서 line 1010과 일치한다.
- 현재 코드:

```python
1005:             # NOTE: enable_mkldnn=True 는 현재 PaddlePaddle 빌드(PIR executor)에서
1006:             #       `ConvertPirAttribute2RuntimeAttribute not support ...ArrayAttribute<DoubleAttribute>`
1007:             #       런타임 에러로 inference 실패 → False 유지. paddle 버전이 PIR+oneDNN 지원 시 재검토.
1008:             enable_mkldnn=False,
1009:             cpu_threads=os.cpu_count() or 4,
1010:             text_recognition_batch_size=30,
1011:         )
1012:     return _ocr_engine
```

- 맥락:

```python
992: def get_ocr_engine():
993:     global _ocr_engine
994:     if _ocr_engine is None:
995:         import os
996:         from paddleocr import PaddleOCR
997:         _ocr_engine = PaddleOCR(
998:             lang="korean",
999:             text_detection_model_name="PP-OCRv5_mobile_det",
1000:             text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
1001:             device="cpu",
1002:             use_textline_orientation=False,
1003:             use_doc_orientation_classify=False,  # 자체 detect_orientation 사용, 중복 제거
1004:             use_doc_unwarping=False,             # UVDoc 비활성화 (영수증에 불필요, 속도 주범)
```

- 의존성/부수 효과:
  - `_ocr_engine`은 전역 싱글톤이므로 값 변경 후 서버 재기동 또는 프로세스 재생성이 필요하다.
  - 현재 `device="cpu"`이고 `paddlepaddle-gpu`가 설치되어 있지 않으므로 T4 GPU 16GB는 이 설정의 직접 대상이 아니다.
  - batch size 증가는 recognition 단계의 처리량을 늘릴 수 있으나 CPU 메모리/RSS 증가와 일부 이미지에서 latency 변동이 가능하다.
  - OCR 결과값 자체를 의도적으로 바꾸는 옵션은 아니지만, OCR 엔진 내부 batching 변경이므로 baseline/google/거래명세서 회귀 검증은 필요하다.
- 회귀 가능성: **중**
  - 인식 결과 변경 가능성은 낮은 편이나, CPU 메모리/시간 변동 리스크가 있어 바로 전역 적용은 조건부가 적절하다.
- 롤백:
  - `text_recognition_batch_size=64,`를 `text_recognition_batch_size=30,`으로 되돌리고 서버 재기동.

### 변경 후보 ② 서버 startup 모델 warmup 훅 추가

- FastAPI 앱 선언 실제 line: `ocr-server/main.py:73`
- 현재 코드:

```python
68:     _ADDRESS_CUT_RE, _ADDRESS_CORE_TOKEN_RE, _ADDRESS_STORE_NOISE_RE,
69:     _LABEL_ONLY_RE, _ADDRESS_LABEL_RE, _ADDRESS_CONTINUATION_RE,
70:     _ADDRESS_BROAD_ONLY_RE, _ADDRESS_TRAILING_NOISE_RE,
71: )
72:
73: app = FastAPI(title="MySuit OCR Server")
74:
75:
76: def _parse_amounts(s: str, keyword_context: bool = False) -> list:
77:     cleaned = _clean_number(s)
78:
```

- 이미 존재하는 startup handler:

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

- 의존성/부수 효과:
  - 지시서의 신규 warmup hook은 이미 유사 기능이 존재한다.
  - 새 `@app.on_event("startup")`를 추가하면 warmup이 중복 실행될 수 있다.
  - 현재 `_ocr_engine` 싱글톤 초기화에는 lock이 없으므로, 중복 startup hook 또는 첫 요청과 warmup thread가 겹치면 engine 초기화 race 가능성이 있다.
  - 현재 handler는 background thread로 실행되어 startup 자체를 막지는 않는다. 다만 thread 내부 예외를 잡지 않으므로 warmup 실패 시 로그 traceback이 날 수 있다.
  - 제안 코드의 `np` 사용은 전역 import 여부에 의존하지만, 기존 코드는 함수 내부에서 `numpy`를 import하므로 이 문제를 피하고 있다.
  - lazy load fallback은 `get_ocr_engine()`의 `if _ocr_engine is None:` 구조로 유지된다.
- 회귀 가능성: **중**
  - 인식 결과 변경 가능성은 낮지만, 제안 코드를 그대로 추가하면 중복 warmup/race라는 운영 리스크가 있다.
- 롤백:
  - 새로 추가한 startup hook 전체를 제거한다.
  - 더 안전한 적용 방향은 신규 hook 추가가 아니라 기존 `_warmup_ocr()`에 `try/except`와 idempotent guard를 보강하는 방식이다.

### 변경 후보 ③ `enable_mkldnn=False` → `True`

- 실제 line: `ocr-server/main.py:1008`
- 지시서 line 1008과 일치한다.
- 현재 코드:

```python
1005:             # NOTE: enable_mkldnn=True 는 현재 PaddlePaddle 빌드(PIR executor)에서
1006:             #       `ConvertPirAttribute2RuntimeAttribute not support ...ArrayAttribute<DoubleAttribute>`
1007:             #       런타임 에러로 inference 실패 → False 유지. paddle 버전이 PIR+oneDNN 지원 시 재검토.
1008:             enable_mkldnn=False,
1009:             cpu_threads=os.cpu_count() or 4,
1010:             text_recognition_batch_size=30,
1011:         )
```

- 버전 확인:
  - `paddleocr`: `3.4.1`
  - `paddlepaddle`: `3.3.1`
  - `paddlepaddle-gpu`: 설치 안 됨
- grep 결과:
  - 운영 코드 내 `enable_mkldnn` 관련 별도 guard/fallback 분기는 확인되지 않았다.
  - 현재 주석 외에 런타임 호환성 체크는 없다.
- 의존성/부수 효과:
  - CPU build이므로 `enable_mkldnn`은 무시되는 GPU 옵션이 아니라 실제 CPU inference 경로에 영향을 줄 수 있다.
  - 코드 주석에 PIR executor 비호환 런타임 에러가 명시되어 있다.
  - 실패 시 서버 기동은 되더라도 첫 OCR inference에서 에러가 날 수 있다.
  - 단일 라인 변경이라 rollback은 쉽지만, 적용 실패 영향은 크다.
- 회귀 가능성: **높음**
  - 현재 코드가 명시적으로 실패 이력을 남긴 상태이고, 설치된 PaddlePaddle도 PIR 계열 최신 CPU build다.
- 롤백:
  - `enable_mkldnn=True,`를 `enable_mkldnn=False,`로 되돌리고 서버 재기동.

### 변경 후보 ④ JPEG quality `95` → `85`

- 실제 line: `ocr-server/main.py:2283`
- 현재 코드:

```python
2279:         blur = cv2.GaussianBlur(ocr_img, (0, 0), 1.5)
2280:         ocr_img = cv2.addWeighted(ocr_img, 1.5, blur, -0.5, 0)
2281:
2282:         ocr_h, ocr_w = ocr_img.shape[:2]
2283:         _, img_encoded = cv2.imencode('.jpg', ocr_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
2284:         processed_b64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
2285:         timings["ocr_image_prep_ms"] = _ms(time.time() - _t_ocrp0)
2286:         timings["ocr_image_wh"] = [ocr_w, ocr_h]
2287:         timings["processed_image_wh"] = [ocr_w, ocr_h]
2288:
2289:         # 4. bbox 좌표 스케일 OCR → 미리보기 크기
```

- OCR 호출은 이후에 발생한다:

```python
2296:         _t_fullocr0 = time.time()
2297:         result = ocr.ocr(ocr_img)
2298:         t3 = time.time()
2299:         timings["full_ocr_ms"] = _ms(t3 - _t_fullocr0)
```

- response 삽입 위치:

```python
2755:     if processed_b64:
2756:         response["processed_image"] = f"data:image/jpeg;base64,{processed_b64}"
2757:     if original_b64:
2758:         response["original_image"] = f"data:image/jpeg;base64,{original_b64}"
```

- preprocessingDebug 분기:

```python
2825:     _debug_preprocessing = debugPreprocessing.strip().lower() in ("true", "1", "yes")
2826:     _auto_apply_preprocessing = autoApplyPreprocessing.strip().lower() in ("true", "1", "yes")
2827:     # B-06: auto-apply implies debug mode...
2828:     _run_preprocessing = _debug_preprocessing or _auto_apply_preprocessing
2829:     if _run_preprocessing and not region_list:
2830:         try:
2831:             _prep_debug = _build_preprocessing_debug(
```

- `processed_b64` / `processed_image` 사용 범위:
  - `processed_b64`는 response의 `processed_image` data URL 생성에 쓰인다.
  - OCR은 base64로 인코딩된 JPEG가 아니라 메모리상의 `ocr_img`를 직접 사용한다.
  - frontend에서는 `processed_image`가 Preview/History/TestWorkspace 표시 및 저장용 URL로 사용된다.
  - `cv2.imencode` quality 설정은 `main.py`에서 원본 표시용 quality 80과 processed 표시용 quality 95 두 곳이 확인되며, preprocessingDebug 별도 quality 인코딩은 확인되지 않았다.
- 의존성/부수 효과:
  - OCR 인식 전처리 결과 자체를 바꾸지 않는다.
  - response size, 네트워크 전송량, 프론트 렌더링/저장 부담을 줄일 수 있다.
  - processed preview 시각 품질은 다소 낮아질 수 있다.
- 회귀 가능성: **낮음**
  - OCR 결과 변경 가능성은 매우 낮다. UI 시각 비교는 필요하다.
- 롤백:
  - `cv2.IMWRITE_JPEG_QUALITY, 85`를 `cv2.IMWRITE_JPEG_QUALITY, 95`로 되돌리고 서버 재기동.

## 3. 위험 요소 매트릭스

| 변경 | 인식 결과 변경 가능성 | 가능한 부수 효과 | 즉시 롤백 가능 여부 |
|---|---|---|---|
| ① batch_size 30→64 | 낮음~중. 의도상 인식 로직 변경은 아니나 OCR engine batching 변경 | CPU 메모리 증가, latency 변동, 대용량 문서에서 RSS 상승 | 가능. 단일 라인 복귀 후 재기동 |
| ② startup warmup 추가 | 낮음 | 이미 warmup handler가 있어 중복 실행/race 가능. 현재 handler 예외 처리 미흡 | 가능. 추가 hook 제거. 단, 권장 방향은 기존 hook 보강 |
| ③ enable_mkldnn False→True | 높음 | 코드 주석상 PIR executor 런타임 에러 이력. CPU inference 실패 가능 | 가능. 단일 라인 복귀 후 재기동 |
| ④ JPEG quality 95→85 | OCR 인식 기준 매우 낮음 | processed preview/history 이미지 품질 저하 가능. response size 감소 | 가능. 단일 라인 복귀 후 재기동 |

## 4. 발견된 추가 이슈

- **startup warmup은 이미 존재한다.** 지시서의 신규 hook을 그대로 추가하면 중복 warmup이 된다.
- **현재 warmup handler에는 예외 처리가 없다.** background thread라 startup은 막지 않지만, 실패 시 로그 traceback이 발생할 수 있다.
- **`_ocr_engine` 싱글톤 초기화에는 lock이 없다.** 중복 warmup 또는 첫 요청과 warmup이 겹치면 초기화 race 가능성이 있다.
- **현재 9099 서버는 venv가 아니라 시스템 Python으로 실행 중이다.** 재기동 절차를 표준화해야 적용 후 비교가 정확하다.
- **`enable_mkldnn=True`는 코드 주석상 명시적 실패 이력이 있다.** 현재 PaddlePaddle CPU build에서도 별도 guard 없이 적용하는 것은 위험하다.
- **JPEG quality 변경은 OCR 입력이 아니라 response 이미지에 적용된다.** 성능 효과는 OCR `processing_time`보다는 response size, 전송, 프론트 렌더링에 더 가깝다.

## 5. 권고

| 변경 | 권고 | 사유 |
|---|---|---|
| ① batch_size 64 | 🟡 Conditional | 인식 로직 변경은 아니지만 CPU 메모리/latency 변동 가능. 단독 적용 후 baseline/google/거래명세서/영수증 회귀와 RSS 확인 필요 |
| ② startup warmup | 🔴 No-go as written | 이미 startup warmup이 존재함. 새 hook 추가는 중복/race 가능. 다음 단계에서는 기존 handler 보강 방식만 검토 |
| ③ enable_mkldnn | 🔴 No-go | 현재 코드 주석에 PIR executor 비호환 에러가 명시되어 있고 CPU build에서 직접 영향. 별도 격리 실험 전 운영 적용 비권장 |
| ④ JPEG quality 85 | 🟢 Go | OCR 결과에는 영향이 거의 없고 response size 감소 기대. Preview/History 시각 품질만 확인하면 됨 |

Conditional 조건:

- ①은 단독 변경으로 적용하고, 같은 프로세스/같은 Python 환경에서 before/after를 비교해야 한다.
- ②는 신규 hook 추가가 아니라 기존 `_warmup_ocr()`에 `try/except`, idempotent guard 또는 lock을 넣는 별도 변경으로 재정의해야 한다.
- ③은 운영 반영 전 별도 포트/격리 프로세스에서 최소 거래명세서 7개와 영수증 baseline/google lock 회귀를 통과해야 한다.

## 6. 실제 적용 시 권장 순서

1. **④ JPEG quality 95→85**
   - OCR 결과 영향이 가장 낮다.
   - response size, Preview/History 시각 품질만 확인하면 된다.
2. **① batch_size 30→64**
   - 단독 적용 후 CPU 메모리, wall time, `processing_time`, baseline/google/거래명세서 회귀를 확인한다.
3. **② startup warmup**
   - 새 hook 추가는 하지 않는다.
   - 기존 `_warmup_ocr()`에 예외 처리와 중복 초기화 방지 보강이 필요한지 별도 변경으로 처리한다.
4. **③ enable_mkldnn**
   - 현재는 No-go.
   - 꼭 검토하려면 운영 반영이 아니라 별도 포트/격리 프로세스에서 단독 실험 후 즉시 rollback 가능한 상태로 진행한다.

## 7. 검증 시 권장 사용 명령

아래 명령은 실제 적용 단계에서 사용할 후보이며, 이번 사전 분석에서는 실행하지 않았다.

```bash
# 백업
cp d:/Free_Vue/OCR/ocr-server/main.py d:/Free_Vue/OCR/ocr-server/backup/main_YYYYMMDD_HHMM_before_safe_perf_opt.py

# 정적 검증
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python -m py_compile d:/Free_Vue/OCR/ocr-server/main.py

# 현재 9099 프로세스 확인
powershell -Command "Get-NetTCPConnection -LocalPort 9099 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess"
powershell -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=23196' | Select-Object ProcessId,CommandLine"

# 서버 재기동 후보 1: 현재 관측된 방식에 맞춤
cd d:/Free_Vue/OCR/ocr-server
"C:/Users/jinsung/AppData/Local/Programs/Python/Python312/python.exe" main.py

# 서버 재기동 후보 2: 프로젝트 venv 기준 권장 방식
cd d:/Free_Vue/OCR/ocr-server
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python main.py

# 패키지 버전 재확인
d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python -m pip show paddleocr paddlepaddle paddlepaddle-gpu

# Swagger 확인
curl http://localhost:9099/docs

# 단일 회귀 호출 예시: 거래_1
curl -X POST http://localhost:9099/ocr/extract ^
  -F "file=@D:/Free_Vue/OCR/mysuit-ocr/public/data/testsets/invoice_statement/1.jpg" ^
  -F "template_id=TPL-31D13CF3" ^
  -F "model_id=paddleocr" ^
  -o tmp/after_invoice_1.json

# 단일 회귀 호출 예시: 영수증
curl -X POST http://localhost:9099/ocr/extract ^
  -F "file=@D:/Free_Vue/OCR/mysuit-ocr/public/data/testsets/baseline/1.jpg" ^
  -F "template_id=TPL-003" ^
  -F "model_id=paddleocr" ^
  -o tmp/after_receipt_1.json
```

검증 기준:

- 거래명세서 `거래_1~거래_7` rowCount 유지:
  - `1.jpg=28`, `2.pdf=13`, `3.pdf=1`, `4.pdf=1`, `5.pdf=6`, `6.pdf=6`, `7.pdf=1`
- 영수증 baseline은 `9.jpg` 제외 9개 파일 유지:
  - `1.jpg`, `2.jpg`, `3.jpg`, `4.jpg`, `7.jpg`, `8.jpg`, `10.jpg`, `a1.jpg`, `a2.jpg`
- baseline/google lock 문서 기준 주요 필드와 총합계금액 회귀 없음.
- response size와 processed preview 품질은 ④ 적용 시 별도 확인.
- CPU 메모리/RSS는 ① 적용 시 별도 확인.

## 8. 최종 Go / No-go 요약

| 우선순위 | 변경 | 최종 판단 |
|---|---|---|
| 1 | ④ JPEG quality 95→85 | 🟢 Go |
| 2 | ① batch_size 30→64 | 🟡 Conditional |
| 3 | ② startup warmup | 🔴 No-go as written / 기존 hook 보강만 Conditional |
| 4 | ③ enable_mkldnn False→True | 🔴 No-go |

결론:

- 다음 운영 적용 후보로는 **④ JPEG quality 85**가 가장 안전하다.
- **① batch_size 64**는 단독 적용과 메모리/회귀 검증을 조건으로 진행 가능하다.
- **② startup warmup**은 이미 구현되어 있으므로 새 hook 추가는 하지 않는 것이 맞다.
- **③ enable_mkldnn**은 현재 코드 주석과 설치 버전 기준으로 운영 적용 비권장이다.
