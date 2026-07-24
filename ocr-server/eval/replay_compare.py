"""replay_compare — re-score a parser edit LOCALLY, no re-OCR, no GPU, no training.

The missing link in the local loop. Pieces that already existed:
  - replay_free.replay_one : run the (edited) free parser on a frozen OCR snapshot
  - compare_fields / compare_table / buckets : the SAME scorer the AWS run uses

This wires them: for each snapshot in a run, replay the parser on it, score the
output against GT, and write a fresh per-sample comparison — into a SIDECAR dir
(default `replay_compare/`) so the original `compare/` (and the checker) are
untouched. Then `parser_drop_classify.py --compare-dir replay_compare` reads it.

So the loop closes WITHOUT AWS:
    edit parser  ->  python eval/replay_compare.py
                 ->  python eval/parser_drop_classify.py --compare-dir replay_compare
                 ->  see which class shrank  ->  edit again

Faithful dispatch: this reproduces the SERVER's real free->gate->fallback choice
(main.py ~3289-3419), not just the free path — because the fallback extractor
(extract_invoice_statement_fields) also consumes only the snapshot's inputs
(ocr_lines_raw + context's tableExpectedColumns/tableBounds/columnGuides). So all
24 samples replay as production would, and each is tagged path=free|fallback.
The one thing NOT replayed is FREE_HIRES_TABLE_REOCR (needs re-OCR; default OFF).
Faithfulness vs the recorded run is reported per sample (FAITHFUL = unchanged).

    ../.venv/Scripts/python.exe eval/replay_compare.py
    ../.venv/Scripts/python.exe eval/replay_compare.py --ts 053_20260617_142725/study
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
from build_manifest import build_manifest  # noqa: E402
from compare_fields import compare_fields  # noqa: E402
from compare_table import compare_table  # noqa: E402
from buckets import tag_sample  # noqa: E402
from gt_loader import load_gt, load_gt_aggregate  # noqa: E402
from replay_free import _deserialize_lines, _recorded_df, _canon  # noqa: E402
import learndata_apply as LDA  # noqa: E402

# learndata itemCode 측정 컬럼: 파일 있으면 로드 → replay 때 itemCode 옆에 나란히 채점.
#  A=held-out(9,001 제외, 비순환 효과=측정1) · B=full(9,001 포함, 순환 상한 참고)
_LEARN_SPECS = [
    ("itemCodeLearnA", os.path.join(HERE, "data/invoice_war/learndata_heldout.json")),
    ("itemCodeLearnB", os.path.join(HERE, "data/invoice_war/learndata_full.json")),
]

# server post-step + free-result gate + fallback extractor — all live in extractors
# (no main.py import => no OCR model load). Mirrors main.py ~3320-3419 dispatch.
from extractors.invoice_statement_free import (  # noqa: E402
    extract_invoice_statement_free,
    sanitize_document_scalar_fields as _sanitize,
    _is_valid_invoice_statement_free_result as _free_ok,
    fill_pharma_columns as _fill_pharma,
    fill_scalar_defaults as _fill_scalars,
    drop_boilerplate_table_rows as _drop_boiler,
    append_missing_ha_rows as _append_ha,
    salvage_blob_amount as _salvage_blob_amount,
    split_merged_item_name as _split_merged_item_name,
    recover_shifted_item_name as _recover_shifted_item_name,
    adopt_missing_item_names as _adopt_item_names,
    synthesize_missing_rows as _synth_rows,
    recover_unitprice_amount_columns as _recover_upa,
    fill_arith_empty_amount as _fill_arith_amount,
    fill_arith_empty_quantity as _fill_arith_qty,
    fix_swapped_qty_unitprice as _fix_swap_qu,
    fix_totals_arithmetic as _fix_totals,
    adopt_band_names_master_gated as _adopt_band_names,
    fill_spec_from_item_name as _fill_spec_from_name,
    reconstruct_numeric_columns as _geo_recon,
    refine_supplier_bizno as _refine_sup_bizno,
    refine_buyer_bizno as _refine_buy_bizno,
)
from extractors.invoice_statement import (  # noqa: E402
    extract_invoice_statement_fields,
    recover_postjoin_blank_amounts as _recover_postjoin_amounts,
    recover_postjoin_same_row_amounts as _recover_same_row_amounts,
)
from extractors.master_match import fill_master_match as _fill_master  # noqa: E402
from extractors.master_match import fill_insurance_from_master as _fill_insurance  # noqa: E402
from extractors.master_match import fill_party_match as _fill_party  # noqa: E402
from extractors.master_match import (  # noqa: E402
    strip_trailing_item_classification as _strip_item_classification,
)
from extractors.master_match import (  # noqa: E402
    strip_leading_item_code as _strip_leading_item_code,
)
from extractors.master_match import (  # noqa: E402
    strip_trailing_item_page_fraction as _strip_item_page_fraction,
)

# ②G4 마스터 매칭 포함 여부. False(--no-master-match)로 돌리면 Rule 단계(매칭 전) 사이드카가
# 나온다 — baseline_matrix가 Rule=replay_compare_rule / Master=replay_compare로 단계 분리.
MASTER_MATCH = True
# 금액P1 열복구 적용 여부 — 분석 하네스 전용 토글. 프로덕션(main.py)에서는 항상 켜져
# 있고, 이 플래그는 base(패치 전) 사이드카를 같은 코드로 재현해 P1 효과만 격리하려는
# 측정용이다(--skip-upa → replay_compare_base). 제품 기능 게이트가 아님.
APPLY_UPA = True


def _load_recorded_run_scope(run_dir: str) -> list[str] | None:
    """Return the exact source-file scope recorded by the historical live run.

    A run's snapshots directory may contain files left by an older invocation,
    while the current manifest may have changed since the run was created.
    ``run_meta.ran`` is therefore the only stable replay scope for historical
    runs. Older runs without this metadata retain the legacy snapshot behavior.
    """
    path = os.path.join(run_dir, "run_meta.json")
    try:
        meta = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    ran = meta.get("ran")
    if not isinstance(ran, list) or not all(isinstance(src, str) and src for src in ran):
        return None
    # Preserve the recorded order while rejecting accidental duplicates.
    return list(dict.fromkeys(ran))


def _apply_row_synthesis(
    rows, lines, enabled: bool, *, keep_unverified_amount: bool = True,
    prefer_rightmost_money: bool = False,
    prefer_arithmetic_triple: bool = True,
    append_arithmetic_triple: bool = False,
):
    """Apply missing-item row creation unless this replay is an ablation arm."""
    if not enabled:
        return rows
    synthesized, _ = _synth_rows(
        rows, lines, prefer_rightmost_money=prefer_rightmost_money,
        prefer_arithmetic_triple=prefer_arithmetic_triple,
        append_arithmetic_triple=append_arithmetic_triple,
    )
    if not keep_unverified_amount:
        for row in synthesized:
            if (
                isinstance(row, dict)
                and row.get("_source") == "invoice_statement_free_row_synth"
            ):
                row["amount"] = ""
    return synthesized


def replay_dispatch(
    snap: dict, *, enable_row_synthesis: bool = True,
    keep_row_synthesis_amount: bool = True,
    prefer_rightmost_row_synthesis_money: bool = False,
    prefer_arithmetic_row_synthesis_triple: bool = True,
    append_arithmetic_row_synthesis_triple: bool = False,
    allow_relaxed_master_item_name_adoption: bool = True,
) -> tuple[dict, str]:
    """Reproduce the server's free->gate->fallback choice on a snapshot envelope.

    Returns (document_fields, path) where path is 'free' or 'fallback'. Skips the
    default-OFF FREE_HIRES_TABLE_REOCR branch (it re-OCRs; not replayable offline).
    """
    lines = _deserialize_lines(snap.get("ocr_lines_raw"))
    img = snap.get("image_size") or [0, 0]
    ctx = snap.get("context") or {}
    dt = snap.get("doc_type", "invoice_statement")
    free = extract_invoice_statement_free(
        ocr_lines_raw=lines, full_text=snap.get("full_text", ""),
        image_size=(int(img[0]), int(img[1])), doc_type=dt, context=ctx,
    )
    if _free_ok(free):
        df = free.get("document_fields") if isinstance(free, dict) else None
        if not isinstance(df, dict):
            df = free
        path = "free"
    else:
        df = extract_invoice_statement_fields(
            lines, debug={},
            table_expected_columns=ctx.get("tableExpectedColumns"),
            table_bounds=ctx.get("tableBounds"),
            column_guides=ctx.get("columnGuides"),
        )
        path = "fallback"
    if isinstance(df, dict) and _sanitize is not None:
        df = _sanitize(df)
    # mirror main.py join-point boilerplate/footer row drop (R1) — before pharma fill
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _drop_boiler(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point ③P1 HA-append (품명단독라인 → 2D 재구성 행 추가)
    if isinstance(df, dict) and isinstance(df.get("tableRows"), list):
        try:
            df["tableRows"], _ = _append_ha(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py join-point blob-amount salvage (empty amount -> last comma-money)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _salvage_blob_amount(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point pharma-column fill (empty cells only)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_pharma(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py join-point 같이읽힘(blob) itemName split (blob 신호 행만)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _split_merged_item_name(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point 컬럼밀림 복구 (itemName 빈칸 + spec 약품명)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _recover_shifted_item_name(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point 품명입양 (itemName 빈 행 ← y-밴드 미소비 품명전용 라인)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _adopt_item_names(
                df["tableRows"], lines,
                allow_relaxed_master=allow_relaxed_master_item_name_adoption,
            )
        except Exception:
            pass
    # mirror main.py join-point 행신설 (미소비 품명라인+콤마금액 y-밴드 쌍, 3중 게이트)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"] = _apply_row_synthesis(
                df["tableRows"], lines, enable_row_synthesis,
                keep_unverified_amount=keep_row_synthesis_amount,
                prefer_rightmost_money=prefer_rightmost_row_synthesis_money,
                prefer_arithmetic_triple=prefer_arithmetic_row_synthesis_triple,
                append_arithmetic_triple=(
                    append_arithmetic_row_synthesis_triple
                ),
            )
        except Exception:
            pass
    # mirror main.py join-point standalone trailing 전문/일반 cleanup
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _strip_item_classification(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point leading barcode/row-number/date code strip
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _strip_leading_item_code(df["tableRows"])
        except Exception:
            pass
    # mirror main.py final-row same-row relocation + OCR-column recovery
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _recover_same_row_amounts(df["tableRows"])
            df["tableRows"], _ = _recover_postjoin_amounts(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py 금액P1 단가·금액 열 복구 (재배정 + 산술 단가fill, 빈칸/오배치만)
    if APPLY_UPA and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _recover_upa(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py 금액P2 산술 금액 채움 (빈 amount = 수량×단가, _rawText anchor)
    if APPLY_UPA and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_arith_amount(df["tableRows"])
        except Exception:
            pass
    # mirror main.py 금액P3 geometry 숫자열 재구성 (빈칸 fill + 산술성립 append)
    if APPLY_UPA and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _geo_recon(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py 수량L2' 스왑 (수량칸↔단가칸 뒤바뀐 행, L1보다 먼저)
    if APPLY_UPA and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fix_swap_qu(df["tableRows"])
        except Exception:
            pass
    # mirror main.py 수량L1 산술 수량 채움 (빈 수량 = 금액÷단가, 빈칸만)
    if APPLY_UPA and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_arith_qty(df["tableRows"])
        except Exception:
            pass
    # mirror main.py 합계 3형제 산술 복구 (supply+tax=total, 10% prior 게이트)
    if APPLY_UPA and isinstance(df, dict):
        try:
            df, _ = _fix_totals(df, lines)
        except Exception:
            pass
    # mirror main.py 품명 밴드입양 (마스터 게이트, 마스터매칭 앞)
    if APPLY_UPA and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _adopt_band_names(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py spec(규격) B: itemName 꼬리 개수/포장 규격 → 빈 spec 복사
    if APPLY_UPA and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_spec_from_name(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point 사업자번호 재선택 (마스터매칭 앞 — itembuycust 앵커)
    if isinstance(df, dict):
        try:
            df, _ = _refine_sup_bizno(df, lines)
            df, _ = _refine_buy_bizno(df, lines)
        except Exception:
            pass
    # mirror main.py join-point 마스터 자동매칭 (빈칸 채움 + itembuycust rescue, ②G4)
    if MASTER_MATCH and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_master(
                df["tableRows"], supplier_bizno=df.get("supplierBizNumber"))
        except Exception:
            pass
    # mirror main.py display cleanup after Master choice (itemName trailing 1/N)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _strip_item_page_fraction(df["tableRows"])
        except Exception:
            pass
    # mirror main.py 보험코드 master-join (itemCode→bohum/pyojun, 마스터매칭 뒤)
    if MASTER_MATCH and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_insurance(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point ④거래처/지점 매칭 (사업자번호 앵커/지점 trigram)
    if isinstance(df, dict):
        try:
            df, _ = _fill_party(df)
        except Exception:
            pass
    # mirror main.py scalar defaults (taxType/discountAmount)
    if isinstance(df, dict):
        try:
            df, _ = _fill_scalars(df)
        except Exception:
            pass
    return (df if isinstance(df, dict) else {}), path


def _load_only_sources(path: str) -> set[str]:
    """Read an exact sourceFile allow-list (one sourceFile per line)."""
    selected: set[str] = set()
    with open(path, encoding="utf-8-sig") as fh:
        for raw in fh:
            value = raw.strip()
            if not value or value.startswith("#"):
                continue
            # Accept a copied sidecar filename as a convenience.
            if value.endswith(".json"):
                value = value[:-5]
            selected.add(value)
    return selected


def _resolve_testset(run_dir: str, requested: str | None) -> str:
    if requested:
        return requested
    meta_path = os.path.join(run_dir, "run_meta.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta_testset = json.load(fh).get("testset")
            if meta_testset in C.TESTSETS:
                return meta_testset
        except Exception:
            pass
    return C.DEFAULT_TESTSET


def replay_compare(
    ts: str | None,
    testset: str | None,
    out_subdir: str,
    only_sources: set[str] | None = None,
    enable_row_synthesis: bool = True,
    keep_row_synthesis_amount: bool = True,
    prefer_rightmost_row_synthesis_money: bool = False,
    prefer_arithmetic_row_synthesis_triple: bool = True,
    append_arithmetic_row_synthesis_triple: bool = False,
    allow_relaxed_master_item_name_adoption: bool = True,
) -> int:
    lookup_testset = testset or C.DEFAULT_TESTSET
    run_dir = os.path.join(C.RUNS_DIR, ts) if ts else C.latest_run(lookup_testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    testset = _resolve_testset(run_dir, testset)
    snap_dir = os.path.join(run_dir, "snapshots")
    if not os.path.isdir(snap_dir):
        print(f"no snapshots/ in {run_dir} — cannot replay (run had no OCR snapshot)."); return 2
    out_dir = os.path.join(run_dir, out_subdir)
    if only_sources and os.path.isdir(out_dir) and os.listdir(out_dir):
        print(f"partial replay output is not empty: {out_dir}")
        print("use a new --out-subdir so stale and current results cannot be mixed")
        return 2
    os.makedirs(out_dir, exist_ok=True)

    # learndata 룩업 로드(있는 것만) → itemCode 옆 measurement 컬럼
    # master_index(code→unit/bp1/nm) = 다중코드 spec-unit 해소용(있으면 자동 적용, 없으면 majority).
    master_index = None
    md_path = os.path.join(HERE, "data/invoice_war/master_dict.json")
    if os.path.isfile(md_path):
        master_index = LDA.load_master_index(md_path)
        print(f"[learndata] master_index ← master_dict.json ({len(master_index):,} codes, spec-unit 해소 ON)")
    learn_luts = []
    for out_key, path in _LEARN_SPECS:
        if os.path.isfile(path):
            dist = LDA.load_dist(path)
            learn_luts.append((out_key, dist))
            print(f"[learndata] {out_key} ← {os.path.basename(path)} (읽기 {len(dist):,}개, learn_count≥3)")
    if not learn_luts:
        print("[learndata] 룩업 파일 없음 → itemCode measurement 컬럼 생략 "
              "(data/invoice_war/learndata_*.json 필요)")

    manifest = build_manifest(testset)
    kind = manifest["kind"]
    # War/ETL thin: ONE aggregate GT, indexed by gtKey (load once). Else per-image.
    agg = None
    if manifest.get("gtAggregate"):
        agg = load_gt_aggregate(os.path.normpath(os.path.join(C.HERE, manifest["gtAggregate"])), profile=kind)
        gtkey_by_src = {s["sourceFile"]: s["gtKey"] for s in manifest["samples"] if s.get("gtKey")}
    else:
        gt_by_src = {s["sourceFile"]: s["gt"] for s in manifest["samples"] if s.get("gt")}

    recorded_scope = _load_recorded_run_scope(run_dir)
    snapshot_sources = {f[:-5] for f in os.listdir(snap_dir) if f.endswith(".json")}
    if recorded_scope is not None:
        missing_snapshots = [src for src in recorded_scope if src not in snapshot_sources]
        if missing_snapshots:
            print(f"run_meta.ran has {len(missing_snapshots)} source(s) without snapshots; "
                  "historical replay would be incomplete")
            for src in missing_snapshots[:20]:
                print(f"  missing snapshot: {src}")
            return 2
        sources = recorded_scope
        stale_count = len(snapshot_sources - set(recorded_scope))
        scope_label = f"run_meta.ran ({len(sources)}), excluded stale snapshots={stale_count}"
    else:
        sources = sorted(snapshot_sources)
        scope_label = f"legacy snapshots ({len(sources)}; no usable run_meta.ran)"
    if only_sources is not None:
        available = set(sources)
        missing = sorted(only_sources - available)
        sources = [src for src in sources if src in only_sources]
        if missing:
            print(f"target list has {len(missing)} source(s) outside this run")
            for src in missing[:20]:
                print(f"  missing target: {src}")
        if not sources:
            print("target list selected 0 snapshots; abort")
            return 2
        scope_label += f", partial target={len(sources)}"
    print(f"replay+score over {os.path.relpath(run_dir, C.RUNS_DIR)}: {scope_label} "
          f"-> {out_subdir}/\n")
    n_written = n_faithful = n_free = 0
    sys.stdout.reconfigure(errors="replace")
    total = len(sources)
    w = len(str(total))
    for i, src in enumerate(sources, 1):
        prog = f"[{i:>{w}}/{total}]"
        if agg is not None:
            gtkey = gtkey_by_src.get(src)
            if not gtkey or gtkey not in agg:
                print(f"  {prog} skip {src:<10} (no GT in manifest)"); continue
        elif not gt_by_src.get(src):
            print(f"  {prog} skip {src:<10} (no GT in manifest)"); continue
        snap = json.load(open(os.path.join(snap_dir, src + ".json"), encoding="utf-8"))
        ext_df, path = replay_dispatch(
            snap, enable_row_synthesis=enable_row_synthesis,
            keep_row_synthesis_amount=keep_row_synthesis_amount,
            prefer_rightmost_row_synthesis_money=(
                prefer_rightmost_row_synthesis_money
            ),
            prefer_arithmetic_row_synthesis_triple=(
                prefer_arithmetic_row_synthesis_triple
            ),
            append_arithmetic_row_synthesis_triple=(
                append_arithmetic_row_synthesis_triple
            ),
            allow_relaxed_master_item_name_adoption=(
                allow_relaxed_master_item_name_adoption
            ),
        )                                               # (edited) parser, faithful dispatch
        n_free += 1 if path == "free" else 0
        gt = agg[gtkey] if agg is not None else load_gt(
            os.path.normpath(os.path.join(C.HERE, gt_by_src[src])), profile=kind)

        # learndata 적용: ext·gt 양쪽에 itemCodeLearn{A,B} + itemNameLearn{A,B} 주입
        # → compare_table 동적 채점. 이름은 learndata 아이템의 정식명(코드→master nm).
        for out_key, dist in learn_luts:
            LDA.apply_to_rows(ext_df.get("tableRows"), gt.get("tableRows"), dist, out_key,
                              master_index=master_index,
                              name_out_key=out_key.replace("itemCode", "itemName"))

        fcmp = compare_fields(gt, ext_df)
        tcmp = compare_table(gt["tableRows"], ext_df.get("tableRows") or [])
        tags = tag_sample(fcmp, tcmp, preprocess=None)
        out = {
            "sourceFile": src, "profile": gt["profile"],
            "extractionPath": path,                     # free | fallback (classifier reads this)
            "pageCount": None, "multiPage": None,
            "replayOptions": {
                "rowSynthesis": enable_row_synthesis,
                "rowSynthesisAmount": keep_row_synthesis_amount,
                "rowSynthesisRightmostMoney": (
                    prefer_rightmost_row_synthesis_money
                ),
                "rowSynthesisArithmeticTriple": (
                    prefer_arithmetic_row_synthesis_triple
                ),
                "rowSynthesisAppendArithmeticTriple": (
                    append_arithmetic_row_synthesis_triple
                ),
                "relaxedMasterItemNameAdoption": (
                    allow_relaxed_master_item_name_adoption
                ),
            },
            "fields": fcmp, "table": tcmp, "buckets": tags,
        }
        with open(os.path.join(out_dir, src + ".json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2); fh.write("\n")
        n_written += 1

        rec = _recorded_df(run_dir, src)
        faithful = rec is not None and _canon(rec) == _canon(ext_df)
        n_faithful += 1 if faithful else 0
        fa = fcmp["fieldAccuracy"]; ca = tcmp["cellAccuracy"]
        tag = "FAITHFUL" if faithful else ("CHANGED " if rec is not None else "no-record")
        print(f"  {prog} {tag}  {path:<8} {src:<10} field={('n/a' if fa is None else f'{fa*100:5.1f}%')}"
              f"  cell={('n/a' if ca is None else f'{ca*100:5.1f}%')}")

    print(f"\n[written] {out_dir}  ({n_written} samples, path: {n_free} free / "
          f"{n_written - n_free} fallback, {n_faithful} unchanged vs recorded)")
    print(f"next: python eval/parser_drop_classify.py --ts {os.path.relpath(run_dir, C.RUNS_DIR)} "
          f"--compare-dir {out_subdir}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None, help="run dir under runs/ (default: latest study run)")
    ap.add_argument("--testset", default=None,
                    help="default: infer from run_meta.json, then invoice_study")
    ap.add_argument("--out-subdir", default="replay_compare",
                    help="sidecar dir under the run (NOT the checker's compare/). "
                         "Partial replay convention: replay_lab/replay_probe_<name>")
    ap.add_argument("--only-list", default=None,
                    help="partial replay: UTF-8 sourceFile list, one per line")
    ap.add_argument("--no-master-match", action="store_true",
                    help="②G4 마스터 매칭 없이 replay (Rule 단계 사이드카용; "
                         "관례: --out-subdir replay_compare_rule)")
    ap.add_argument("--skip-upa", action="store_true",
                    help="금액P1 단가·금액 열복구 없이 replay (P1 전 base 사이드카용; "
                         "관례: --out-subdir replay_compare_base)")
    ap.add_argument("--disable-row-synth", action="store_true",
                    help="ablation only: disable missing-item row creation while "
                         "keeping every other parser and matcher step identical")
    ap.add_argument("--row-synth-name-only", action="store_true",
                    help="candidate only: create the missing item-name row but do "
                         "not trust its single unverified comma-number as amount")
    ap.add_argument("--row-synth-rightmost-money", action="store_true",
                    help="candidate only: when multiple comma-numbers share the "
                         "name row, use the rightmost one instead of the first")
    ap.add_argument("--row-synth-arithmetic-triple", action="store_true",
                    help="candidate only: fill quantity, unit price and amount "
                         "only when one q*u=amount triple exists in the row band")
    ap.add_argument("--row-synth-arithmetic-merge-only", action="store_true",
                    help="explicitly select the adopted default: use a unique "
                         "q*u=amount triple only to fill an existing empty-name row")
    ap.add_argument("--disable-row-synth-arithmetic-merge", action="store_true",
                    help="ablation only: disable the adopted arithmetic merge while "
                         "keeping ordinary missing-row synthesis enabled")
    ap.add_argument("--adopt-relaxed-master-name", action="store_true",
                    help="explicitly select the adopted default: allow a generic "
                         "Korean/English line to fill an existing empty-name row "
                         "at Master similarity >=0.70")
    ap.add_argument("--disable-relaxed-master-name-adoption", action="store_true",
                    help="ablation only: disable the adopted relaxed Master-name "
                         "adoption while keeping ordinary item-name adoption enabled")
    args = ap.parse_args()
    if args.no_master_match:
        MASTER_MATCH = False
    if args.skip_upa:
        APPLY_UPA = False
    only_sources = _load_only_sources(args.only_list) if args.only_list else None
    if args.only_list and args.out_subdir == "replay_compare":
        ap.error("--only-list requires a distinct --out-subdir "
                 "(for example replay_lab/replay_probe_R001)")
    raise SystemExit(replay_compare(
        args.ts, args.testset, args.out_subdir, only_sources=only_sources,
        enable_row_synthesis=not args.disable_row_synth,
        keep_row_synthesis_amount=not args.row_synth_name_only,
        prefer_rightmost_row_synthesis_money=args.row_synth_rightmost_money,
        prefer_arithmetic_row_synthesis_triple=(
            not args.disable_row_synth_arithmetic_merge
            or args.row_synth_arithmetic_triple
            or args.row_synth_arithmetic_merge_only
        ),
        append_arithmetic_row_synthesis_triple=(
            args.row_synth_arithmetic_triple
            and not args.row_synth_arithmetic_merge_only
        ),
        allow_relaxed_master_item_name_adoption=(
            not args.disable_relaxed_master_name_adoption
            or args.adopt_relaxed_master_name
        )))
