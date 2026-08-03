"""demo_next_target — 다음 타깃(잃어버린 품명 / 아직 못 읽는 품명)을 찾는 기준셋 스캔.

★기준(자)은 항상 같다: <기준셋 9,001 문서에서 수확한 품명 크롭> 고정 집합.
  072 리플레이는 base 판독을 준 1회성 산출물이고, 그 뒤로는 문서 파이프라인을 다시
  돌릴 필요가 없다 — 같은 크롭 집합을 새 모델로 다시 읽히면 그 모델의 판독이 나온다.
  (인식만 수행, 파서·정렬 없음 → 수 분. 문서 단위 eval 불필요)

  base  → 072 리플레이(또는 이 스캔)  = 1차 1단계 타깃 선정 근거
  m1    → 이 스캔                     = 1차 2단계 타깃(잃어버린 품명)
  m2    → 이 스캔                     = 2차 1단계 타깃(m2 가 못 읽는 품명)  …

각 스캔 결과는 demo/scans/<실행번호>.jsonl 로 남긴다. 다음 단계에서 '무엇을 잃었나'는
직전 스캔과 대조만 하면 되므로, 모델 하나만 새로 읽히면 된다(재스캔 없음).

출력: demo/<실행번호>/NEXT_TARGETS.json
  lost    직전 모델은 맞게 읽던 품명인데 이번 모델이 틀림  → 이번 회차 2단계 타깃
  unread  이번 모델이 그 품명의 모든 출현을 틀림           → 다음 회차 1단계 타깃

    python eval/demo_next_target.py --run-tag 260803_1200
    python eval/demo_next_target.py --run-tag 260803_1200 --prev-scan demo/scans/<직전>.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR, CORPUS_PATH  # noqa: E402
from finetune_crops import load_labels, crop_name  # noqa: E402
from finetune_report import _report_id, BASE_MODEL, find_ft_inference, predict_all  # noqa: E402
from demo_report import _demo_run_dir, DEMO_DIR  # noqa: E402

FAIL_LABELS = os.path.join(CORPUS_DIR, "labels.txt")
BAL_LABELS = os.path.join(CORPUS_DIR, "labels_correct.txt")
BAL_META = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
REPLAY_SRC = os.path.join(CORPUS_DIR, "replay_sources.txt")
SCANS_DIR = os.path.join(DEMO_DIR, "scans")
HANGUL = re.compile(r"[가-힣]")


def basis_crops(min_match: float, limit: int = 0) -> list[tuple[str, str]]:
    """기준셋(9,001) 문서에서 수확한 품명 크롭 = 고정 판독 대상.

    failure 풀(ledger 에 src)과 정답 풀(meta 사이드카에 src) 양쪽에서 모은다.
    정답 풀이 있어야 '원래 읽히던 품명을 잃었다'를 볼 수 있다.
    """
    replay = set()
    if os.path.exists(REPLAY_SRC):
        replay = {ln.strip() for ln in open(REPLAY_SRC, encoding="utf-8") if ln.strip()}
    if not replay:
        raise SystemExit(f"기준셋 소스 목록이 없습니다: {REPLAY_SRC}")

    rows: list[tuple[str, str]] = []
    fails = load_labels(FAIL_LABELS)
    for ln in open(CORPUS_PATH, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if e.get("column") != "itemName" or e.get("src") not in replay:
            continue
        if (e.get("matchRatio") or 0) < min_match:
            continue
        rel = "crops/" + crop_name(e)
        gt = fails.get(rel)
        if gt and os.path.exists(os.path.join(CORPUS_DIR, rel)):
            rows.append((rel, gt))

    if os.path.exists(BAL_META):
        bal = load_labels(BAL_LABELS)
        for ln in open(BAL_META, encoding="utf-8"):
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if rec.get("column") != "itemName" or rec.get("src") not in replay:
                continue
            rel = rec.get("path")
            gt = bal.get(rel)
            if gt and os.path.exists(os.path.join(CORPUS_DIR, rel)):
                rows.append((rel, gt))
    if limit:
        rows = rows[:limit]
    return rows


def _load_scan(path: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path or not os.path.exists(path):
        return out
    for ln in open(path, encoding="utf-8"):
        try:
            d = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if d.get("path"):
            out[d["path"]] = d
    return out


def _latest_scan(exclude: str) -> str | None:
    cands = sorted(glob.glob(os.path.join(SCANS_DIR, "*.jsonl")))
    cands = [c for c in cands if os.path.abspath(c) != os.path.abspath(exclude)]
    return cands[-1] if cands else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-tag", dest="run_tag")
    ap.add_argument("--prev-scan", default=None,
                    help="직전 모델 스캔 결과(jsonl). 미지정 = demo/scans 최신")
    ap.add_argument("--exclude", default="", help="이미 타깃인 품명(콤마) — 후보에서 제외")
    ap.add_argument("--min-match", type=float, default=0.7)
    ap.add_argument("--limit", type=int, default=0, help="스캔 크롭 상한(0=전부)")
    ap.add_argument("--min-count", type=int, default=3, help="후보 품명의 최소 출현 크롭 수")
    args = ap.parse_args()
    run_tag = _report_id(args.run_tag)
    already = {t.strip().replace(" ", "") for t in args.exclude.split(",") if t.strip()}

    rows = basis_crops(args.min_match, args.limit)
    if not rows:
        raise SystemExit("기준셋 품명 크롭을 찾지 못했습니다(코퍼스/replay_sources 확인)")
    print(f"[스캔] 기준셋 품명 크롭 {len(rows):,}장 — 이번 모델로 판독")

    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore
    ft_dir = find_ft_inference()
    if not ft_dir:
        raise SystemExit("파인튜닝 inference 디렉터리 없음 — export 먼저")
    preds = predict_all(create_model(BASE_MODEL, ft_dir),
                        [os.path.join(CORPUS_DIR, r) for r, _ in rows])

    os.makedirs(SCANS_DIR, exist_ok=True)
    scan_path = os.path.join(SCANS_DIR, f"{run_tag}.jsonl")
    with open(scan_path, "w", encoding="utf-8") as f:
        for (rel, gt), p in zip(rows, preds):
            f.write(json.dumps({"path": rel, "gt": gt, "pred": p,
                                "ok": p.strip() == gt.strip()}, ensure_ascii=False) + "\n")
    print(f"[스캔] 저장: {scan_path}")

    prev_path = args.prev_scan or _latest_scan(scan_path)
    prev = _load_scan(prev_path) if prev_path else {}
    prev_label = os.path.basename(prev_path or "")
    if prev:
        print(f"[대조] 직전 스캔: {prev_path} ({len(prev):,}장)")
    else:
        # ★1차 1단계에는 직전 스캔이 없다. 그런데 base 의 크롭별 정오답은 이미 알고 있다 —
        #  크롭이 어느 풀에서 수확됐는지가 곧 base 판정이기 때문:
        #    crops/          = base 가 틀린 셀에서 잘린 크롭
        #    crops_correct/  = base 가 맞힌 셀에서 잘린 크롭
        #  이 풀 정보를 base 스캔 대신 써서 "base 는 읽던 걸 m1 이 잃었다"를 바로 계산한다.
        prev = {rel: {"ok": rel.startswith("crops_correct/")} for rel, _ in rows}
        prev_label = "pools(base)"
        n_ok = sum(1 for v in prev.values() if v["ok"])
        print(f"[대조] 직전 스캔 없음 → base 는 크롭 풀로 대체 "
              f"(정답 {n_ok:,} / 오답 {len(prev) - n_ok:,})")

    lost = defaultdict(lambda: {"n": 0, "hit": 0, "wrong": {}})
    unread = defaultdict(lambda: {"n": 0, "hit": 0, "wrong": {}})
    for (rel, gt), p in zip(rows, preds):
        ok = p.strip() == gt.strip()
        u = unread[gt]
        u["n"] += 1
        if not ok:
            u["hit"] += 1
            u["wrong"][p.strip() or "(빈칸)"] = u["wrong"].get(p.strip() or "(빈칸)", 0) + 1
        pv = prev.get(rel)
        if pv and pv.get("ok"):
            l = lost[gt]
            l["n"] += 1
            if not ok:
                l["hit"] += 1
                l["wrong"][p.strip() or "(빈칸)"] = l["wrong"].get(p.strip() or "(빈칸)", 0) + 1

    def _rank(stat) -> list[dict]:
        out = []
        for gt, s in stat.items():
            if (gt.replace(" ", "") in already or s["n"] < args.min_count
                    or not s["hit"] or not HANGUL.search(gt)):
                continue
            out.append({"name": gt, "crops": s["n"], "hits": s["hit"],
                        "rate": round(100.0 * s["hit"] / s["n"], 1),
                        "wrong": sorted(s["wrong"].items(), key=lambda x: -x[1])[:3]})
        out.sort(key=lambda x: (-x["rate"], -x["crops"]))   # 전 출현이 뒤집힌 것 우선
        return out[:20]

    lost_r, unread_r = _rank(lost), _rank(unread)
    payload = {"schemaVersion": "demo-next-target.v2", "runTag": run_tag,
               "basisCrops": len(rows), "prevScan": prev_label,
               "lost": lost_r, "unread": unread_r}
    out_path = os.path.join(_demo_run_dir(run_tag), "NEXT_TARGETS.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    def _show(title, items):
        print(f"\n[{title}] 상위 5")
        for c in items[:5]:
            w = " · ".join(f"“{k}” {v}" for k, v in c["wrong"][:2])
            print(f"  {c['name'][:34]:36} {c['hits']}/{c['crops']}장 ({c['rate']}%)  {w[:50]}")
        if not items:
            print("  (없음)")

    _show("이번 단계 2단계 타깃 후보 — 직전 모델이 읽던 걸 잃음", lost_r)
    _show("다음 회차 1단계 타깃 후보 — 이번 모델이 여전히 못 읽음", unread_r)
    print(f"\n[저장] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
