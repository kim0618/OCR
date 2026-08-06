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
# ★기준셋 확정 목록(2026-08-04 전수 검증). 87,316 중 46%가 품명이 아닌 조각 크롭
#  (검출 실패 박스에 셀 전체 라벨이 붙은 것 - base·FT 모두 정답 0.00%로 실증,
#   표본 40장 육안 판독 40/40 조각). 폭/(글자수*높이) >= 0.30 만 남긴 45,617장.
#  남김 구간은 표본 40/40 전부 진짜 품명으로 확인됨.
BASIS_KEEP = os.path.join(DEMO_DIR, "basis_keep.txt")


_GT_BAD_PATH = os.path.join(DEMO_DIR, "gt_bad.txt")


def gt_bad() -> set[str]:
    """크롭 실물로 확인된 GT 오독 품명(공백 제거). 후보·손실 집계에서 뺀다.
    모델이 틀린 게 아니라 정답 라벨이 틀린 건이라, 세면 실험 신호가 흐려진다."""
    out: set[str] = set()
    if os.path.exists(_GT_BAD_PATH):
        for ln in open(_GT_BAD_PATH, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                out.add(ln.split("\t")[0].replace(" ", ""))
    return out


def basis_keep() -> set[str] | None:
    """확정 목록. 없으면 None(필터 없이 동작 - 구버전 호환)."""
    if not os.path.exists(BASIS_KEEP):
        return None
    return {ln.strip() for ln in open(BASIS_KEEP, encoding="utf-8") if ln.strip()}
HANGUL = re.compile(r"[가-힣]")

# 후보에는 실제 품명만 남긴다. 거래명세서의 품명 컬럼에는 약품명 말고도
# 할인·집계 행과 표 헤더 조각이 섞여 들어오는데, 이런 건 학습 타깃이 될 수 없다.
# 특히 '매입에누리(OCR)' 류는 이미지마다 글자가 다른데 라벨만 하나로 뭉쳐 있어
# 타깃으로 삼으면 서로 다른 글자를 같은 문자열로 읽으라고 가르치는 셈이 된다.
_NOT_ITEM_EXACT = {"품명", "규격", "수량", "단가", "금액", "비고", "명", "계",
                   "소계", "합계", "총계", "이월", "잔액", "전잔", "당잔"}
_NOT_ITEM_PART = ("에누리", "할인", "부가세", "부가가치세", "공급가", "매출", "매입",
                  "반품", "미수", "수금", "운임", "배송비", "택배비", "(OCR)")


def is_item_name(name: str) -> bool:
    """후보로 쓸 수 있는 실제 품명인가."""
    s = (name or "").strip()
    if not HANGUL.search(s):
        return False
    flat = s.replace(" ", "")
    if flat in _NOT_ITEM_EXACT or len(flat) < 3:
        return False
    if flat != flat.strip(_EDGE_JUNK):
        return False          # 앞뒤에 표 테두리가 붙은 오염 라벨 - 학습 타깃으로 부적합
    return not any(k in s for k in _NOT_ITEM_PART)


# 표 테두리·얼룩을 글자로 읽은 흔적. 원문 GT(구글 OCR)에는 이런 게 그대로 남는다
# (build_gt.sql: itemName = 원문 description, 마스터 정식명은 itemNameMaster 로 따로).
# ★'%'는 뺀다 - "헥사메딘액0.12%"처럼 품명의 일부인 경우가 많다(후행 448건 중 대부분).
_EDGE_JUNK = r"""|[]_?$><~`^\!@#&*=+{};:"'‘’“”"""


def _strip_edge(s: str) -> str:
    # NFKC: ㈜→(주), ㎎→mg, 전각→반각 등 합자·폭 변형을 풀어서 비교한다.
    # 2026-08-04 실증: GT "㈜이든파마" vs 모델 "(주이든파마" - 같은 표기가 다른
    # 문자 코드라는 이유로 13크롭이 통째로 '못 읽음' 후보 1위에 올랐다.
    import unicodedata
    s = unicodedata.normalize("NFKC", s)
    # ㈜는 NFKC 가 (주) 로 풀므로 인코딩 차이까지만 등가로 본다.
    # 모델이 닫는 괄호를 빠뜨린 "(주" 는 실제 한 글자 삭제 = 인식 결함으로 남긴다(학습 대상).
    return "".join(s.split()).strip(_EDGE_JUNK)


def same_text(gt: str, pred: str) -> bool:
    """손실 집계용 비교 - 공백 차이는 같은 것으로 본다.

    ★2026-08-04 실측: '잃어버림' 4,084 중 1,961(48%)이 글자는 전부 맞고 띄어쓰기만
      다른 건이었다("더모픽스크림 30g" -> "더모픽스크림30g").
      ①GT(구글 OCR 원본)의 띄어쓰기가 인쇄를 정확히 반영한다는 보장이 없고
       (모델이 없는 공백을 넣은 반대 사례도 나온다),
      ②품명은 마스터 매칭(유사도)으로 넘어가므로 공백 하나로 매칭이 갈리지 않는다.
      제품 기준으로 이미 성공한 건을 실패로 세면 앵커 실험의 신호가 흐려진다.
    ★앞뒤 잡문자(| [ ] _ ? …)도 같이 뺀다. 이 GT 는 상대 시스템의 <원문 OCR>이라
      표 세로선을 글자로 읽은 "|스파로드정" 같은 오염이 1.9% 섞여 있다. 우리 모델이
      선을 안 읽은 것은 오답이 아니라 더 정확히 읽은 것이다.
    ★단, 소생 판정(demo_report)은 엄격한 완전일치를 그대로 쓴다.
    """
    return _strip_edge(gt) == _strip_edge(pred)


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

    keep = basis_keep()
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
        if keep is not None and rel not in keep:
            continue
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
            if keep is not None and rel not in keep:
                continue
            gt = bal.get(rel)
            if gt and os.path.exists(os.path.join(CORPUS_DIR, rel)):
                rows.append((rel, gt))
    if limit:
        rows = rows[:limit]
    return rows


def _thumbs(rels: list[str], max_n: int = 3) -> list[str]:
    """후보 크롭 실물을 base64 JPEG 로 - 표에서 눈으로 GT/오독을 판단하는 근거.
    마스터 사전 같은 간접 증거는 쓰지 않는다: 사전에 없는 정상 품명이 많고(포장 변형·
    비의약품), 사전에 있어도 그 크롭에 그 글자가 인쇄됐다는 보장이 없다. 실물이 유일한 증거."""
    import base64
    import io as _io
    out: list[str] = []
    try:
        from PIL import Image
    except ImportError:
        return out
    for rel in rels[:max_n]:
        p = os.path.join(CORPUS_DIR, rel)
        if not os.path.exists(p):
            continue
        try:
            im = Image.open(p).convert("RGB")
            if im.height > 34:
                im = im.resize((max(1, im.width * 34 // im.height), 34))
            buf = _io.BytesIO()
            im.save(buf, "JPEG", quality=75)
            out.append(base64.b64encode(buf.getvalue()).decode())
        except OSError:
            continue
    return out


def _load_scan(path: str) -> dict[str, dict]:
    """스캔 결과 로드 - 확정 목록(basis_keep)이 있으면 그 크롭만.
    옛 스캔 파일에는 조각 크롭 판독이 그대로 남아 있어 여기서 걸러야
    새 스캔(처음부터 45,617장만 읽음)과 같은 모집단이 된다."""
    out: dict[str, dict] = {}
    if not path or not os.path.exists(path):
        return out
    keep = basis_keep()
    for ln in open(path, encoding="utf-8"):
        try:
            d = json.loads(ln)
        except json.JSONDecodeError:
            continue
        p = d.get("path")
        if p and (keep is None or p in keep):
            out[p] = d
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
    ap.add_argument("--use-base", action="store_true",
                    help="파인튜닝 모델 대신 official base 로 스캔 - 최초 1회 기준선 만들기")
    ap.add_argument("--model-dir", default=None,
                    help="스캔할 export inference 디렉터리. 미지정이면 기존처럼 "
                         "eval/finetune/output 의 최신 export 를 사용한다")
    ap.add_argument("--scan-tag", default=None,
                    help="스캔 파일 이름(기본: --run-tag). base 기준선은 000_base 권장 "
                         "- 파일명 정렬이 곧 시간 순서라 000_ 이 항상 첫 기준선이 된다")
    ap.add_argument("--progress-every", type=int, default=2000,
                    help="진행 로그를 찍는 간격(크롭 수). 기본 2,000")
    ap.add_argument("--from-scan", action="store_true",
                    help="이미 있는 스캔 파일을 그대로 쓰고 판독은 건너뜀 - 대조 상대(--prev-scan)만 "
                         "바꿔 후보를 다시 뽑을 때. GPU 안 씀")
    ap.add_argument("--scan-only", action="store_true",
                    help="스캔만 하고 잃음/못읽음 후보 계산은 건너뜀(base 기준선용)")
    args = ap.parse_args()
    run_tag = _report_id(args.run_tag)
    scan_tag = args.scan_tag or run_tag
    already = {t.strip().replace(" ", "") for t in args.exclude.split(",") if t.strip()}
    already |= gt_bad()          # 실물 확인된 GT 오독은 후보로 다시 올라오지 않게
    scan_path = os.path.join(SCANS_DIR, f"{scan_tag}.jsonl")
    # ★덮어쓰기 금지 — 판독(20분) 시작 전에 막는다.
    #  모델 선택은 output/best_accuracy(=마지막 학습본)를 따르므로, 나중에 옛 --run-tag 로
    #  다시 돌리면 '그 단계 모델' 이름표를 단 채 최신 모델 판독이 저장돼 다음 대조가 틀어진다.
    if os.path.exists(scan_path) and not args.from_scan:
        raise SystemExit(
            f"★{scan_path} 가 이미 있습니다 - 그 단계 모델의 판독 결과이므로 덮어쓰지 않습니다.\n"
            f"  정말 다시 만들 거라면 먼저 지우세요:  rm {scan_path}\n"
            f"  (단, 그 사이 다른 파인튜닝을 돌렸다면 지금 모델은 그 단계 모델이 아닙니다)")

    if args.from_scan:
        # 판독 결과를 그대로 재사용 - 대조 상대만 바꿔 후보를 다시 뽑는 경로(GPU 0분).
        if not os.path.exists(scan_path):
            raise SystemExit(f"--from-scan 인데 스캔 파일이 없습니다: {scan_path}")
        cur = _load_scan(scan_path)
        rows = [(p, r["gt"]) for p, r in cur.items()]
        preds = [r["pred"] for r in cur.values()]
        print(f"[스캔] 기존 결과 재사용: {scan_path} ({len(rows):,}장) - 판독 건너뜀")
    else:
        print("[스캔] 기준셋 품명 크롭 목록 만드는 중 (ledger 1.7GB 훑기, 1~3분)…", flush=True)
        rows = basis_crops(args.min_match, args.limit)
    if not rows:
        raise SystemExit("기준셋 품명 크롭을 찾지 못했습니다(코퍼스/replay_sources 확인)")

    if not args.from_scan:
        if args.use_base and args.model_dir:
            raise SystemExit("--use-base 와 --model-dir 는 함께 쓸 수 없습니다")
        who = ("official base" if args.use_base else
               (f"지정 모델({args.model_dir})" if args.model_dir else "이번 파인튜닝 모델"))
        print(f"[스캔] 기준셋 품명 크롭 {len(rows):,}장 — {who} 로 판독")
        try:
            from paddlex import create_model
        except ImportError:
            from paddlex.inference import create_model  # type: ignore
        if args.use_base:
            model = create_model(BASE_MODEL)          # 기준선: 파인튜닝 없는 원본
        else:
            ft_dir = args.model_dir or find_ft_inference()
            if not ft_dir:
                raise SystemExit("파인튜닝 inference 디렉터리 없음 — export 먼저")
            if not os.path.isdir(ft_dir):
                raise SystemExit(f"지정한 inference 디렉터리가 없습니다: {ft_dir}")
            model = create_model(BASE_MODEL, ft_dir)
        # 8만 장을 한 번에 넘기면 10분 넘게 아무 출력이 없다 → 덩어리로 나눠 진행률을 찍는다.
        import time
        paths = [os.path.join(CORPUS_DIR, r) for r, _ in rows]
        chunk = max(500, args.progress_every)
        preds = []
        t0 = time.time()
        for i in range(0, len(paths), chunk):
            preds += predict_all(model, paths[i:i + chunk])
            done = len(preds)
            ok_so_far = sum(1 for p, (_, gt) in zip(preds, rows) if p.strip() == gt.strip())
            el = time.time() - t0
            eta = el / done * (len(paths) - done) if done else 0
            print(f"[스캔] {done:,}/{len(paths):,} ({100.0 * done / len(paths):5.1f}%) · "
                  f"정답 {ok_so_far:,} ({100.0 * ok_so_far / done:.1f}%) · "
                  f"경과 {el / 60:.1f}분 · 남은 예상 {eta / 60:.1f}분", flush=True)

        os.makedirs(SCANS_DIR, exist_ok=True)
        # 4~5만 장 스캔 도중 중단된 반쪽 jsonl 이 recount 의 공통집합을 깨뜨리지 않도록,
        # 같은 디렉터리의 임시 파일을 완성한 뒤에만 최종 이름으로 원자 교체한다.
        scan_tmp = scan_path + f".tmp.{os.getpid()}"
        try:
            with open(scan_tmp, "w", encoding="utf-8") as f:
                for (rel, gt), p in zip(rows, preds):
                    f.write(json.dumps({"path": rel, "gt": gt, "pred": p,
                                        "ok": p.strip() == gt.strip()}, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(scan_tmp, scan_path)
        finally:
            if os.path.exists(scan_tmp):
                os.remove(scan_tmp)
        ok_n = sum(1 for p, (_, gt) in zip(preds, rows) if p.strip() == gt.strip())
        print(f"[스캔] 저장: {scan_path}  "
              f"(정답 {ok_n:,} / {len(rows):,} = {100.0 * ok_n / len(rows):.1f}%)")
        if args.scan_only:
            print("[스캔] --scan-only: 후보 계산 없이 종료(기준선 저장 완료)")
            return 0

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

    lost = defaultdict(lambda: {"n": 0, "hit": 0, "wrong": {}, "paths": []})
    unread = defaultdict(lambda: {"n": 0, "hit": 0, "wrong": {}, "paths": []})
    _bad = gt_bad()
    for (rel, gt), p in zip(rows, preds):
        if gt.replace(" ", "") in _bad:
            continue                   # GT 오독 확정 건 - 모델 잘못이 아니므로 집계 제외
        ok = same_text(gt, p)          # 공백 차이는 실패로 세지 않는다
        u = unread[gt]
        u["n"] += 1
        if not ok:
            u["hit"] += 1
            u["wrong"][p.strip() or "(빈칸)"] = u["wrong"].get(p.strip() or "(빈칸)", 0) + 1
            if len(u["paths"]) < 3:
                u["paths"].append(rel)
        pv = prev.get(rel)
        if pv and same_text(pv.get("gt") or "", pv.get("pred") or ""):
            l = lost[gt]
            l["n"] += 1
            if not ok:
                l["hit"] += 1
                l["wrong"][p.strip() or "(빈칸)"] = l["wrong"].get(p.strip() or "(빈칸)", 0) + 1
                if len(l["paths"]) < 3:
                    l["paths"].append(rel)

    def _rank(stat) -> list[dict]:
        out = []
        for gt, s in stat.items():
            if (gt.replace(" ", "") in already or s["n"] < args.min_count
                    or not s["hit"] or not is_item_name(gt)):
                continue
            out.append({"name": gt, "crops": s["n"], "hits": s["hit"],
                        "rate": round(100.0 * s["hit"] / s["n"], 1),
                        "wrong": sorted(s["wrong"].items(), key=lambda x: -x[1])[:3],
                        "crops64": _thumbs(s["paths"])})
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
