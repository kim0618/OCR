# T-10-preview-overlay-scale-fix 결과

작성일: 2026-05-15

## 1. 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/components/upload/UploadWorkspace.tsx` | `TemplateItem`에 `image?: {width, height}` 추가. `loadLocalTemplates` + server 매핑에서 `template_json.image` 읽기. `OcrDocViewer`에 `originalWidth`/`originalHeight` 전달. |
| `src/components/upload/OcrDocViewer.tsx` | `originalWidth`/`originalHeight` props 추가. `updateScale()`에서 bbox 좌표계 크기 우선 사용. tooltip에 원본/렌더 bbox 비교 표시. |

## 2. 핵심 요약

**두 가지 좌표계 불일치**:

| 구분 | 크기 | 이유 |
|------|------|------|
| Backend PDF render (bbox 기준) | 1654×1169 (5.pdf landscape) | PyMuPDF 200 DPI = 200/72 scale |
| Frontend PDF display (화면 표시) | 1190×841 (5.pdf landscape) | UploadWorkspace scale=2 고정 |
| 비율 | 1654/1190 = 1.39× 차이 | overlay box가 39% 크게 표시됨 |

OcrDocViewer는 `scale.x = offsetWidth / img.naturalWidth`로 계산. 이때 `img.naturalWidth`는 frontend display size (1190)이고 bbox는 backend original size (1654). 두 값이 달라서 overlay가 어긋남.

**수정**: template.image.width/height (backend 200 DPI 기준 원본 크기)를 OcrDocViewer에 전달. `updateScale()`에서 이를 bbox 좌표계 크기로 사용:
```
scale.x = img.offsetWidth / originalWidth  (1654)
```

## 3. 원인

- Backend: PyMuPDF 200 DPI (`200/72 ≈ 2.778` scale) → 5.pdf 1654px
- Frontend display: pdf.js `scale: 2` → 5.pdf 1190px  
- OcrAnnotator (template 생성 시): `scale = 200/72` → 1654px (backend와 일치)
- 따라서 template.image.width = 1654 (backend 좌표계)
- UploadWorkspace display = 1190 (frontend 좌표계)
- 불일치: 1654/1190 = 1.39× → overlay가 39% 크게 위치 어긋남

## 4. 좌표 변환 방식

- **original size**: `template.image.width / template.image.height` (template_json.image에서 로드)
  - 5.pdf: 1654×1169, 2.pdf: 1654×2338, 1.jpg: 2483×3511
- **displayed size**: `img.offsetWidth / img.offsetHeight` (실제 화면 크기)
- **scaleX**: `img.offsetWidth / originalWidth`
- **scaleY**: `img.offsetHeight / originalHeight`
- **offset 처리**: 없음 (이미지가 container에 width:100% fill로 렌더링됨)
- **fallback**: `originalWidth` 없으면 기존 `img.naturalWidth` 사용 (기존 동작 유지)

## 5. 개선 결과

| 대상 | 기존 문제 | 수정 후 |
|------|-----------|---------|
| 7.pdf (template) | overlay가 1.39× 크고 위치 어긋남 | template.image 크기 기준 scale 적용 → 올바른 위치 |
| 5.pdf (template) | 동일 39% 오프셋 | template.image.width=1654 기준 보정 |
| 2.pdf (template) | portrait A4, 동일 오프셋 | template.image 기준 보정 |
| 1.jpg (template) | previewUrl = original JPG (2483px) → naturalWidth=2483 = template.image.width → 기존 이미 정확 | originalWidth=2483 사용, 동작 동일 |
| 템플릿 없음 mode | originalWidth 미제공 → 기존 naturalWidth 사용 | 회귀 없음 |

## 6. 수동 확인 가이드

서버 재시작 후 (`npm run dev` + python main.py):

1. `http://localhost:8089/runocr` 접속
2. 7.pdf 업로드 + 거래_7 template 선택 + RunOCR 실행
3. **Preview 탭 (왼쪽 이미지)**:
   - overlay badge가 실제 문서 필드 위에 표시되는지 확인
   - table region이 하단 전체를 덮는 대신 실제 표 영역만 강조하는지 확인
   - badge tooltip에 "original bbox: x,y, w×h / rendered: x,y, w×h" 표시 확인
4. **1.jpg RunOCR** 실행 후 overlay 위치 회귀 없는지 확인

## 7. 검증 결과

- **typecheck**: PASS ✅
- **build**: PASS ✅ (전체 페이지 빌드 성공)

## 8. 남은 문제

1. **7.pdf template 미저장**: 7.pdf RunOCR을 실행하려면 template annotation 저장 필요.
   - UI에서 7.pdf 업로드 → annotation → 저장 후 RunOCR 가능

2. **object-fit letterbox**: 이미지가 container에 letterbox 방식으로 들어가면 추가 offset 필요.
   - 현재 `width: 100%` fill 방식이면 문제 없음

3. **full OCR mode (no template)**: `processedImageUrl`이 설정될 때의 좌표 정확도는 별도 확인 필요.

## 9. 다음 작업 판단

- **overlay scale 보정 완료** → 7.pdf annotation 저장 후 RunOCR E2E 검증 진행
- 7.pdf overlay 여전히 어긋나면 → object-fit letterbox offset 추가 보정 필요
- template image 메타데이터 없는 경우 → annotation 재저장으로 image 크기 포함
