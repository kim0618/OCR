"""finetune_adopt — 파인튜닝 결과를 '채택'해서 트리의 줄기로 승격.

파인튜닝은 output/(스크래치)에 결과를 낸다. 게이트를 통과해 채택하기로 하면
이 스크립트가 그걸 안정 위치(adopted/)로 올리고, 버전 스냅샷을 남기고, 계보를
기록한다. 이후:
  - main.py 는 adopted/inference 를 rec 로 로드(채택된 모델만 서비스에 반영)
  - run-finetune.sh --from-adopted 는 adopted/best_accuracy.pdparams 를 base 로
    이어받아 다음 라운드를 학습(트리 줄기 연장)

    # 방금 돌린 파인튜닝(output/)을 v5 로 채택, 부모는 official
    python eval/finetune_adopt.py --version v5

    # 채택한 v5 를 이어받아 학습한 결과를 v6 로 채택(부모=v5)
    python eval/finetune_adopt.py --version v6 --parent v5

버전을 안 주면 날짜시각(YYMMDD_HHMM)으로 자동 태깅. parent 를 안 주면 현재
adopted/META.json 의 version(직전 채택본)을 부모로 잇는다(없으면 official).

산출:
  eval/finetune/adopted/inference/            main.py 가 로드하는 서비스 모델
  eval/finetune/adopted/best_accuracy.pdparams --from-adopted 이어받기 base
  eval/finetune/adopted/META.json             {version,parent,adopted_at,...}
  eval/finetune/versions/<version>/           그 버전 스냅샷(트리 되짚기용)
  RUN_HISTORY.jsonl 에 adopt 이벤트 append (트리 화면 ★ 표시)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
FT = os.path.join(HERE, "finetune")
OUT = os.path.join(FT, "output")
ADOPTED = os.path.join(FT, "adopted")
VERSIONS = os.path.join(FT, "versions")


def _find(root: str, name: str) -> str | None:
    """output 하위에서 name(inference 디렉터리 / *.pdparams) 최우선 후보를 찾음."""
    best_first = os.path.join(root, "best_accuracy")
    for base in (best_first, root):
        if not os.path.isdir(base):
            continue
        cand = os.path.join(base, name)
        if os.path.exists(cand):
            return cand
    # 재귀 폴백
    hits = []
    for dp, dns, fns in os.walk(root):
        if name.endswith(".pdparams"):
            if name in fns:
                hits.append(os.path.join(dp, name))
        elif name in dns:
            hits.append(os.path.join(dp, name))
    hits.sort(key=lambda p: (0 if "best_accuracy" in p else 1, len(p)))
    return hits[0] if hits else None


def _prev_version() -> str | None:
    meta = os.path.join(ADOPTED, "META.json")
    if os.path.exists(meta):
        try:
            return json.load(open(meta, encoding="utf-8")).get("version")
        except Exception:
            return None
    return None


def adopt(version: str | None, parent: str | None) -> int:
    if not os.path.isdir(OUT):
        print(f"[adopt] output 없음: {OUT} — 먼저 파인튜닝을 돌리세요")
        return 1
    now = datetime.datetime.now()
    version = version or now.strftime("v%y%m%d_%H%M")
    # parent 미지정 → 직전 채택본을 이어받은 것으로 간주(트리 줄기), 없으면 official
    if parent is None:
        parent = _prev_version() or "official"

    inf = _find(OUT, "inference")
    pdp = _find(OUT, "best_accuracy.pdparams") or _find(OUT, "latest.pdparams")
    if not inf:
        print(f"[adopt] inference 디렉터리를 output 에서 못 찾음 — export 됐는지 확인")
        return 1

    # 1) 버전 스냅샷 (되짚기용, 덮어쓰기 방지)
    vdir = os.path.join(VERSIONS, version)
    if os.path.exists(vdir):
        print(f"[adopt] 이미 존재하는 버전: {version} (다른 --version 쓰거나 삭제 후 재시도)")
        return 1
    os.makedirs(vdir, exist_ok=True)
    shutil.copytree(inf, os.path.join(vdir, "inference"))
    if pdp:
        shutil.copy2(pdp, os.path.join(vdir, "best_accuracy.pdparams"))

    # 2) adopted/ 갱신 (main.py + --from-adopted 이 보는 안정 위치)
    if os.path.isdir(ADOPTED):
        shutil.rmtree(ADOPTED)
    os.makedirs(ADOPTED, exist_ok=True)
    shutil.copytree(inf, os.path.join(ADOPTED, "inference"))
    if pdp:
        shutil.copy2(pdp, os.path.join(ADOPTED, "best_accuracy.pdparams"))

    meta = {
        "version": version,
        "parent": parent,
        "adopted_at": now.strftime("%Y-%m-%d %H:%M"),
        "inference": os.path.relpath(os.path.join(ADOPTED, "inference"), HERE),
        "has_checkpoint": bool(pdp),
    }
    json.dump(meta, open(os.path.join(ADOPTED, "META.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 3) 계보 이벤트 기록 → 트리 화면 ★ + base 반영
    try:
        from run_history import record, render_html
        record("adopt", ts=version, base=parent)   # ★ 표시(해당 finetune 행 adopted=1)
        render_html()
    except Exception as exc:
        print(f"  (run_history 기록 실패: {exc})")

    print(f"[adopt] ★ 채택 완료: {version}  (부모={parent})")
    print(f"        adopted/inference  → main.py 가 이걸 rec 로 로드")
    print(f"        adopted/best_accuracy.pdparams → --from-adopted 이어받기 base")
    print(f"        스냅샷: {os.path.relpath(vdir, HERE)}")
    print(f"  다음 라운드: bash ~/OCR/run-finetune.sh --from-adopted  (부모={version} 로 이어받음)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None, help="채택 버전 태그(기본 vYYMMDD_HHMM)")
    ap.add_argument("--parent", default=None, help="이어받은 부모(기본 직전 채택본→없으면 official)")
    return adopt(ap.parse_args().version, ap.parse_args().parent)


if __name__ == "__main__":
    raise SystemExit(main())
