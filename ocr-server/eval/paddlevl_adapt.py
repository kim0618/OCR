"""paddlevl_adapt — PaddleOCR-VL 의 문서 파싱 결과를 우리 파서 입력으로 바꾸고, 파서를 태워
run_batch 레이아웃(samples/)으로 저장한다. GPU·AWS 불필요.

왜 이런 모양인가
----------------
Qwen·InternVL 은 이미지에서 바로 우리 JSON 을 낸다(인식 + 파서를 한꺼번에 대체).
PaddleOCR-VL 은 **문서를 구조로 재현**할 뿐이라 "어느 칸이 공급자 상호인가"를 모른다.
그래서 이 모델은 **인식 층만** 갈아끼우는 실험이고, 그 뒤는 우리 파서가 그대로 받는다:

    PaddleOCR-VL parsing_res_list  →  [이 스크립트]  →  ocr_lines_raw 스냅샷
                                   →  replay_free.replay_one (우리 free 파서)
                                   →  samples/<src>.json  (run_batch 와 같은 키)

이렇게 하면 채점기(compare_run)·후처리 통일(llm_derive_run)·계획서 채우기(llm_plan_fill)를
Qwen 때와 **한 글자도 바꾸지 않고** 그대로 탄다. 좌표가 있으니 Qwen 이 못 쓴 좌표 기반 룰
11개도 살아난다 - 그게 이 경로의 유일한 존재 이유다.

입력(모델이 낸 것, AWS 에서 회수)
    <parse-dir>/<src>.json = {"image_size": [w,h], "parsing_res_list": [
        {"block_label": "text"|"table"|..., "block_bbox": [x0,y0,x1,y1], "block_content": "..."}, ...]}

좌표 합성
    text  블록 - 줄 단위로 쪼개 bbox 안에 세로로 균등 배치
    table 블록 - HTML 을 행×열 격자로 보고 bbox 를 균등 분할(모델이 셀 좌표를 주지 않는다)
    격자는 근사지만 우리 컬럼 매칭은 x 중심으로 도는 규칙이라 이 정도면 붙는다.
    ⚠️ 셀 좌표가 진짜가 아니라는 사실은 결과를 읽을 때 늘 같이 말해야 한다.

    python eval/paddlevl_adapt.py --parse eval/runs/vlm_paddlevl_500r/parse --run vlm_paddlevl_500r
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from replay_compare import replay_dispatch  # noqa: E402

CONF = 0.99            # 모델이 신뢰도를 주지 않는다. 파서는 값만 보고 쓰지 않는다.
CONTEXT = {            # 071 스냅샷(thin·free 경로)과 같은 모양
    "templateMode": False,
    "requestTemplateMode": "unstructured",
    "isUnstructuredTemplate": True,
    "template_id": "",
    "selectedTemplateId": "",
    "tableExpectedColumns": None,
    "tableBounds": None,
    "columnGuides": None,
}

TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")


def poly(x0: float, y0: float, x1: float, y1: float) -> list:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def clean(s: str) -> str:
    return html.unescape(TAG.sub(" ", s or "")).replace("\xa0", " ").strip()


def text_lines(content: str, bbox: list) -> list:
    """텍스트 블록 - 줄마다 한 라인. 높이를 균등 분할해 세로 순서를 보존한다."""
    rows = [r for r in (content or "").split("\n") if r.strip()]
    if not rows:
        return []
    x0, y0, x1, y1 = bbox
    h = (y1 - y0) / len(rows)
    out = []
    for i, r in enumerate(rows):
        t = clean(r)
        if t:
            out.append([poly(x0, y0 + i * h, x1, y0 + (i + 1) * h), t, CONF])
    return out


def table_lines(content: str, bbox: list) -> list:
    """표 블록 - HTML 격자를 bbox 에 균등 분할해 셀마다 한 라인.
    모델이 셀 좌표를 주지 않으므로 합성이다. colspan/rowspan 은 무시한다(명세서 표엔 거의 없다)."""
    rows = [TD.findall(r) for r in TR.findall(content or "")]
    rows = [r for r in rows if r]
    if not rows:
        return text_lines(content, bbox)          # 표로 안 읽히면 글자라도 살린다
    x0, y0, x1, y1 = bbox
    ncol = max(len(r) for r in rows)
    cw, rh = (x1 - x0) / max(1, ncol), (y1 - y0) / len(rows)
    out = []
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            t = clean(cell)
            if t:
                out.append([poly(x0 + j * cw, y0 + i * rh, x0 + (j + 1) * cw, y0 + (i + 1) * rh), t, CONF])
    return out


def _row_keys(cells: list) -> tuple[list, int]:
    """한 행을 우리 정규 키로 옮긴다. (키 목록, 알아본 칸 수)"""
    try:
        from extractors.invoice_statement import _EXPECTED_COLUMN_ALIASES as AL
    except Exception:
        return [], 0
    norm = lambda t: re.sub(r"\s+", "", t or "").lower()
    lut = {norm(v): k for k, vs in AL.items() for v in vs}
    keys, hit = [], 0
    for i, c in enumerate(cells):
        k = lut.get(norm(clean(c)))
        if k:
            hit += 1
        keys.append(k or "_col%d" % i)
    return keys, hit


def find_header(rows: list) -> tuple[int, list] | tuple[None, None]:
    """품목표 머리글이 몇 번째 행인가.

    ★모델은 헤더부(공급자·공급받는자 등록번호…)와 품목표를 **한 덩어리 표**로 낸다
      (2026-09-17 실측: rowspan 으로 묶인 한 표 안에 둘 다 들어 있다).
      그래서 첫 행만 보면 못 찾는다 - 표 중간에서 찾아야 하고,
      그 앞은 품목이 아니라 문서 머리글이므로 글자로만 넣어야 한다.
    """
    for i, cells in enumerate(rows[:12]):          # 머리글이 12행보다 아래 있는 경우는 없다
        if len(cells) < 3:
            continue
        keys, hit = _row_keys(cells)
        if hit >= max(2, len(cells) // 2):
            return i, keys
    return None, None


def grid_lines(rows: list, bbox: list, ncol: int, skip_head: bool = False) -> list:
    """머리글을 뺀 표 본문을 같은 격자(ncol)에 올린다. 행 높이는 머리글 한 줄만큼 내려서 잡는다."""
    if not rows:
        return []
    x0, y0, x1, y1 = bbox
    nrow = len(rows) + (1 if skip_head else 0)
    cw, rh = (x1 - x0) / max(1, ncol), (y1 - y0) / nrow
    off = 1 if skip_head else 0
    out = []
    for i, row in enumerate(rows):
        for j, cell in enumerate(row[:ncol]):
            t = clean(cell)
            if t:
                out.append([poly(x0 + j * cw, y0 + (i + off) * rh, x0 + (j + 1) * cw, y0 + (i + off + 1) * rh), t, CONF])
    return out


def to_snapshot(parse: dict) -> dict:
    # block_order 가 키는 있는데 값이 None 인 블록이 섞여 온다(2026-09-17 실측) -
    # .get(k, default) 는 그 경우 None 을 돌려줘 정렬에서 TypeError 가 난다.
    def order(b):
        for k in ("block_order", "block_id"):
            v = b.get(k)
            if isinstance(v, (int, float)):
                return v
        return 1e9
    blocks = sorted(parse.get("parsing_res_list") or [], key=order)
    # 품목표 = 가장 큰 표 블록 하나. 나머지 표는 글자로만 넣는다(합계표·안내문 등).
    tables = [b for b in blocks
              if (b.get("block_label") or "").lower() == "table" or "<t" in (b.get("block_content") or "").lower()]
    main = max(tables, key=lambda b: len(b.get("block_content") or ""), default=None)

    lines, ctx = [], dict(CONTEXT)
    for b in blocks:
        bbox = [float(v) for v in (b.get("block_bbox") or [0, 0, 0, 0])]
        content = b.get("block_content") or ""
        if b is main:
            rows = [TD.findall(r) for r in TR.findall(content)]
            rows = [r for r in rows if r]
            hi, keys = find_header(rows)
            if keys:
                if hi:
                    # 머리글 위쪽(문서 헤더부)은 품목이 아니다 - 표 bbox 를 행 비율로 갈라
                    # 위쪽은 글자로만 넣는다. 안 가르면 그게 전부 품목 행이 된다(+22행 사고).
                    x0, y0, x1, y1 = bbox
                    ysplit = y0 + (y1 - y0) * hi / max(1, len(rows))
                    head_txt = chr(10).join(" ".join(clean(c) for c in r if clean(c)) for r in rows[:hi])
                    lines += text_lines(head_txt, [x0, y0, x1, ysplit])
                    bbox = [x0, ysplit, x1, y1]
                    rows = rows[hi:]
                # ★모델이 표를 표로 주므로 파서가 컬럼을 추론할 이유가 없다.
                #   격자를 그대로 넘겨 헤더 검출 경로를 건너뛴다(T-6j colGuides).
                #   합성 GT 로도 열이 밀리던 문제가 여기서 잡힌다.
                x0, y0, x1, y1 = bbox
                cw = (x1 - x0) / max(1, len(keys))
                ctx["tableExpectedColumns"] = {"required": keys, "optional": []}
                ctx["tableBounds"] = {"xMin": x0, "xMax": x1, "yMin": y0, "yMax": y1, "source": "paddlevl"}
                ctx["columnGuides"] = [x0 + i * cw for i in range(1, len(keys))]
                # ⚠️ 머리글을 빼면 안 된다 - free 경로는 컬럼 가이드를 보지 않고 머리글로 컬럼을 찾는다
                #    (가이드는 fallback/템플릿 경로만 읽는다). 빼면 5칸 scaffold 로 떨어져 열이 밀린다.
                lines += grid_lines(rows, bbox, len(keys))
                continue
        if (b.get("block_label") or "").lower() == "table" or "<t" in content.lower():
            lines += table_lines(content, bbox)
        else:
            lines += text_lines(content, bbox)
    w, h = (parse.get("image_size") or [0, 0])[:2]
    return {
        "schemaVersion": "ocr-free-input.v1",
        "ocr_lines_raw": lines,
        # full_text 는 모델이 준 글자 그대로. Qwen 경로와 달리 여기선 공짜로 얻는다
        # (structure/recognition 실패 분해가 이 모델에서는 가능하다).
        "full_text": "\n".join(l[1] for l in lines),
        "image_size": [int(w), int(h)],
        "doc_type": "invoice_statement",
        "context": ctx,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parse", required=True, help="모델이 낸 파싱 JSON 디렉터리")
    ap.add_argument("--run", required=True, help="eval/runs/ 아래 만들 run 이름")
    ap.add_argument("--model", default="PaddlePaddle/PaddleOCR-VL")
    ap.add_argument("--elapsed-sec", type=float, default=0.0, help="AWS run 소요(원장용)")
    ap.add_argument("--keep-snapshots", action="store_true", help="스냅샷도 남긴다(디버깅)")
    a = ap.parse_args()

    run_dir = os.path.join(HERE, "runs", a.run)
    sam_dir = os.path.join(run_dir, "samples")
    os.makedirs(sam_dir, exist_ok=True)
    snap_dir = os.path.join(run_dir, "snapshots")
    if a.keep_snapshots:
        os.makedirs(snap_dir, exist_ok=True)

    def src_of(parse: dict, fallback: str) -> str:
        """sourceFile 은 image_path 에서 유도한다(llm_runner.source_name 과 같은 규약).
        파싱 파일 이름만 쓰면 2605__437387__ 같은 앞부분이 없어 compare_run 이 GT 를 못 찾는다."""
        norm = (parse.get("image_path") or "").replace("\\", "/")
        m = re.search(r"images_replay/([^/]+)/([^/]+)/([^/]+)$", norm)
        if m:
            return "%s__%s__%s" % (m.group(1), m.group(2), m.group(3))
        base = os.path.basename(norm) or fallback
        if "/runs/" in norm and base.endswith(".jpg.jpg"):
            base = base[:-4]
        return base or fallback

    files = sorted(f for f in os.listdir(a.parse) if f.endswith(".json"))
    ok = fail = 0
    for fn in files:
        src = fn[:-5]
        try:
            parse = json.load(io.open(os.path.join(a.parse, fn), encoding="utf-8"))
            src = src_of(parse, src)
            snap = to_snapshot(parse)
            if a.keep_snapshots:
                with io.open(os.path.join(snap_dir, fn), "w", encoding="utf-8") as fh:
                    json.dump(snap, fh, ensure_ascii=False)
            df, path = replay_dispatch(snap)
            rows = (df or {}).get("tableRows") or []
            rec = {
                "sourceFile": src,
                "imagePath": parse.get("image_path", ""),
                "pageCount": 1, "multiPage": False,
                "status": "ok", "httpStatus": 200,
                "extractionSourceRaw": "paddlevl", "extractionPath": path,
                "rowCount": len(rows),
                "tableDetected": "Y" if rows else "N",
                "documentFields": df,
                "fullText": snap["full_text"],
                "paddlevl": {"model": a.model, "blocks": len(parse.get("parsing_res_list") or []),
                             "ocrLines": len(snap["ocr_lines_raw"])},
                "clientMs": 0.0, "error": None,
            }
            ok += 1
        except Exception as exc:                                  # noqa: BLE001
            rec = {"sourceFile": src, "status": "error", "error": str(exc),
                   "documentFields": {}, "rowCount": 0, "tableDetected": "N",
                   "extractionSourceRaw": "paddlevl", "extractionPath": "free"}
            fail += 1
            print("  ERR %s  %s" % (src[:44], exc))
        with io.open(os.path.join(sam_dir, src + ".json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)

    meta = {"run": a.run, "model": a.model, "prompt": "(파서 재사용 - 프롬프트 없음)",
            "fulltext": True, "docs": len(files), "ok": ok, "fail": fail,
            "elapsedSec": a.elapsed_sec,
            "docsPerHour": round(ok / a.elapsed_sec * 3600, 1) if a.elapsed_sec else None}
    with io.open(os.path.join(run_dir, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False))
    print("→ %s  (파서 재생 %d장 · 실패 %d)" % (sam_dir, ok, fail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
