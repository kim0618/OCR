"""후보 표에 이미지가 비어 있는 크롭을 AWS 코퍼스에서 가져와 캐시에 채운다.

배경: 잃어버림 후보 크롭은 감사 압축본(lost_crops.tgz)에 전부 있지만, 못 읽음 후보는
원본이 AWS 코퍼스에만 있어 로컬에는 옛 NEXT_TARGETS 캐시가 있는 것만 표시된다.
사람이 GT/오독을 판단하는 유일한 근거가 크롭 실물이므로 빈 칸을 남기지 않는다.

사용법
  1) (로컬) 필요한 경로 목록을 뽑는다
       python eval/finetune/demo/fetch_candidate_crops.py --list
     -> eval/finetune/demo/missing_crops.txt
  2) (로컬→AWS) 목록을 올리고 AWS 에서 묶는다
       scp -i <key> eval/finetune/demo/missing_crops.txt ubuntu@<host>:/tmp/
       ssh  -i <key> ubuntu@<host> 'cd ~/OCR/ocr-server/eval/finetune_corpus \
            && tr -d "\\r" < /tmp/missing_crops.txt > /tmp/mc.txt \
            && tar czf /tmp/missing_crops.tgz -T /tmp/mc.txt'
       scp -i <key> ubuntu@<host>:/tmp/missing_crops.tgz eval/finetune/demo/
  3) (로컬) 캐시에 반영
       python eval/finetune/demo/fetch_candidate_crops.py --apply
     -> eval/finetune/demo/crop_cache.json (경로 -> data:URI)
  4) 재집계·화면 재생성
       python eval/finetune/demo/recount_reviewed_gt.py
       python eval/demo_summary.py
"""
from __future__ import annotations

import argparse
import base64
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECOUNT = HERE / "GT_REVIEW_RECOUNT.json"
SCANS = HERE / "scans"
CACHE = HERE / "crop_cache.json"
MISSING = HERE / "missing_crops.txt"
ARCHIVE = HERE / "missing_crops.tgz"
TOP_N = 10          # 화면에 실제로 뜨는 행 수. 그 이상은 굳이 받지 않는다.
PER_ROW = 3         # 행당 표시 썸네일 수


def _scan_rows(tag: str) -> dict[str, dict]:
    path = SCANS / f"{tag}.jsonl"
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["path"]] = row
    return rows


def _needed(latest_tag: str) -> list[str]:
    """상위 후보 행 중 이미지가 없는 행의 크롭 경로."""
    data = json.loads(RECOUNT.read_text(encoding="utf-8"))
    scan = _scan_rows(latest_tag)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    # 이름 -> 그 이름을 GT 로 갖는 스캔 경로들
    by_name: dict[str, list[str]] = {}
    for path, row in scan.items():
        by_name.setdefault("".join(row["gt"].split()), []).append(path)

    # 화면에는 모든 run 의 후보 표가 나온다. 한 run 만 채우면 나머지가 빈칸으로 남는다.
    sections = []
    for run_candidates in (data.get("candidates") or {}).values():
        sections.extend([run_candidates.get("lost") or [], run_candidates.get("unread") or []])
    if not sections:
        sections = [data.get("v5LostCandidates") or [], data.get("v5UnreadCandidates") or []]

    want: list[str] = []
    for rows_all in sections:
        rows = sorted(rows_all, key=lambda r: (-r["hits"], -r["crops"], r["name"]))[:TOP_N]
        for row in rows:
            if len(row.get("crops64") or []) >= min(PER_ROW, row["hits"]):
                continue
            for path in by_name.get("".join(row["name"].split()), [])[:PER_ROW]:
                if path not in cache and path not in want:
                    want.append(path)
    return want


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--latest-tag", default=None,
                    help="기준 스캔 태그(기본: scans 의 000_base 제외 최신)")
    ap.add_argument("--list", action="store_true", help="필요한 경로 목록만 출력")
    ap.add_argument("--apply", action="store_true", help="내려받은 tgz 를 캐시에 반영")
    ap.add_argument("--archive", default=None,
                    help="반영할 tgz 경로(기본: missing_crops.tgz). 다른 목적으로 따로 "
                         "받아온 압축본도 같은 캐시에 넣을 수 있게 한다")
    args = ap.parse_args()

    tag = args.latest_tag or sorted(
        p.stem for p in SCANS.glob("*.jsonl") if p.name != "000_base.jsonl")[-1]

    if args.apply:
        archive_path = Path(args.archive) if args.archive else ARCHIVE
        if not archive_path.exists():
            raise SystemExit(f"압축본이 없습니다: {archive_path}")
        cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        added = 0
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                data = archive.extractfile(member)
                if data is None:
                    continue
                mime = "image/png" if member.name.lower().endswith(".png") else "image/jpeg"
                key = member.name.lstrip("./")
                if key not in cache:
                    added += 1
                cache[key] = f"data:{mime};base64," + base64.b64encode(data.read()).decode("ascii")
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"캐시 갱신: {CACHE}  (신규 {added} / 전체 {len(cache)})")
        return

    want = _needed(tag)
    MISSING.write_text("\n".join(want) + ("\n" if want else ""), encoding="utf-8")
    print(f"기준 스캔: {tag}")
    print(f"이미지가 없는 상위 후보 크롭 {len(want)}개 -> {MISSING}")
    if not want:
        print("모두 이미지가 있습니다. AWS 에서 받아올 것이 없습니다.")


if __name__ == "__main__":
    main()
