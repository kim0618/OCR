# RunAll Snapshot Diff Report

## 1. 입력 파일
- **before**: `test-before.json` (생성: 2026-05-16T10:00:00.000Z, testset: invoice_statement)
- **after**: `test-after.json` (생성: 2026-05-16T14:00:00.000Z, testset: invoice_statement)
- **diff 생성**: 2026-05-16T05:25:38.026Z

## 2. 전체 요약
| 항목 | before | after | delta |
|---|---:|---:|---:|
| totalSamples | 7 | 7 | 0 |
| samplesRun | 7 | 7 | 0 |
| improved | — | 2 | — |
| regressed | — | 0 | — |
| unchanged | — | 5 | — |

## 3. rowCount 집계 변화
| 상태 | before | after | delta |
|---|---:|---:|---:|
| exact ✓ | 6 | 7 | +1 |
| short ✓ | 1 | 0 | -1 |
| over | 0 | 0 | 0 |
| unknown | 0 | 0 | 0 |

## 4. 개선 샘플
| 파일 | 변화 항목 |
|---|---|
| 3.pdf | missing: 2 → 0 |
| 5.pdf | rowCount: short → exact |

## 6. documentType별 변화
| documentType | rowExact Δ | rowShort Δ | rowOver Δ | warn Δ | missing Δ합 | 판정 |
|---|---:|---:|---:|---:|---:|---|
| invoice_statement | +1 | -1 | 0 | -1 | -2 | ✓ 개선 |

## 7. missing field 변화
**invoice_statement**
| field | before | after | delta |
|---|---:|---:|---:|
| insuranceCode ✓ | 2 | 1 | -1 |
| spec ✓ | 1 | 0 | -1 |

## 8. warning 변화
**invoice_statement**
| warning | before | after | delta |
|---|---:|---:|---:|
| insuranceCode:ocr_source_missing ↓ | 2 | 1 | -1 |

## 9. sample별 상세 (변화 있는 샘플)
| 파일 | 판정 | rowCountStatus | actualRow | expected | missing Δ | warn Δ |
|---|---|---|---:|---:|---:|---:|
| 3.pdf | ✓ 개선 | exact → exact | 1 → 1 | 1 | -2 | -1 |
| 5.pdf | ✓ 개선 | short → exact | 5 → 6 | 6 | 0 | 0 |
