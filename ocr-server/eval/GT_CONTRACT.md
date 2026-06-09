# GT_CONTRACT — LEARN-LOOP-INFRA (Phase 0 lock, 2026-06-09)

> The evaluation harness knows **only this contract**. It does not know the DB,
> the extractor internals, or the UI. Any GT file (rich draft today, thin ETL
> later) that satisfies this contract is consumable without harness changes.
>
> Derived from the real fixtures in
> `mysuit-ocr/public/data/testsets/invoice_study/GT/` (6 files) and verified
> against the live extractor key surface
> (`ocr-server/extractors/invoice_statement_free.py`) and API envelope
> (`main.py:3012` → `response["document_fields"]`).

## 1. Unit & identity

- `schemaVersion: draft-gt-document.v1`
- **1 image = 1 GT file.** Pairing key = `sourceFile` (e.g. `1.jpg`, `3.pdf`).
- Current set: `1.jpg, 3.pdf, 4.pdf, 5.pdf, 6.pdf, 7.pdf`. **`2.pdf` excluded**
  (temporary, tracked via manifest status — not a contract violation).

## 2. Document fields (scalar) — `normalizedResult.fields[]`

Each entry is an object; the harness flattens to `{labelEn: value}`.

```
field = { labelEn: <str>, value: <str>, ... }   # other keys are optional (§5)
```

### 2.1 Required, scored — common 12 (present in every sample)

```
supplierCompany  supplierBizNumber  supplierRepresentative  supplierAddress
buyerCompany     buyerBizNumber     buyerRepresentative     buyerAddress
issueDate        supplyAmount       taxAmount               cumulativeAmount
```

A common field MAY carry an empty `value` (e.g. `cumulativeAmount` is often
`""` / `not_reviewed`). Empty GT value → that field is **not scored** for that
sample (no penalty), but its presence as a key is required.

### 2.2 Per-sample, scored only when present — exactly ONE of:

```
totalAmount      # 1.jpg, 3.pdf, 4.pdf, 5.pdf, 6.pdf
totalQuantity    # 7.pdf
```

Observed invariant: **every sample has exactly 12 common + 1 per-sample = 13
fields.** Union over all samples = **14** distinct labelEn. The missing
per-sample field is **never penalized** (it is absent by design, not an error).

> Extractor surface note: `DOCUMENT_FIELD_KEYS` in `invoice_statement_free.py`
> is a superset (adds `subtotal, previousBalance, transactionAmount,
> cumulativeBalance, tableDetected, rowCount, ...`). Those are NOT in any GT and
> are NOT scored. The harness scores only the GT's per-sample required set.

## 3. Table rows — `normalizedResult.tableRows[]`

### 3.1 Value keys (compared, per-row)

```
rowIndex  itemName  spec  productCode  lotNo  expiryDate  quantity  unitPrice  amount
```

These exactly match the GT row value-keys and are produced by the extractor
(`productCode` is emitted via the extractor + `main.py:3069-3081` normalization;
note the extractor's `TABLE_ROW_KEYS` tuple lists `itemCode`, but the emitted
+ normalized row carries `productCode`, which is what GT uses).

`rowIndex` is the alignment key (1-based). A row value MAY be empty → not scored.

### 3.2 Excluded from comparison (GT review-meta, NOT extractor output)

```
rowType  amountOnly  missingFields  fieldStatus  reviewStatus
excludeReason  sourceRowMeta  tableExtraColumns
```

> `rowType` is a row classifier ("item"/...), not an OCR value. It appears in GT
> but in neither the §3.1 value set nor the original plan's exclude list; Phase 0
> decision: **treat as meta → exclude from value comparison.**

### 3.3 Per-sample row counts (verified)

```
1.jpg=28   3.pdf=1   4.pdf=1   5.pdf=6   6.pdf=6   7.pdf=1
```

(`3/4/7.pdf` are genuine single-item invoices, not truncation.)

## 4. Excluded rows — top-level `excludedRows[]`

Rows the GT author deliberately dropped. **Must NOT be counted as extractor
misses** (no false "missing row" penalty). Currently `[]` in all 6 files; the
code path exists but is unexercised until larger sets (Phase 6) / ETL (Phase 7).

## 5. Optional keys — rich-only, bonus / harmless if absent (thin GT passes)

```
bboxRefs   edited   confidence   fieldStatus   orientationGt
```

All 6 current fixtures are **rich** (carry `bboxRefs`). Thin GT (future ETL,
Phase 7) will omit these — the core comparison (value + row) must still pass.
These are never required and never penalized when missing.

## 6. API envelope (what the runner reads back)

```
resp["document_fields"]                      # snake_case envelope (main.py:3012)
  ├─ <camelCase scalar keys>                 # e.g. supplierCompany, issueDate
  ├─ tableRows: [ {<value keys>}, ... ]
  └─ tableMeta:
       └─ extractionSource: "free" | "<fallback>"   # main.py:3015 — record & split-tally
```

- Mixed casing is intentional: envelope is snake (`document_fields`), inner keys
  are camel (`supplierCompany`), table array is `tableRows`. Read exactly via
  `resp["document_fields"]["tableRows"]`.
- `tableMeta.extractionSource` distinguishes the `free` path (main.py:2958) from
  the `extract_invoice_statement_fields` fallback (main.py:3003). Metrics tally
  free vs fallback **separately**.

## 7. What the harness must NOT assume

- No DB knowledge (ETL absorbs the DB → emits contract-conformant GT).
- No write to `public/data` (read-only) or to operational OCR logic.
- PDF = page 0 only (current samples are 1-page); assert page count == 1 and
  flag multi-page rather than silently reading page 0.
