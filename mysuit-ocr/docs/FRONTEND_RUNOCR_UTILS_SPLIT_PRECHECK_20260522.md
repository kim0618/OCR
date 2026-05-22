# FRONTEND RUNOCR UTILS SPLIT PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `RunOcrWorkspace.tsx` 및 `src/components/runocr/ui/*` 수정 없음.
- utils 파일 생성 없음.
- import 수정/파일 이동/리팩토링 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_utils_split_precheck.py`
- `docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv`

## 4. 분석 범위
- 필수: `src/components/runocr/RunOcrWorkspace.tsx`
- 참고: `src/components/runocr/ui/*`, history/restore/autofill 관련 import 흐름, 최근 구조 리포트

## 5. RunOcrWorkspace 구조 요약
- path: `src/components/runocr/RunOcrWorkspace.tsx`
- lineCount: 1587
- sizeBytes: 68321
- type/interface count: 9
- state/ref/memo/effect count: 38
- handler count: 9

| section | start | end |
| --- | --- | --- |
| imports/types | 1 | 2 |
| state declarations | 3 | 110 |
| component start | 111 | 238 |
| template/preprocess effects | 239 | 389 |
| preprocess helpers | 390 | 848 |
| main OCR request | 849 | 862 |
| history/autofill mapping | 863 | 1171 |
| result sync effects | 1172 | 1211 |
| JSX return | 1212 | 1258 |
| viewer/result props | 1259 | 1587 |

## 6. 상태 관리 책임 분류
| line | kind | name | responsibility | moveCandidate | usageLines |
| --- | --- | --- | --- | --- | --- |
| 114 | useRef | fileInputRef | file/preprocess state | utils/useRunOcrState.ts candidate | [114, 383, 1312, 1408] |
| 115 | useRef | uploadStartRef | file/preprocess state | utils/useRunOcrState.ts candidate | [115, 315, 420] |
| 117 | useState | activeTemplateId | template/model selection state | RunOcrWorkspace 유지 또는 useRunOcrState.ts | [117, 827, 832, 837, 1121, 1125, 1337, 1385, 1545] |
| 118 | useState | templates | template/model selection state | RunOcrWorkspace 유지 또는 useRunOcrState.ts | [118, 239, 832, 1125, 1332, 1333, 1390] |
| 119 | useState | selectedModelId | template/model selection state | RunOcrWorkspace 유지 또는 useRunOcrState.ts | [119, 841, 1443] |
| 120 | useState | runOcrTemplateMode | template/model selection state | RunOcrWorkspace 유지 또는 useRunOcrState.ts | [120] |
| 121 | useState | cardTooltip | template/model selection state | RunOcrWorkspace 유지 또는 useRunOcrState.ts | [121, 1560, 1565, 1567, 1579] |
| 124 | useState | selectedFile | file/preprocess state | utils/useRunOcrState.ts candidate | [124, 302, 311, 312, 313, 324, 357, 380, 826, 836, 896, 1051] |
| 125 | useState | previewUrl | file/preprocess state | utils/useRunOcrState.ts candidate | [125, 1101, 1113, 1119, 1120, 1409] |
| 126 | useState | renderedUrl | file/preprocess state | utils/useRunOcrState.ts candidate | [126, 1101, 1113, 1119, 1120] |
| 127 | useState | uploadDuration | file/preprocess state | utils/useRunOcrState.ts candidate | [127, 1467] |
| 128 | useState | preprocessResult | file/preprocess state | utils/useRunOcrState.ts candidate | [128, 1478, 1482, 1484, 1488, 1490, 1495, 1497, 1500, 1502, 1505, 1507] |
| 129 | useState | isPreprocessing | file/preprocess state | utils/useRunOcrState.ts candidate | [129, 1121, 1474] |
| 132 | useState | ocrResult | OCR result/job state | utils/useRunOcr.ts candidate | [132, 1128, 1129, 1137, 1152, 1211, 1244, 1260] |
| 133 | useState | isOcrRunning | OCR result/job state | utils/useRunOcr.ts candidate | [133, 1121, 1254, 1285, 1421, 1543, 1547] |
| 134 | useState | selectedFieldIndex | result panel UI state | RunOcrWorkspace 유지 또는 ui local state candidate | [134, 198, 205, 209, 216, 1140, 1245, 1278] |
| 135 | useState | processedImageUrl | other state | review | [135, 1099, 1113, 1124, 1266, 1267, 1295, 1296] |
| 136 | useState | corners | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [136, 390, 391, 393, 394, 395, 847] |
| 137 | useState | showCornerAdjust | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [137] |
| 140 | useRef | canvasImgRef | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [140, 1218] |
| 141 | useState | canvasRegions | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [141, 210, 216, 1143, 1220, 1287] |
| 142 | useState | canvasSelectedId | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [142, 198, 200, 202, 206, 212, 215, 216, 1146, 1163, 1164, 1222] |
| 143 | useState | canvasDrawMode | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [143, 1224, 1235, 1283] |
| 144 | useState | canvasZoom | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [144, 1226] |
| 145 | useState | rowTemplateTargetId | template/model selection state | RunOcrWorkspace 유지 또는 useRunOcrState.ts | [145, 1227] |
| 146 | useState | colGuideTargetId | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [146, 1229] |
| 147 | useState | canvasLoaded | viewer/canvas state | RunOcrWorkspace 유지; UI split later | [147, 1096, 1216, 1219] |
| 148 | useState | resultTab | OCR result/job state | utils/useRunOcr.ts candidate | [148, 1148, 1155, 1167, 1216, 1247] |
| 151 | useState | currentJobId | OCR result/job state | utils/useRunOcr.ts candidate | [151, 1175, 1192, 1288] |
| 152 | useState | currentCreatedAt | OCR result/job state | utils/useRunOcr.ts candidate | [152, 1289] |
| 156 | useState | initialOutputFields | OCR result/job state | utils/useRunOcr.ts candidate | [156, 1172, 1173, 1175, 1176] |
| 272 | useMemo | hintSections | derived state | keep until dependencies are reduced | [272, 1524] |
| 199 | useEffect | useEffect@199 | side effect | review after request/state split | [199] |
| 204 | useEffect | useEffect@204 | side effect | review after request/state split | [204] |
| 229 | useEffect | useEffect@229 | side effect | review after request/state split | [229] |
| 301 | useEffect | useEffect@301 | side effect | review after request/state split | [301] |
| 1097 | useEffect | useEffect@1097 | side effect | review after request/state split | [1097] |
| 1127 | useEffect | useEffect@1127 | side effect | review after request/state split | [1127] |

## 7. OCR 요청/FormData 책임 분석
| line | keywords | snippet |
| --- | --- | --- |
| 33 | ["regions"] | regions?: Region[]; |
| 37 | ["documentType"] | documentType?: string; |
| 124 | ["selectedFile"] | const [selectedFile, setSelectedFile] = useState<File \| null>(null); |
| 170 | ["template_id"] | id: String(item?.template_id ?? ""), |
| 173 | ["regions"] | regions: Array.isArray(item?.template_json?.regions) ? item.template_json.regions : [], |
| 175 | ["documentType"] | // T-9-fix: include documentType from template metadata for routing |
| 176 | ["documentType"] | documentType: String(item?.template_json?.documentType ?? ""), |
| 239 | ["fetch("] | const res = await fetch("/templates"); |
| 248 | ["template_id"] | id: t.template_id, |
| 250 | ["regions"] | regions: Array.isArray(t.template_json?.regions) ? t.template_json.regions : t.regions, |
| 251 | ["documentType"] | // T-9-fix: include documentType from template metadata |
| 252 | ["documentType"] | documentType: String(t.template_json?.documentType ?? ""), |
| 302 | ["selectedFile"] | if (!selectedFile) { |
| 311 | ["selectedFile"] | selectedFile.type.startsWith("image/") && !isTiff(selectedFile); |
| 312 | ["selectedFile"] | const isPdf = selectedFile.type === "application/pdf"; |
| 313 | ["selectedFile"] | const isTiffFile = isTiff(selectedFile); |
| 324 | ["selectedFile"] | const url = URL.createObjectURL(selectedFile); |
| 338 | ["regions"] | // so that canvas regions and overlay bboxes align with the rendered image. |
| 357 | ["selectedFile"] | const arrayBuffer = await selectedFile.arrayBuffer(); |
| 380 | ["selectedFile"] | }, [selectedFile]); |
| 388 | ["new FormData"] | const formData = new FormData(); |
| 389 | ["formData.append"] | formData.append("file", file); |
| 390 | ["fetch("] | const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL \|\| ""}/preprocess/corners`, { method: "POST", body: formData }); |
| 402 | ["new FormData"] | const formData = new FormData(); |
| 403 | ["formData.append"] | formData.append("file", file); |
| 404 | ["fetch("] | const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL \|\| ""}/preprocess/info`, { |
| 441 | ["regions"] | // Enrich raw.fields with ko/en labels from template regions so the |
| 443 | ["regions"] | const regions: any[] = (template as any).regions ?? []; |
| 445 | ["regions"] | const region = regions[i] ?? {}; |
| 798 | ["regions"] | if (isRunOcr && template?.regions?.length) { |
| 799 | ["regions"] | return template.regions.map((region, index) => ({ |
| 826 | ["selectedFile"] | if (!selectedFile) return; |
| 835 | ["new FormData"] | const formData = new FormData(); |
| 836 | ["formData.append", "selectedFile"] | formData.append("file", selectedFile); |
| 837 | ["formData.append", "template_id"] | if (activeTemplateId) formData.append("template_id", activeTemplateId); |
| 838 | ["regions"] | if (useRegionTemplate && activeTemplate?.regions?.length) { |
| 839 | ["formData.append", "regions"] | formData.append("regions", JSON.stringify(activeTemplate.regions)); |
| 841 | ["formData.append", "model_id"] | if (isRunOcr) formData.append("model_id", selectedModelId); |
| 842 | ["documentType"] | // T-9-fix: pass documentType from template metadata to backend for routing priority |
| 843 | ["documentType"] | if (activeTemplate?.documentType) { |
| 844 | ["formData.append", "documentType"] | formData.append("documentType", activeTemplate.documentType); |
| 847 | ["formData.append"] | // if (corners.length === 4) formData.append("corners", JSON.stringify(corners)); |
| 849 | ["/ocr/extract", "/api/ocr-extract"] | const ocrEndpoint = backendBase ? `${backendBase}/ocr/extract` : "/api/ocr-extract"; |
| 850 | ["fetch("] | const res = await fetch(ocrEndpoint, { |
| 896 | ["selectedFile"] | fileName: selectedFile.name, |
| 976 | ["regions"] | (activeTemplate.regions?.length ?? 0) > 0; |
| 991 | ["regions"] | ? String((activeTemplate?.regions?.[idx] as Record<string, unknown> \| undefined)?.koField ?? "").trim() |
| 1051 | ["selectedFile"] | file_name: selectedFile.name, |
| 1070 | ["documentType"] | documentType: activeTemplate?.documentType \|\| undefined, |
| 1082 | ["selectedFile"] | file_name: selectedFile.name, |
| 1100 | ["selectedFile"] | ?? ((selectedFile?.type === "application/pdf" \|\| (selectedFile && isTiff(selectedFile))) |
| 1107 | ["selectedFile"] | fileName: selectedFile?.name ?? "", |
| 1113 | ["selectedFile"] | }, [previewUrl, renderedUrl, selectedFile, processedImageUrl]); |
| 1115 | ["selectedFile"] | const needsRender = selectedFile |
| 1116 | ["selectedFile"] | ? selectedFile.type === "application/pdf" \|\| isTiff(selectedFile) |
| 1121 | ["selectedFile"] | const canRunOcr = !!selectedFile && !isPreprocessing && !isOcrRunning && (!isRunOcr \|\| !!activeTemplateId); |
| 1211 | ["selectedFile"] | if (ocrResult && selectedFile) { |
| 1220 | ["regions"] | regions={canvasRegions} |
| 1263 | ["selectedFile"] | if (!selectedFile) return []; |
| 1264 | ["new FormData"] | const formData = new FormData(); |
| 1267 | ["fetch("] | const blob = await fetch(processedImageUrl).then((r) => r.blob()); |
| 1268 | ["formData.append"] | formData.append("file", blob, "processed.jpg"); |
| 1270 | ["formData.append", "selectedFile"] | formData.append("file", selectedFile); |
| 1272 | ["regions"] | const url = `/ocr/revalidate?regions=${encodeURIComponent(JSON.stringify(targets))}`; |
| 1273 | ["fetch("] | const res = await fetch(url, { method: "POST", body: formData }); |
| 1281 | ["selectedFile"] | fileName={selectedFile?.name ?? ""} |
| 1293 | ["selectedFile"] | if (!selectedFile) return []; |
| 1294 | ["new FormData"] | const formData = new FormData(); |
| 1296 | ["fetch("] | const blob = await fetch(processedImageUrl).then((r) => r.blob()); |
| 1297 | ["formData.append"] | formData.append("file", blob, "processed.jpg"); |
| 1299 | ["formData.append", "selectedFile"] | formData.append("file", selectedFile); |
| 1301 | ["regions"] | const url = `/ocr/revalidate?regions=${encodeURIComponent(JSON.stringify(targets))}`; |
| 1302 | ["fetch("] | const res = await fetch(url, { method: "POST", body: formData }); |
| 1409 | ["selectedFile"] | hasFile={!!(previewUrl && selectedFile)} |
| 1411 | ["selectedFile"] | {selectedFile && ( |
| 1416 | ["selectedFile"] | {isTiff(selectedFile) ? "TIFF" : "PDF"} 렌더링 중... |
| 1424 | ["selectedFile"] | <div className="uw-filename-chip" title={selectedFile.name}> |
| 1425 | ["selectedFile"] | {selectedFile.name} |
| 1453 | ["selectedFile"] | {selectedFile ? ( |
| 1459 | ["selectedFile"] | <span className="uw-file-value" title={selectedFile.name}>{selectedFile.name}</span> |
| 1463 | ["selectedFile"] | <span className="uw-file-value">{formatFileType(selectedFile)}</span> |
| 1545 | ["selectedFile"] | title={isRunOcr && selectedFile && !activeTemplateId ? "상단 템플릿을 선택해야 실행할 수 있습니다." : undefined} |

판정:
- main OCR request 영역에는 `new FormData`, `formData.append`, endpoint 선택, `fetch`, loading/error 처리가 같이 있다.
- `buildOcrFormData`는 입력과 출력이 가장 명확하다.
- `runOcrRequest`는 endpoint/fetch/error handling을 함께 묶을 수 있지만 네트워크 behavior라 Phase 2A에서 같이 할지 신중해야 한다.

## 8. OCR 응답 mapping 책임 분석
| line | keywords | snippet |
| --- | --- | --- |
| 132 | ["setOcrResult"] | const [ocrResult, setOcrResult] = useState<OcrResult \| null>(null); |
| 151 | ["setCurrentJobId"] | const [currentJobId, setCurrentJobId] = useState<string \| null>(null); |
| 152 | ["setCurrentCreatedAt"] | const [currentCreatedAt, setCurrentCreatedAt] = useState<string \| null>(null); |
| 156 | ["initialOutputFields"] | const [initialOutputFields, setInitialOutputFields] = useState<HistoryOutputField[] \| null>(null); |
| 422 | ["setOcrResult"] | setOcrResult(null); |
| 777 | ["runResult"] | function buildResultRegions(runResult: OcrResult, template?: TemplateItem): Region[] { |
| 778 | ["runResult"] | const ocrFieldRegions = (runResult.fields ?? []) |
| 802 | ["runResult"] | name: region.name \|\| runResult.fields?.[index]?.name \|\| `field_${index + 1}`, |
| 803 | ["runResult"] | fieldType: (region.fieldType \|\| runResult.fields?.[index]?.field_type \|\| "field") as FieldType, |
| 807 | ["runResult"] | return (runResult.fields ?? []) |
| 857 | ["runResult"] | const runResult = isRunOcr ? buildRunOcrResult(json, activeTemplate) : json; |
| 858 | ["runResult"] | runResult.raw_ocr_fields = rawOcrFields; |
| 859 | ["runResult"] | const originalRunFields: OcrFieldResult[] = ((runResult.fields ?? []) as OcrFieldResult[]).map((field) => ({ |
| 875 | ["runResult"] | runResult?.full_text, |
| 882 | ["runResult"] | runResult.fields = originalRunFields; |
| 913 | ["runResult"] | runResult.fields = applyAutofillToOutputFields({ |
| 917 | ["runResult"] | const resultFields = ((runResult.fields ?? []) as OcrFieldResult[]); |
| 949 | ["runResult"] | runResult.fields = originalRunFields; |
| 959 | ["runResult"] | runResult.fields = attachSourceBboxes((runResult.fields ?? []) as OcrFieldResult[], rawOcrFields); |
| 960 | ["runResult"] | runResult.autofill_summary = autofillSummary; |
| 961 | ["setOcrResult", "runResult"] | setOcrResult(runResult); |
| 962 | ["runResult"] | if (runResult.processed_image) { |
| 963 | ["runResult"] | setProcessedImageUrl(runResult.processed_image); |
| 965 | ["runResult"] | const ocrRegions = buildResultRegions(runResult, activeTemplate); |
| 972 | ["runResult"] | // 출력 필드 표는 runResult.fields(receipt_fields/template 매핑) 를 사용 → 명확한 분리. |
| 1003 | ["runResult"] | // 출력 필드 표 데이터 — 정제된 결과(runResult.fields = template/receipt_fields 매핑) 기반. |
| 1005 | ["runResult"] | const structuredFields: OcrFieldResult[] = (runResult.fields ?? []) as OcrFieldResult[]; |
| 1030 | ["runResult"] | // runResult.fields 는 이미 region.koField/enField 로 enrich 되어 있으므로 |
| 1056 | ["runResult"] | image_url: runResult.processed_image, |
| 1058 | ["runResult"] | processed_image_url: runResult.processed_image ?? null, |
| 1059 | ["runResult"] | original_image_url: runResult.original_image ?? null, |
| 1062 | ["output_fields"] | output_fields: outputFieldsForHistory, |
| 1067 | ["document_fields"] | const rawDocFields = (json as Record<string, unknown>)?.document_fields as |
| 1076 | ["setCurrentJobId"] | setCurrentJobId(successRecord.job_id); |
| 1077 | ["setCurrentCreatedAt"] | setCurrentCreatedAt(successRecord.created_at); |
| 1087 | ["setCurrentJobId"] | setCurrentJobId(failRecord.job_id); |
| 1088 | ["setCurrentCreatedAt"] | setCurrentCreatedAt(failRecord.created_at); |
| 1171 | ["output_fields"] | // Custom 탭 onBlur 자동저장 — 사용자 편집을 history.output_fields.modified 에 반영. |
| 1172 | ["initialOutputFields"] | // immutable 메타(no/en/ko/original/applied/autofillAction/suggestions)는 initialOutputFields 에서 보존. |
| 1173 | ["initialOutputFields"] | // initialOutputFields 가 null 이면 success 레코드가 아니므로 자동저장을 건너뛴다. |
| 1175 | ["initialOutputFields"] | if (!currentJobId \|\| !initialOutputFields) return; |
| 1176 | ["initialOutputFields"] | const initial = initialOutputFields; |
| 1192 | ["output_fields"] | updateHistoryRun(currentJobId, { output_fields: merged }); |
| 1197 | ["setOcrResult"] | setOcrResult(null); |
| 1199 | ["setCurrentJobId"] | setCurrentJobId(null); |
| 1200 | ["setCurrentCreatedAt"] | setCurrentCreatedAt(null); |

판정:
- OCR response 이후 `autofill`, `history`, `initialOutputFields`, `setOcrResult`가 얽혀 있다.
- `mapOcrResponse`는 유효 후보지만 Phase 2A에서는 범위가 크다.

## 9. History/Restore 연동 분석
| line | keywords | snippet |
| --- | --- | --- |
| 12 | ["appendHistoryRun", "updateHistoryRun", "syncHistoryIndexAndDetailOnCreate"] | import { appendHistoryRun, updateHistoryRun, syncHistoryIndexAndDetailOnCreate, type HistoryDetailDocumentFields, type HistoryOcrField, type HistoryOutputField } from "@/lib/historyStore"; |
| 17 | ["AutofillSuggestion"] | buildAutofillSuggestionsFromCandidates, |
| 19 | ["collectInternalAutofillCandidates"] | collectInternalAutofillCandidates, |
| 23 | ["suggestions"] | suggestionsForHistoryField, |
| 25 | ["AutofillSuggestion"] | type AutofillSuggestion, |
| 26 | ["autofill"] | } from "@/lib/autofillEngine"; |
| 153 | ["appendHistoryRun", "autofill", "suggestions"] | // appendHistoryRun 시점의 immutable 메타(no/en/ko/original/applied/autofillAction/suggestions) |
| 727 | ["autofill"] | if (field.autofillAction === "corrected" \|\| field.autofillAction === "filled") return "restored"; |
| 743 | ["autofill"] | const lookupValue = field.autofillAction === "corrected" |
| 746 | ["autofill"] | if (field.autofillAction === "filled" && !field.original) { |
| 863 | ["autofill", "AutofillSuggestion"] | let autofillSuggestions: AutofillSuggestion[] = []; |
| 864 | ["autofill"] | let autofillSummary: AutofillRunSummary = { |
| 883 | ["autofill"] | autofillSummary = { |
| 892 | ["AutofillSuggestion"] | const internalSuggestions = buildAutofillSuggestionsFromCandidates({ |
| 894 | ["collectInternalAutofillCandidates"] | candidates: collectInternalAutofillCandidates(businessNumber), |
| 902 | ["AutofillSuggestion"] | const businessNumberSuggestion: AutofillSuggestion[] = hasBusinessNumberField |
| 912 | ["autofill"] | autofillSuggestions = [...businessNumberSuggestion, ...internalSuggestions]; |
| 915 | ["autofill", "suggestions"] | suggestions: autofillSuggestions, |
| 918 | ["autofill"] | const confirmedCount = resultFields.filter((field) => field.autofillAction === "confirmed").length; |
| 919 | ["autofill"] | const correctedCount = resultFields.filter((field) => field.autofillAction === "corrected").length; |
| 920 | ["autofill"] | const filledCount = resultFields.filter((field) => field.autofillAction === "filled").length; |
| 924 | ["autofill"] | return autofillSuggestions.some((suggestion) => normalizeAutofillFieldKey(suggestion.field) === key && canAutoApplySuggestion(suggestion)); |
| 927 | ["autofill"] | autofillSuggestions.length === 0 ? "no_candidates" : |
| 932 | ["autofill"] | autofillSummary = { |
| 935 | ["autofill"] | candidateCount: autofillSuggestions.length, |
| 948 | ["autofill"] | console.warn("[autofill] skipped", err); |
| 950 | ["autofill"] | autofillSummary = { |
| 960 | ["autofill"] | runResult.autofill_summary = autofillSummary; |
| 1011 | ["suggestions"] | const suggestions = suggestionsForHistoryField( |
| 1013 | ["autofill"] | autofillSuggestions, |
| 1024 | ["autofill"] | autofillAction: ocrF?.autofillAction, |
| 1025 | ["suggestions"] | suggestions: suggestions.length > 0 ? suggestions : undefined, |
| 1036 | ["autofill", "suggestions"] | const suggestions = suggestionsForHistoryField({ en, ko }, autofillSuggestions); |
| 1046 | ["autofill"] | autofillAction: f.autofillAction, |
| 1047 | ["suggestions"] | suggestions: suggestions.length > 0 ? suggestions : undefined, |
| 1050 | ["appendHistoryRun"] | const successRecord = appendHistoryRun({ |
| 1063 | ["autofill"] | autofill_summary: autofillSummary, |
| 1069 | ["syncHistoryIndexAndDetailOnCreate"] | syncHistoryIndexAndDetailOnCreate(successRecord, { |
| 1081 | ["appendHistoryRun"] | const failRecord = appendHistoryRun({ |
| 1172 | ["autofill", "suggestions"] | // immutable 메타(no/en/ko/original/applied/autofillAction/suggestions)는 initialOutputFields 에서 보존. |
| 1188 | ["autofill"] | autofillAction: field.autofillAction ?? base?.autofillAction, |
| 1189 | ["suggestions"] | suggestions: base?.suggestions, |
| 1192 | ["updateHistoryRun"] | updateHistoryRun(currentJobId, { output_fields: merged }); |

판정:
- `appendHistoryRun`, `updateHistoryRun`, `syncHistoryIndexAndDetailOnCreate`, autofill summary/suggestions 흐름이 workspace 내부에 있다.
- Phase 2A에서는 history/restore adapter를 건드리지 않는 것이 안전하다.

## 10. UI 조립 책임 분석
| line | keywords | snippet |
| --- | --- | --- |
| 89 | ["return ("] | return ( |
| 376 | ["return ("] | return () => { |
| 718 | ["return ("] | return ( |
| 807 | ["return ("] | return (runResult.fields ?? []) |
| 1212 | ["return ("] | return ( |
| 1242 | ["<OcrDocViewer"] | <OcrDocViewer |
| 1259 | ["<OcrResultPanel"] | <OcrResultPanel |
| 1261 | ["onRerun"] | onRerun={runOcr} |
| 1262 | ["onRevalidate"] | onRevalidate={async (targets) => { |
| 1292 | ["onPartialOcr"] | onPartialOcr={async (targets) => { |
| 1325 | ["return ("] | return ( |

판정:
- `OcrDocViewer`, `OcrResultPanel`, `CornerAdjust` props 전달이 workspace return 근처에 몰려 있다.
- UI split은 props 폭발 위험이 있으므로 request/formdata 분리 이후가 적절하다.

## 11. 분리 후보 우선순위
| name | targetPath | recommendation | inputs | outputs | risk | reason | validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| buildOcrFormData | src/components/runocr/utils/buildOcrFormData.ts | DO_FIRST | ["selectedFile", "activeTemplateId", "activeTemplate", "isRunOcr", "selectedModelId"] | ["FormData"] | LOW-MEDIUM | Pure-ish boundary with concrete output; easiest to diff by FormData keys. | ["typecheck", "build", "FormData key before/after diff candidate", "/runocr smoke"] |
| runOcrRequest | src/components/runocr/utils/runOcrRequest.ts | DO_FIRST_WITH_FORMDATA_OR_NEXT | ["FormData", "backendBase", "AbortSignal?"] | ["raw OCR response JSON"] | MEDIUM | Endpoint/fetch/error status handling is cohesive, but touches network behavior. | ["typecheck", "build", "manual API smoke", "/runocr smoke"] |
| mapOcrResponse | src/components/runocr/utils/mapOcrResponse.ts | DO_LATER | ["raw response", "selectedFile metadata", "autofill suggestions?", "template metadata?"] | ["OcrResult", "history snapshot inputs"] | HIGH | Currently intertwined with autofill/history snapshot and state updates. | ["fixture runner", "typecheck", "build", "manual smoke"] |
| useRunOcrState | src/components/runocr/utils/useRunOcrState.ts | DO_LATER | ["initial options"] | ["state values and setters"] | MEDIUM-HIGH | May reduce line count but risks creating a setter bucket without clarifying flow. | ["typecheck", "build", "/runocr smoke"] |
| useRunOcr | src/components/runocr/utils/useRunOcr.ts | DEFER | ["request config", "template state", "history/restore adapters"] | ["run handlers", "result state", "loading/error state"] | HIGH | Should happen after request/mapping/history seams are clearer. | ["full runners", "typecheck", "build", "manual smoke"] |
| RunOcrControls | src/components/runocr/ui/RunOcrControls.tsx | DO_LATER | ["file/template/model/preprocess props", "handlers"] | ["control JSX"] | MEDIUM-HIGH | Props are still broad; safer after request/state boundaries shrink. | ["typecheck", "build", "visual smoke"] |
| RunOcrResultLayout | src/components/runocr/ui/RunOcrResultLayout.tsx | DO_LATER | ["viewer props", "result panel props", "layout state"] | ["viewer/result layout JSX"] | HIGH | Would move many props and can obscure behavior if done before request split. | ["typecheck", "build", "visual smoke"] |
| history adapter | src/components/runocr/utils/buildRunOcrHistorySnapshot.ts | DEFER | ["OcrResult", "autofill summary", "file/template metadata"] | ["appendHistoryRun payload"] | HIGH | History snapshot preserves immutable autofill metadata; avoid in Phase 2A. | ["history smoke", "typecheck", "build"] |
| restore/autofill adapter | src/components/runocr/utils/runAutofillForOcrResult.ts | DEFER | ["document fields", "profile data"] | ["suggestions", "summary", "patched fields"] | HIGH | Cross-feature restore logic; needs dedicated adapter precheck. | ["restore smoke", "typecheck", "build"] |

## 12. Phase 2A 추천 범위
권장: **A 또는 작은 B**.
- 가장 안전한 1차: `buildOcrFormData.ts`만 분리.
- 허용 가능한 확장: `buildOcrFormData.ts` + `runOcrRequest.ts`.
- 제외 권장: `mapOcrResponse`, `useRunOcr`, UI component split, history/restore adapter.

## 13. Phase 2A 예상 파일
- `src/components/runocr/utils/buildOcrFormData.ts`
- 선택: `src/components/runocr/utils/runOcrRequest.ts`

## 14. Phase 2A 검증 전략
| validation |
| --- |
| npm run typecheck |
| npm run build |
| node tmp/check_table_view_model_v1_fixtures_js.mjs |
| node tmp/check_clean_json_v1_fixtures_js.mjs |
| python tmp/codex_markdown_contract_fixture_lock.py --check ... |
| FormData key before/after diff script candidate |
| /runocr manual smoke with invoice upload |

## 15. dirty 상태
현재 dirty 상태는 기록만 했고 되돌리지 않았다.

| git status --short |
| --- |
|  M src/app/runocr/page.tsx |
| RM src/components/upload/UploadWorkspace.tsx -> src/components/runocr/RunOcrWorkspace.tsx |
| R  src/components/upload/CornerAdjust.tsx -> src/components/runocr/ui/CornerAdjust.tsx |
| R  src/components/upload/OcrDocViewer.tsx -> src/components/runocr/ui/OcrDocViewer.tsx |
| RM src/components/upload/OcrResultPanel.tsx -> src/components/runocr/ui/OcrResultPanel.tsx |
|  M src/lib/invoiceTableDisplay.ts |
|  M ../ocr-server/data/review_log.jsonl |
|  M ../ocr-server/requirements.txt |
| ?? docs/CLEAN_JSON_CONTRACT_20260521.json |
| ?? docs/CLEAN_JSON_CONTRACT_20260521.md |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| ?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json |
| ?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json |
| ?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md |
| ?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md |
| ?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md |
| ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json |
| ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md |
| ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.json |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.md |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md |
| ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json |
| ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md |
| ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv |
| ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md |
| ?? docs/MARKDOWN_V1_CONTRACT_20260521.json |
| ?? docs/MARKDOWN_V1_CONTRACT_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md |
| ?? src/lib/cleanJsonBuilder.ts |
| ?? src/lib/markdownReportBuilder.ts |
| ?? src/lib/ocrResultFormatters.ts |
| ?? src/lib/structuredTableViewModel.ts |
| ?? tmp/ |
| ?? ../ocr-server/requirements-aws.txt |

## 16. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 1.962 | False |
| npm.cmd run build | PASS | 0 | 15.67 | True |

## 17. 다음 작업 제안
- `CODEX_FRONTEND_RUNOCR_UTILS_SPLIT_2A_FORMDATA_ONLY`로 `buildOcrFormData.ts`만 먼저 분리하는 것을 추천한다.
- 더 공격적으로 가도 `runOcrRequest.ts`까지만 포함하고, mapping/history/UI는 다음 phase로 둔다.
