# T-10-preview-label-overlay-fix 결과

작성일: 2026-05-15

## 1. 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/lib/invoiceFieldLabels.ts` | 신규 생성: invoice_statement 필드 한글/영문 라벨 매핑 유틸 |
| `src/components/upload/UploadWorkspace.tsx` | template mode에서 `raw.fields`에 ko/en 라벨 주입 |
| `src/components/upload/OcrDocViewer.tsx` | overlay badge: 라벨 표시 + large region ⚠ 경고 + 상세 tooltip |
| `src/components/upload/OcrResultPanel.tsx` | fieldLabel 개선 + 필드 헤더에 라벨 표시 + table 요약 (N행) |

## 2. 핵심 요약

- **필드명 표시**: field_1, field_2 등 내부명 대신 한글 라벨 우선 표시. template region의 `koField`/`enField` → 없으면 canonical key 매핑 → 없으면 내부명.
- **overlay badge**: 번호 + 짧은 필드명 표시. 표 영역은 `표` 배지. 큰 영역(height>20% or width>80%)은 ⚠ 갈색 배지.
- **tooltip**: 필드명, key, rawId, source, bbox, 신뢰도 상세 표시.
- **table 요약**: "표 데이터 · N행" + 첫 행 미리보기.
- **Validation 탭**: 필드명을 한글 라벨 full로 표시.

## 3. 필드명 표시 개선

| 기존 | 변경 후 |
|------|---------|
| field_1 | 공급자 (supplierCompany / field_1) |
| field_2 | 공급자 사업자번호 (supplierBusinessNo / field_2) |
| table_1 | 표 데이터 (tableRows / table_1) |
| field_8 | 받는자 주소 (buyerAddress / field_8) |
| (내부명만) | 한글 라벨 + 영문 key + raw id |

## 4. overlay 표시 개선

- **badge 내용**: `[번호] [표] [짧은 라벨]` 형태로 변경
- **large region 경고**: height > imageHeight*0.2 OR width > imageWidth*0.8 → ⚠ 갈색 배지
- **tooltip 내용**: 필드명 / key / raw: field_10 / source: ocr / bbox: x,y,w×h / 신뢰도%
- **cursor: help**: tooltip 있음을 시각적으로 표시

## 5. table_1 표시 개선

- "표 데이터 · N행" 요약 배지 표시
- 첫 번째 행 미리보기: "1행: 품명 / 규격 / 수량 / 단가"
- 기존 table row 목록 유지
- JSON 탭에서 raw 확인 가능 (기존 유지)

## 6. 7.pdf 수동 확인 가이드

1. `npm run dev` 시작 후 `http://localhost:8089/upload` 접속
2. 7.pdf 업로드 + 거래_7 template 선택 + RunOCR 실행
3. **오른쪽 Custom 탭**: field_1 대신 "공급자 (supplierCompany)" 형태로 표시 확인
4. **overlay**: 각 박스에 번호 + 짧은 라벨 표시. table 영역에 "표" 배지 확인
5. **큰 영역**: field_10처럼 큰 region은 ⚠ 갈색 배지로 표시됨
6. **tooltip**: 박스에 마우스 올리면 bbox/source/신뢰도 확인
7. **table 필드**: "표 데이터 · 1행" + 첫 행 미리보기 표시 확인

## 7. 검증 결과

- **typecheck**: PASS ✅ (오류 없음)
- **build**: PASS ✅ (전체 페이지 빌드 성공)

## 8. 남은 문제

1. **overlay 좌표 scale 문제**: template mode에서 `original_b64`는 max 1200px로 축소되는데, bbox는 200 DPI 원본(1654px) 기준. 비율 불일치로 overlay 위치가 실제 영역과 다를 수 있음. 별도 수정 필요.
   - 수정 방법: `original_b64` 생성 시 실제 dimensions를 response에 포함하거나, frontend에서 scale factor를 보정
2. **template region 이름**: OcrAnnotator에서 region 이름을 영/한 명칭으로 설정하면 더 정확한 표시 가능
3. **7.pdf template 없음**: 현재 7.pdf annotation template이 없어 RunOCR E2E 실행 불가. UI annotation 후 T-10-rerun 필요

## 9. 다음 작업 판단

- **Preview 표시 개선 완료** → 7.pdf UI annotation 저장 후 E2E 검증 진행
- overlay 좌표 자체 불일치 → 좌표 변환/scale 별도 디버깅 필요 (scale factor 보정 작업)
