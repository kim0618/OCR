"""fields 라운드 dataset 최종 재검증: 크롭 실재 / 기준셋 오염 / garbage / 콤마 보존."""
from __future__ import annotations

import json
import os
import random
import re

CORPUS = os.path.expanduser("~/OCR/ocr-server/eval/finetune_corpus")
DS = os.path.join(CORPUS, "dataset")

# 5) 크롭 파일 실재 (각 split 랜덤 2000)
rnd = random.Random(1)
for name in ("train", "val", "test"):
    rows = open(os.path.join(DS, name + ".txt"), encoding="utf-8").read().splitlines()
    sample = rnd.sample(rows, min(2000, len(rows)))
    missing = sum(1 for r in sample
                  if not os.path.exists(os.path.join(CORPUS, r.split("\t")[0])))
    verdict = "OK" if missing == 0 else "FAIL"
    print("5) %s: sample %d missing-crop=%d  %s" % (name, len(sample), missing, verdict))

# 6) 기준셋 오염: src 없는 meta(기준셋 수확 338,592) path 유입 여부
banned = set()
for ln in open(os.path.join(CORPUS, "labels_correct.meta.jsonl"), encoding="utf-8"):
    try:
        r = json.loads(ln)
    except json.JSONDecodeError:
        continue
    if not r.get("src"):
        banned.add(r["path"])
leak = 0
for name in ("train", "val", "test"):
    for ln in open(os.path.join(DS, name + ".txt"), encoding="utf-8"):
        if ln.split("\t")[0] in banned:
            leak += 1
print("6) benchmark-harvest balance leak = %d  %s"
      % (leak, "OK(0)" if leak == 0 else "FAIL-CONTAMINATED"))

# 7) 금액/수량 failure 라벨 garbage (음수·12자리+)
MONEY = {"amount", "unitPrice", "supplyAmount", "taxAmount", "totalAmount",
         "discountAmount", "quantity"}
mcol: dict[str, str] = {}
for ln in open(os.path.join(DS, "split_metadata.jsonl"), encoding="utf-8"):
    try:
        r = json.loads(ln)
    except json.JSONDecodeError:
        continue
    if r.get("column") in MONEY:
        mcol[r["path"]] = r["column"]
bad = tot = 0
badex: list[str] = []
comma = re.compile(r"\d{1,3}(,\d{3})+")
bare = re.compile(r"(?<!\d)\d{4,}(?!\d)")
ok = broken = 0
for name in ("train", "val", "test"):
    for ln in open(os.path.join(DS, name + ".txt"), encoding="utf-8"):
        parts = ln.rstrip("\n").split("\t")
        if len(parts) < 2 or parts[0] not in mcol:
            continue
        lab = parts[1]
        tot += 1
        runs = re.findall(r"\d+", lab)
        if re.search(r"-\d", lab) or (runs and max(len(x) for x in runs) >= 12):
            bad += 1
            if len(badex) < 3:
                badex.append(lab)
        if comma.search(lab):
            ok += 1
        elif bare.search(lab):
            broken += 1
print("7) money/qty labels %d, garbage=%d  %s %s"
      % (tot, bad, "OK" if bad == 0 else "FAIL", badex))
if ok + broken:
    print("8) money/qty 1000+ comma: preserved %d / collapsed %d (%.1f%% preserved)"
          % (ok, broken, 100.0 * ok / (ok + broken)))
