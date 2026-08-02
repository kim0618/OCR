---
name: project_deskew_overapply_chain
description: RunOCR Preview 회전 이슈 추적 체인(3H~3N)과 deskew over-apply 근본원인 + 3O pending 상태
metadata: 
  node_type: memory
  type: project
  originSessionId: 4ca2ff73-b980-4c4f-bdcf-8f7c04dbf942
---

RunOCR Preview "살짝 회전" 이슈 추적 체인 (2026-06-04):

- **근본원인**: `preprocess.py:deskew()`(minAreaRect, threshold 0.5°, confidence gate 없음)가 정방향 표 문서에 허위 소각도를 적용. 7.pdf: orientation 0°인데 deskew -1.64° over-apply → processed_image 기울어 보임. `DESKEW_OVERAPPLY_ON_UPRIGHT_PDF`.
- 호출부: `main.py:~2383` 전체이미지(free) 경로 `deskew(doc_img)`. PDF 전용 skip 없음, orientation과 독립.
- **3J(폐기)**: Preview 원본/OCR 토글 추가 → 사용자 요구 벗어남. **3L에서 원복**(RunOcrWorkspace.tsx pre-3J 복원). Preview는 `processedImageUrl ?? displayUrl` 유지가 정답.
- **3N(적용됨)**: debug-only harness. `deskew()`에 숫자 metadata(rawAngle/normalizedAngle/absAngle/applied/threshold) 추가 + `main.py`가 `extract_debug.preprocess`로 보존(정책/추출 불변). 7샘플 production fingerprint = tmp/full_unstructured_invoice_3n_sample_fingerprint_matrix.json.
- deskew 실제 적용 샘플: **4.pdf(2.62°), 6.pdf(1.01°), 7.pdf(1.64°)만**. 1.jpg는 0.197°<0.5°라 이미 미적용. 2.pdf orientation=90°(production 실측).
- **3O(적용됨)**: `PDF_ORIENTATION0_SMALL_ANGLE_DESKEW_SKIP` 정책을 main.py에 추가(policyVersion=3o_pdf_orientation0_small_angle_skip_policy). 조건: PDF+orientation==0+deskew원래적용+abs≤2.0 → `doc_deskewed=doc_img`(회전 전 채택). preprocess.py deskew 함수는 불변. 결과: 6·7.pdf finalApplied=false(over-apply 해소), 4.pdf(2.62°) 유지, 1.jpg(image)·2.pdf(orient90) 비대상. 행수/fallback 전부 불변(regressionPassed=true).
- **3O 부작용(GT 재검수 포인트)**: 회전 제거로 6·7.pdf OCR 셀 일부 변함 — 7.pdf row1 quantity ""→"1,000", 6.pdf "1"→"". 행수/shape는 동일.
- **3P(완료)**: UI smoke(route+수동가이드, Playwright 미설치) + 7.pdf GT resume = **READY**. 7.pdf: policyApplied=true/finalApplied=false(회전 해소), rows=1, quantity="1,000". 토글 재출현 없음. 회귀 OK(1.jpg/4.pdf/6.pdf).
- **7.pdf GT 수동 보정 항목(파서 한계, 회전 무관, 3O 회귀 아님 — 3N에서도 lotNo="")**: lotNo OCR ""→GT `0350623-231024-260811` 병합, expiryDate OCR "231024"→"" 제거. quantity/itemName은 OK.
- **3Q(완료)**: 7.pdf GT draft review = **FINAL_PROMOTION_READY**. clean review candidate(REVIEW_CANDIDATE_ONLY, 표준 8key) = tmp/full_unstructured_invoice_3q_7pdf_draft_gt_review_candidate.json. row0: itemName 클리마토플란정, lotNo 0350623-231024-260811, expiryDate "", quantity "1,000", 나머지 "". final GT 미저장.
- **3R(BLOCK)**: 7.pdf final GT write 시도 → **저장 위치 BLOCK**. 유일한 final-GT convention = `api/ground-truth` → `public/data/testsets/<folder>/ground_truth.json`(수정 금지). 서버측 per-sample data/gt standalone 파일 convention 없음. candidate는 READY(보존), final write 미실행(finalWriteExecuted=false).
- **3S(완료)**: GT 저장 정책 audit. 소비 convention=public/data ground_truth.json(document-scalar: fields+documentFields), invoice_statement GT에 7.pdf scalar entry 이미 존재(rowCount/firstRowPreview/totalQuantity). data/gt standalone convention/loader 부재. candidate(per-row tableRows)와 스키마 불일치. **권장=후보 B(standalone `data/gt/invoice_statement/7.pdf.json`)** — public fixture 보존+구조 무손실, 사용자 승인 필요.
- **3T(완료, 승인됨)**: 7.pdf final GT 를 **standalone `data/gt/invoice_statement/7.pdf.json`** 에 write 완료(schemaVersion invoice_free_gt_v1, status FINAL_GT, tableRows 1행 표준8key, lotNo 0350623-231024-260811, quantity 1,000). git `?? data/` 신규(gitignore 아님). public/data·ground_truth.json·manifest 미수정. **loader/manifest 미연결(의도)** — 이 standalone GT 는 아직 어떤 소비자도 사용 안 함.
- **다음=3U**: `STANDALONE-GT-LOADER-AND-MANIFEST-PRECHECK` — standalone GT 소비 경로 precheck(권장). 대안: `3U-3PDF-GT-DRAFT-REVIEW...`(샘플별 GT 닫기 우선 시).
- 서버 재시작 필요했음(기존 :9099가 --reload 미동작; 3O는 --reload로 자동 반영). [[feedback_server_restart]] 참조.
