"""llm_runner — VLM(vLLM OpenAI 호환 서버)으로 문서 이미지를 돌려 run_batch 모양으로 저장한다.

핵심 계약: 출력이 run_batch 와 같은 레이아웃이면 채점은 기존 경로를 그대로 탄다.
    eval/runs/<run>/samples/<src>.json   ← run_batch 레코드와 같은 키
    eval/runs/<run>/vlm_inputs/<src>.jpg ← 서버로 보낸 그 이미지(카드 셋째 판 재료)
    이후: python eval/compare_run.py --ts <run>  →  compare/  →  compare_cross.py

별도 채점기를 만들지 않는다 - 셀 신원이 어긋나면 교차 2×2 네 칸이 의미를 잃는다.

프롬프트는 eval/LLM/prompt_v1.md 의 ## SYSTEM / ## USER 절을 그대로 쓴다(룰 이식 v1).
--no-fulltext 는 스모크 50장 A/B 용 - full_text 요구만 빼고 나머지는 동일하다.

셋째 판(모델 전처리 후 = 프로세서가 리사이즈한 뷰)은 서버 안에서 일어나므로 클라이언트가
직접 얻을 수 없다. v1 은 보낸 이미지를 저장하고, 프로세서 뷰 재현은 AWS 에서 모델
preprocessor 설정으로 별도 산출한다(러너 밖).

CLI (AWS):
    python eval/llm_runner.py --server http://localhost:8000/v1 --model Qwen/Qwen3-VL-8B-Instruct \
        --list eval/LLM/sample_500.txt --run vlm_qwen3_500
로컬 스모크(서버 없이 형식 검증):
    python eval/llm_runner.py --canned eval/LLM/canned_response.json --list <2장> --run vlm_smoke
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(HERE, "runs")
PROMPT_PATH = os.path.join(HERE, "LLM", "prompt_v1.md")

DOC_FIELDS = ["supplierCompany", "supplierBizNumber", "supplierAddress",
              "buyerCompany", "buyerBizNumber", "buyerAddress",
              "issueDate", "taxType", "supplyAmount", "taxAmount",
              "totalAmount", "discountAmount"]
ROW_FIELDS = ["rowIndex", "itemName", "spec", "quantity", "unitPrice",
              "amount", "manufacturingNo", "expiryDate", "insuranceCode"]


# ---------------------------------------------------------------- 프롬프트

def load_prompt(path: str, fulltext: bool) -> tuple[str, str]:
    text = open(path, encoding="utf-8").read()
    sys_m = re.search(r"^## SYSTEM\n(.*?)^## USER", text, re.S | re.M)
    usr_m = re.search(r"^## USER.*?\n(.*?)^---\n\n## 러너 계약", text, re.S | re.M)
    if not (sys_m and usr_m):
        raise SystemExit(f"프롬프트에서 SYSTEM/USER 절을 찾지 못했다: {path}")
    system, user = sys_m.group(1).strip(), usr_m.group(1).strip()
    if not fulltext:
        # A/B 변형: full_text 가 걸린 줄(스키마 키 + 규칙 10)을 통째로 뺀다
        user = "\n".join(ln for ln in user.split("\n") if "full_text" not in ln)
    return system, user


# ---------------------------------------------------------------- 호출

def call_vlm(server: str, model: str, system: str, user: str, image_path: str,
             timeout: float, max_tokens: int, retry_note: str = "") -> tuple[str, float]:
    with open(image_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user + retry_note},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]},
        ],
    }
    req = urllib.request.Request(
        server.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ms = (time.time() - t0) * 1000
    return data["choices"][0]["message"]["content"], ms


def parse_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("JSON 이 없다")
    return json.loads(t[i:j + 1])


def source_name(path: str) -> str:
    """테스트셋 sourceFile 이름 유도: .../images_replay/2501/10006/NAME.jpg -> 2501__10006__NAME.jpg
    (run_batch·GT 매니페스트와 같은 규약이어야 compare_run 이 GT 를 찾는다)."""
    norm = path.replace("\\", "/")
    m = re.search(r"images_replay/([^/]+)/([^/]+)/([^/]+)$", norm)
    if m:
        return f"{m.group(1)}__{m.group(2)}__{m.group(3)}"
    return os.path.basename(path)


# ---------------------------------------------------------------- 레코드

def to_record(source_file: str, image_path: str, resp: dict, ms: float,
              model: str, raw_len: int) -> dict:
    """run_batch 레코드와 같은 모양으로 - compare_run 이 그대로 읽는다."""
    fields = {k: str((resp.get("documentFields") or {}).get(k) or "") for k in DOC_FIELDS}
    rows = []
    for i, r in enumerate(resp.get("tableRows") or [], start=1):
        if not isinstance(r, dict):
            continue
        row = {k: str(r.get(k) or "") for k in ROW_FIELDS}
        row["rowIndex"] = row["rowIndex"] or str(i)
        rows.append(row)
    fields["tableRows"] = rows
    fields["rowCount"] = len(rows)
    fields["tableDetected"] = "Y" if rows else "N"
    fields["tableMeta"] = {"source": "vlm", "model": model, "rowCount": len(rows)}
    return {
        "sourceFile": source_file,
        "imagePath": image_path,
        "pageCount": 1,
        "multiPage": False,
        "status": "ok",
        "httpStatus": 200,
        "extractionSourceRaw": "vlm",
        "extractionPath": "vlm",
        "rowCount": len(rows),
        "tableDetected": fields["tableDetected"],
        "documentFields": fields,
        "fullText": str(resp.get("full_text") or ""),
        "vlm": {"model": model, "rawChars": raw_len},
        "clientMs": round(ms, 1),
        "error": None,
    }


# ---------------------------------------------------------------- 메인

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://localhost:8000/v1")
    ap.add_argument("--model", default="")
    ap.add_argument("--list", required=True,
                    help="이미지 경로 목록 txt (eval/ 기준 상대 or 절대), 한 줄 하나")
    ap.add_argument("--run", required=True, help="eval/runs/ 아래 run 디렉터리 이름")
    ap.add_argument("--prompt", default=PROMPT_PATH)
    ap.add_argument("--no-fulltext", action="store_true", help="A/B: full_text 요구 제거")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--canned", help="서버 대신 이 JSON 응답을 모든 이미지에 사용(로컬 형식 스모크)")
    args = ap.parse_args()

    system, user = load_prompt(args.prompt, fulltext=not args.no_fulltext)

    paths = []
    for line in open(args.list, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line if os.path.isabs(line) else os.path.join(HERE, line))
    if args.limit:
        paths = paths[:args.limit]

    run_dir = os.path.join(RUNS_DIR, args.run)
    samples_dir = os.path.join(run_dir, "samples")
    inputs_dir = os.path.join(run_dir, "vlm_inputs")
    os.makedirs(samples_dir, exist_ok=True)
    os.makedirs(inputs_dir, exist_ok=True)

    canned = json.load(open(args.canned, encoding="utf-8")) if args.canned else None
    ok = fail = 0
    t_start = time.time()

    for path in paths:
        src = source_name(path)
        out = os.path.join(samples_dir, src + ".json")
        if os.path.exists(out):        # resume: 있는 건 건너뛴다
            ok += 1
            continue
        try:
            if canned is not None:
                resp, ms, raw_len = canned, 0.0, len(json.dumps(canned))
            else:
                raw, ms = call_vlm(args.server, args.model, system, user, path,
                                   args.timeout, args.max_tokens)
                raw_len = len(raw)
                try:
                    resp = parse_json(raw)
                except Exception:
                    raw, ms2 = call_vlm(args.server, args.model, system, user, path,
                                        args.timeout, args.max_tokens,
                                        retry_note="\n\nJSON 하나만, 다른 텍스트 없이 출력하라.")
                    ms += ms2
                    resp = parse_json(raw)
            rec = to_record(src, path, resp, ms, args.model, raw_len)
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, ensure_ascii=False, indent=2)
            with open(path, "rb") as sfh, open(os.path.join(inputs_dir, src), "wb") as dfh:
                dfh.write(sfh.read())   # 보낸 이미지 그대로(프로세서 뷰는 AWS 별도 산출)
            ok += 1
        except Exception as exc:            # noqa: BLE001 - 한 장 실패로 배치 죽이지 않는다
            fail += 1
            with open(os.path.join(run_dir, "errors.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"sourceFile": src, "error": str(exc)},
                                    ensure_ascii=False) + "\n")

    elapsed = time.time() - t_start
    meta = {"run": args.run, "model": args.model, "prompt": os.path.basename(args.prompt),
            "fulltext": not args.no_fulltext, "docs": len(paths), "ok": ok, "fail": fail,
            "elapsedSec": round(elapsed, 1),
            "docsPerHour": round(ok / elapsed * 3600, 1) if elapsed > 0 and ok else None}
    with open(os.path.join(run_dir, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
