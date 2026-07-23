"""Analyze item-name changes from raw OCR to Master on the 067 fair row set.

Read-only: consumes existing Google selector caches and replay sidecars. It does
not run OCR or replay and does not modify scorecards.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from types import SimpleNamespace

import baseline_matrix as B
import learndata_apply as LDA

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from extractors.master_match import (
    MATCH_SIM_FLOOR,
    MasterMatcher,
    _compact_alnum,
    _sfx_score,
    clean_query_name,
    dose_score,
    dose_tokens,
    pack_tokens,
    paren_tokens,
    parse_price,
)


def _configure_9000() -> None:
    B._apply_preset(SimpleNamespace(
        preset="9000", sample=None, gt=None, out=None, mmatch=None, cust=None,
    ))


def _master_name_index(data: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for code, entry in (data.get("item") or {}).items():
        name = (entry or {}).get("nm")
        key = B._clean_nm(name)
        if key:
            out[key].add(str(code))
    return out


def analyze(run: str, scope: str = "fair", supplier_only: bool = False) -> dict:
    _configure_9000()
    keys = B.load_sample_keys()
    _, detail = B.compute_google_master(keys)
    selectors = (detail.get("independentSelectors") or {}).get("itemName") or {}
    if scope == "full":
        selectors = {
            B._safe_sample_id(key): None
            for key in (keys or set())
        }
    compare_dir = os.path.join(B.HERE, "runs", run, "replay_compare")
    runtime_master_path = os.path.abspath(
        os.path.join(B.HERE, "..", "master_dict.json")
    )
    runtime_learn_path = os.path.abspath(
        os.path.join(B.HERE, "..", "learndata_runtime.json")
    )
    master_data = json.load(open(runtime_master_path, encoding="utf-8"))
    runtime_learn = (
        json.load(open(runtime_learn_path, encoding="utf-8"))
        if os.path.isfile(runtime_learn_path) else {}
    )
    master_names = _master_name_index(master_data)
    matcher = MasterMatcher(
        master_data.get("item") or {}, master_data.get("itembuycust"), runtime_learn
    )
    heldout_path = os.path.join(B.DATA, "learndata_heldout.json")
    learn_dist = LDA.load_dist(heldout_path) if os.path.isfile(heldout_path) else {}
    learn_master = LDA.load_master_index(runtime_master_path)

    transitions = Counter()
    regressions = Counter()
    guard = Counter()
    code_canonical = Counter()
    rerank_rows = []
    learn_gate_rows = []
    ibc_rows = []
    failure_signals = Counter()
    runtime_learn_parity = Counter()
    runtime_learn_mismatches = []
    samples = []
    candidate_cache = {}

    for safe_id, selected in selectors.items():
        path = os.path.join(compare_dir, safe_id + ".json")
        if not os.path.isfile(path):
            continue
        comp = json.load(open(path, encoding="utf-8"))
        supplier_biz = "".join(
            ch for ch in str(
                ((((comp.get("fields") or {}).get("perField") or {})
                  .get("supplierBizNumber") or {}).get("ext") or "")
            ) if ch.isdigit()
        )
        remaining = Counter(selected) if selected is not None else None
        for row in (comp.get("table") or {}).get("rows", []):
            cells = row.get("cells") or {}
            if remaining is not None:
                sig = B._cell_gt_signature(cells)
                if remaining[sig] <= 0:
                    continue
                remaining[sig] -= 1

            raw = cells.get("itemName") or {}
            master = cells.get("itemNameMaster") or {}
            learn_a = cells.get("itemNameLearnA") or {}
            raw_ok = raw.get("status") == "match"
            master_ok = master.get("status") == "match"
            transitions[("ok" if raw_ok else "bad",
                         "ok" if master_ok else "bad")] += 1

            raw_value = str(raw.get("ext") or "")
            master_value = str(master.get("ext") or "")
            raw_key = B._clean_nm(raw_value)
            exact_codes = master_names.get(raw_key) or set()
            exact = bool(exact_codes)
            unique = len(exact_codes) == 1
            query_name = clean_query_name(raw_value)
            ranked_for_row = candidate_cache.get(query_name)
            if ranked_for_row is None:
                ranked_for_row = matcher.top_candidates(query_name, 30)
                candidate_cache[query_name] = ranked_for_row

            ext_code = str((cells.get("itemCode") or {}).get("ext") or "")
            code_i = matcher._cd2i.get(ext_code)
            if code_i is not None:
                code_canonical["eligible"] += 1
                code_name_ok = (
                    B._clean_nm(matcher.entry(code_i)["itemNameMaster"])
                    == B._clean_nm(master.get("gt"))
                )
                if code_name_ok:
                    code_canonical["correct"] += 1
                if code_name_ok and not master_ok:
                    code_canonical["gain"] += 1
                if master_ok and not code_name_ok:
                    code_canonical["regress"] += 1

            price = parse_price((cells.get("unitPrice") or {}).get("ext"))
            quantity = (cells.get("quantity") or {}).get("ext")
            amount = (cells.get("amount") or {}).get("ext")
            if price is None:
                qdigits = "".join(ch for ch in str(quantity or "") if ch.isdigit())
                parsed_amount = parse_price(amount)
                if qdigits and parsed_amount:
                    qnum = int(qdigits)
                    if qnum > 0:
                        price = round(parsed_amount / qnum)
            spec = str((cells.get("spec") or {}).get("ext") or "")
            runtime_code = matcher.resolve_learndata_code(
                raw_value, spec=spec,
                price=(cells.get("unitPrice") or {}).get("ext"),
                quantity=quantity, amount=amount,
            )
            q_dose = dose_tokens(f"{raw_value} {spec}")
            q_pack = pack_tokens(f"{spec} {quantity or ''}")
            q_paren = paren_tokens(raw_value) | paren_tokens(spec)
            if not supplier_only:
                features = []
                for sim, idx in ranked_for_row:
                    if sim < MATCH_SIM_FLOOR:
                        continue
                    ds = dose_score(
                        q_dose, q_pack, matcher._nms[idx], matcher._units[idx]
                    )
                    dscore = 0.0 if ds is None else (-1.0 if ds == 0 else ds)
                    pscore = 0.0
                    if price is not None and price > 0:
                        pscore = max(
                            0.0,
                            1.0 - abs(matcher._bp1s[idx] - price) / price,
                        )
                    sfx = _sfx_score(q_paren, paren_tokens(matcher._nms[idx]))
                    name_ok = (
                        B._clean_nm(matcher.entry(idx)["itemNameMaster"])
                        == B._clean_nm(master.get("gt"))
                    )
                    features.append((sim, dscore, pscore, sfx, name_ok))
                rerank_rows.append((master_ok, features))

            history = matcher._ibc.get(supplier_biz) or set()
            history_candidates = [
                (sim, idx) for sim, idx in ranked_for_row
                if sim >= MATCH_SIM_FLOOR and idx in history
            ]
            if history_candidates:
                proposed_sim, proposed_i = history_candidates[0]
                global_sim = ranked_for_row[0][0] if ranked_for_row else 0.0
                proposed_name = matcher.entry(proposed_i)["itemNameMaster"]
                proposed_ok = (
                    B._clean_nm(proposed_name) == B._clean_nm(master.get("gt"))
                )
                proposed_key = _compact_alnum(proposed_name)
                proposed_dose = dose_score(
                    q_dose, q_pack,
                    matcher._nms[proposed_i], matcher._units[proposed_i],
                )
                ibc_rows.append({
                    "month": safe_id[:4],
                    "file": safe_id,
                    "rowIndex": row.get("rowIndex"),
                    "supplierBiz": supplier_biz,
                    "raw": raw_value,
                    "current": master_value,
                    "proposed": proposed_name,
                    "gt": str(master.get("gt") or ""),
                    "globalSim": round(global_sim, 4),
                    "proposedSim": round(proposed_sim, 4),
                    "doseScore": proposed_dose,
                    "learnAAgrees": (
                        runtime_code == matcher._cds[proposed_i]
                    ),
                    "masterOk": master_ok,
                    "proposedOk": proposed_ok,
                    "changed": (
                        B._clean_nm(proposed_name) != B._clean_nm(master_value)
                    ),
                    "margin": global_sim - proposed_sim,
                    "contained": bool(
                        proposed_key and proposed_key in _compact_alnum(raw_value)
                    ),
                })

            learn_ok = learn_a.get("status") == "match"
            counter = learn_dist.get(raw_value)
            learn_code = str((cells.get("itemCodeLearnA") or {}).get("ext") or "")
            if learn_code and counter:
                if learn_code not in matcher._cd2i:
                    runtime_learn_parity["expectedCodeMissingMaster"] += 1
                else:
                    runtime_learn_parity["scored"] += 1
                    if runtime_code == learn_code:
                        runtime_learn_parity["match"] += 1
                    elif len(runtime_learn_mismatches) < 20:
                        runtime_learn_mismatches.append({
                        "file": safe_id,
                        "rowIndex": row.get("rowIndex"),
                        "reading": raw_value,
                        "spec": spec,
                        "unitPrice": (cells.get("unitPrice") or {}).get("ext"),
                        "quantity": quantity,
                        "amount": amount,
                        "expected": learn_code,
                        "runtime": runtime_code,
                        "counts": dict(counter),
                        })
            if not supplier_only and counter and learn_code:
                total_count = sum(counter.values())
                chosen_count = counter.get(learn_code, 0)
                dominance = chosen_count / total_count if total_count else 0.0
                unit_match = bool(
                    LDA._normspec(spec)
                    and LDA._normspec(spec)
                    == (learn_master.get(learn_code) or {}).get("unit")
                )
                price_match = False
                bp1 = (learn_master.get(learn_code) or {}).get("bp1") or 0
                if price is not None and price > 0 and bp1:
                    price_match = abs(bp1 - price) <= price * 0.01
                learn_gate_rows.append({
                    "masterOk": master_ok,
                    "learnOk": learn_ok,
                    "codes": len(counter),
                    "total": total_count,
                    "dominance": dominance,
                    "unitMatch": unit_match,
                    "priceMatch": price_match,
                })

            if raw_ok and not master_ok:
                regressions["total"] += 1
                regressions["blank_master" if not master_value else "wrong_master"] += 1
                regressions["raw_is_master_name" if exact else "raw_not_master_name"] += 1
                if unique:
                    regressions["raw_is_unique_master_name"] += 1

                gt_code = str((cells.get("itemCode") or {}).get("gt") or "")
                selected_code = str((cells.get("itemCode") or {}).get("ext") or "")
                expected_i = matcher._cd2i.get(gt_code)
                if not gt_code:
                    regressions["no_gt_code"] += 1
                elif expected_i is None:
                    regressions["gt_code_not_in_master"] += 1
                else:
                    regressions["gt_code_in_master"] += 1
                    rank = next(
                        (pos for pos, (_sim, idx) in enumerate(ranked_for_row, 1)
                         if idx == expected_i),
                        None,
                    )
                    if rank is None:
                        regressions["correct_not_in_top30"] += 1
                    else:
                        regressions["correct_in_top30"] += 1
                        history = matcher._ibc.get(supplier_biz) or set()
                        if history:
                            failure_signals["has_supplier_history"] += 1
                        if expected_i in history:
                            failure_signals["correct_in_supplier_history"] += 1
                        elif history:
                            failure_signals["correct_not_in_supplier_history"] += 1
                        regressions[
                            "correct_rank_1" if rank == 1
                            else "correct_rank_2_5" if rank <= 5
                            else "correct_rank_6_30"
                        ] += 1
                if selected_code == gt_code and gt_code:
                    regressions["code_correct_name_wrong"] += 1
                if len(samples) < 20:
                    samples.append({
                        "file": safe_id,
                        "rowIndex": row.get("rowIndex"),
                        "raw": raw_value,
                        "master": master_value,
                        "gt": master.get("gt"),
                        "exactMasterCodes": len(exact_codes),
                    })

            # Runtime-safe name guard simulation:
            # preserve raw only when its normalized value is already present in
            # the canonical master dictionary.
            if exact and raw_ok and not master_ok:
                guard["gain_exact"] += 1
            if exact and master_ok and not raw_ok:
                guard["regress_exact"] += 1
            if unique and raw_ok and not master_ok:
                guard["gain_unique"] += 1
            if unique and master_ok and not raw_ok:
                guard["regress_unique"] += 1

    total = sum(transitions.values())
    rerank = {}
    for dose_weight in (0.0, 0.02, 0.05, 0.10, 0.20):
        for price_weight in (0.0, 0.01, 0.02, 0.05):
            ok = gain = regress = 0
            for current_ok, features in rerank_rows:
                if features:
                    chosen = max(
                        features,
                        key=lambda x: (
                            x[0] + dose_weight * x[1] + price_weight * x[2]
                            + 0.01 * x[3],
                            x[0],
                        ),
                    )
                    proposed_ok = chosen[4]
                else:
                    proposed_ok = False
                ok += int(proposed_ok)
                gain += int(proposed_ok and not current_ok)
                regress += int(current_ok and not proposed_ok)
            rerank[f"d{dose_weight:.2f}_p{price_weight:.2f}"] = {
                "ok": ok, "gain": gain, "regress": regress,
                "netVsCurrent": gain - regress,
            }
    rerank = dict(sorted(
        rerank.items(), key=lambda item: item[1]["netVsCurrent"], reverse=True
    )[:8])
    gate_defs = {
        "all": lambda r: True,
        "single_code": lambda r: r["codes"] == 1,
        "dominance_70": lambda r: r["dominance"] >= 0.70,
        "dominance_80": lambda r: r["dominance"] >= 0.80,
        "dominance_90": lambda r: r["dominance"] >= 0.90,
        "unit_match": lambda r: r["unitMatch"],
        "price_1pct": lambda r: r["priceMatch"],
        "single_or_unit": lambda r: r["codes"] == 1 or r["unitMatch"],
        "dom80_and_count5": lambda r: (
            r["dominance"] >= 0.80 and r["total"] >= 5
        ),
        "unit_or_price": lambda r: r["unitMatch"] or r["priceMatch"],
    }
    learn_gates = {}
    for name, gate in gate_defs.items():
        fired = gain = regress = 0
        for row in learn_gate_rows:
            if not gate(row):
                continue
            fired += 1
            gain += int(row["learnOk"] and not row["masterOk"])
            regress += int(row["masterOk"] and not row["learnOk"])
        learn_gates[name] = {
            "fired": fired, "gain": gain, "regress": regress,
            "net": gain - regress,
        }
    ibc_gates = {}
    for margin in (0.0, 0.01, 0.02, 0.05, 0.10):
        for require_contained, require_learn_agree in (
            (False, False), (True, False), (True, True),
        ):
            label = f"margin_{margin:.2f}" + (
                "_contained" if require_contained else ""
            ) + ("_learn_agree" if require_learn_agree else "")
            fired = gain = regress = 0
            monthly: dict[str, Counter] = defaultdict(Counter)
            for row in ibc_rows:
                if not row["changed"]:
                    continue
                if row["margin"] > margin:
                    continue
                if require_contained and not row["contained"]:
                    continue
                if require_learn_agree and not row["learnAAgrees"]:
                    continue
                fired += 1
                is_gain = row["proposedOk"] and not row["masterOk"]
                is_regress = row["masterOk"] and not row["proposedOk"]
                gain += int(is_gain)
                regress += int(is_regress)
                monthly[row["month"]]["gain"] += int(is_gain)
                monthly[row["month"]]["regress"] += int(is_regress)
            month_nets = {
                month: counts["gain"] - counts["regress"]
                for month, counts in sorted(monthly.items())
            }
            ibc_gates[label] = {
                "fired": fired, "gain": gain, "regress": regress,
                "neutral": fired - gain - regress,
                "net": gain - regress,
                "positiveMonths": sum(v > 0 for v in month_nets.values()),
                "negativeMonths": sum(v < 0 for v in month_nets.values()),
                "zeroMonths": sum(v == 0 for v in month_nets.values()),
            }
    ibc_safe_samples = [
        {
            key: row[key] for key in (
                "month", "file", "rowIndex", "supplierBiz", "raw",
                "current", "proposed", "globalSim", "proposedSim",
                "doseScore", "learnAAgrees", "gt", "masterOk", "proposedOk",
            )
        }
        for row in ibc_rows
        if row["margin"] <= 0.10
        and row["changed"]
        and row["contained"]
    ]
    ibc_regression_samples = [
        {
            key: row[key] for key in (
                "month", "file", "rowIndex", "supplierBiz", "raw",
                "current", "proposed", "globalSim", "proposedSim",
                "doseScore", "learnAAgrees", "gt", "masterOk", "proposedOk",
            )
        }
        for row in ibc_rows
        if row["margin"] <= 0.10
        and row["changed"]
        and row["contained"]
        and row["masterOk"]
        and not row["proposedOk"]
    ]
    ibc_triple_samples = [
        {
            key: row[key] for key in (
                "month", "file", "rowIndex", "supplierBiz", "raw",
                "current", "proposed", "globalSim", "proposedSim",
                "doseScore", "learnAAgrees", "gt", "masterOk", "proposedOk",
            )
        }
        for row in ibc_rows
        if row["margin"] <= 0.10
        and row["changed"]
        and row["contained"]
        and row["learnAAgrees"]
    ]
    return {
        "run": run,
        "scope": scope,
        "selectedRows": total,
        "transitions": {f"{a}->{b}": n for (a, b), n in transitions.items()},
        "regressions": dict(regressions),
        "guard": {
            **guard,
            "net_exact": guard["gain_exact"] - guard["regress_exact"],
            "net_unique": guard["gain_unique"] - guard["regress_unique"],
        },
        "codeCanonical": {
            **code_canonical,
            "net": code_canonical["gain"] - code_canonical["regress"],
        },
        "rerankTop8": rerank,
        "learnAGates": dict(sorted(
            learn_gates.items(), key=lambda item: item[1]["net"], reverse=True
        )),
        "top30FailureSignals": dict(failure_signals),
        "runtimeLearnParity": {
            **runtime_learn_parity,
            "pct": (
                100.0 * runtime_learn_parity["match"]
                / runtime_learn_parity["scored"]
                if runtime_learn_parity["scored"] else None
            ),
            "mismatches": runtime_learn_mismatches,
        },
        "supplierHistoryGates": dict(sorted(
            ibc_gates.items(), key=lambda item: item[1]["net"], reverse=True
        )),
        "supplierHistorySafeChanges": ibc_safe_samples,
        "supplierHistoryRegressions": ibc_regression_samples,
        "supplierHistoryTripleChanges": ibc_triple_samples,
        "samples": samples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="067_20260720_175949")
    ap.add_argument("--scope", choices=("fair", "full"), default="fair")
    ap.add_argument("--supplier-only", action="store_true")
    ap.add_argument(
        "--targets-out",
        default=None,
        help="write unique sourceFiles touched by the supplier/LearnData triple gate",
    )
    ap.add_argument("--quiet", action="store_true",
                    help="suppress the large JSON report (target-list workflow)")
    ap.add_argument("--json-out", default=None,
                    help="write the full analysis JSON to this path")
    args = ap.parse_args()
    result = analyze(args.run, scope=args.scope, supplier_only=args.supplier_only)
    if args.targets_out:
        sources = sorted({
            row["file"]
            for row in result["supplierHistoryTripleChanges"]
            if row.get("file")
        })
        with open(args.targets_out, "w", encoding="utf-8") as fh:
            for source in sources:
                fh.write(source + "\n")
        print(f"[targets] {args.targets_out}: {len(sources):,} documents")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(f"[analysis] {args.json_out}")
    if not args.quiet:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
