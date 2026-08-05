from __future__ import annotations

import base64
import json
import re
import tarfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
AUDIT = HERE / "verify" / "lost_v5_full_audit_20260805"
RESULT = HERE / "GT_REVIEW_220_result.json"
OUTPUT = HERE / "GT_REVIEW_RECOUNT.json"
SCANS = HERE / "scans"
EDGE_JUNK = r'''|[]_?$><~`^\!@#&*=+{};:"'‘’“”'''


def name_key(text: str) -> str:
    return "".join(text.split())


def comparable(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return "".join(text.split()).strip(EDGE_JUNK)


def load_scan(name: str, keep: set[str]) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with (SCANS / name).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["path"] in keep:
                rows[row["path"]] = row
    return rows


def load_policy() -> tuple[dict[str, str], set[str], dict[str, int]]:
    review = json.loads(RESULT.read_text(encoding="utf-8"))
    approved: dict[str, list[str]] = {}
    for row in review:
        if row["status"] == "approved":
            approved.setdefault(name_key(row["old_gt"]), []).append(row["final_gt"])

    conflicts = {
        key: sorted(set(map(comparable, values)))
        for key, values in approved.items()
        if len(set(map(comparable, values))) > 1
    }
    if conflicts:
        raise RuntimeError(f"conflicting reviewed GT mappings: {conflicts}")
    overrides = {key: values[0] for key, values in approved.items()}

    verdicts: dict[int, str] = {}
    for line in (AUDIT / "verdicts.txt").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(\d+)\s+([MGBXOCP])", line.strip())
        if match:
            verdicts[int(match.group(1))] = match.group(2)
    groups = json.loads((AUDIT / "meta.json").read_text(encoding="utf-8"))

    excluded = {
        name_key(group["name"])
        for group in groups
        if verdicts.get(int(group["idx"])) in {"X", "O", "C", "P"}
    }
    excluded.update(
        name_key(row["old_gt"])
        for row in review
        if row["status"] == "exclude"
    )

    # Keep pre-existing exclusions that were not resolved by this review.
    for line in (HERE / "gt_bad.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            key = name_key(line.split("\t", 1)[0])
            if key not in overrides:
                excluded.add(key)

    counts = {
        "reviewRows": len(review),
        "approvedRows": sum(row["status"] == "approved" for row in review),
        "excludedRows": sum(row["status"] == "exclude" for row in review),
        "overrideNames": len(overrides),
        "excludedNames": len(excluded),
    }
    return overrides, excluded, counts


def main() -> None:
    keep = {
        line.strip()
        for line in (HERE / "basis_keep.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    overrides, excluded_names, review_counts = load_policy()
    base = load_scan("000_base.jsonl", keep)
    # 스캔 파일명이 곧 실행 시각이라 정렬이 실험 순서다. 새 run 을 추가해도 코드 수정 불필요.
    scan_names = sorted(p.name for p in SCANS.glob("*.jsonl") if p.name != "000_base.jsonl")
    scans = {name.removesuffix(".jsonl"): load_scan(name, keep) for name in scan_names}
    common = set(base)
    for scan in scans.values():
        common &= set(scan)
    # 새 스캔이 기존보다 좁은 크롭 집합을 담으면 모든 과거 수치의 분모가 조용히 바뀐다.
    # 그러면 곡선 비교가 무효이므로 즉시 멈춘다(EXPECTED 는 GT 재검수 확정 시점 값).
    EXPECTED_COMMON = 45617
    if common and len(common) != EXPECTED_COMMON:
        raise RuntimeError(
            f"공통 크롭이 {EXPECTED_COMMON} 이 아니라 {len(common)} 입니다. "
            f"새 스캔의 크롭 집합이 기존과 다릅니다 - 곡선을 비교할 수 없습니다. "
            f"스캔 파일: {scan_names}")

    policy: dict[str, tuple[str, bool]] = {}
    for path in common:
        old_gt = base[path]["gt"]
        key = name_key(old_gt)
        policy[path] = (overrides.get(key, old_gt), key in excluded_names)

    valid = {path for path, (_, excluded) in policy.items() if not excluded}
    # ★실패 = GT 와 결과가 다른 모든 크롭. 겹치지 않게 셋으로 나눈다:
    #    ③ 표기만 다름 - 글자는 전부 맞고 공백·표 테두리만 다름 (먼저 떼어낸다)
    #    ① 잃어버림    - 글자가 틀렸고, 직전 모델은 맞게 읽던 크롭
    #    ② 못 읽음     - 글자가 틀렸고, 직전 모델도 못 읽던 크롭
    #  실패 = ① + ② + ③.  타깃 후보(①②)에는 글자가 실제로 틀린 것만 올라간다.
    #  GT 가 구글 OCR 원문이라 공백·표 세로선이 인쇄를 정확히 반영한다는 보장이 없어,
    #  표기 차이를 학습 타깃으로 삼지 않는다.
    exact = {path: policy[path][0].strip() == base[path]["pred"].strip() for path in valid}
    base_ok = {
        path: comparable(policy[path][0]) == comparable(base[path]["pred"])
        for path in valid
    }
    base_correct = sum(base_ok.values())
    base_correct_strict = sum(exact.values())

    run_results: dict[str, dict[str, int | float]] = {}
    candidate_ok_by_run: dict[str, dict[str, bool]] = {}
    for tag, scan in scans.items():
        # 글자 기준 정답(표기 차이 무시) / 표기까지 완전일치
        candidate_ok = {
            path: comparable(policy[path][0]) == comparable(scan[path]["pred"])
            for path in valid
        }
        exact_ok = {
            path: policy[path][0].strip() == scan[path]["pred"].strip()
            for path in valid
        }
        correct = sum(candidate_ok.values())
        candidate_ok_by_run[tag] = candidate_ok
        # ③ 표기만 다름: 글자는 맞고 표기만 다름
        notation_only = sum(candidate_ok[path] and not exact_ok[path] for path in valid)
        # ①② 는 글자가 틀린 것만. 직전(base) 이 맞게 읽었나로 갈린다.
        lost = sum(base_ok[path] and not candidate_ok[path] for path in valid)
        unread = sum(not base_ok[path] and not candidate_ok[path] for path in valid)
        revived = sum(not base_ok[path] and candidate_ok[path] for path in valid)
        run_results[tag] = {
            "correct": correct,
            "charWrong": len(valid) - correct,        # ① + ②
            "notationOnly": notation_only,            # ③
            "formatting": notation_only,              # 옛 키 호환
            "lost": lost,                             # ①
            "unread": unread,                         # ②
            # 실패 = ① + ② + ③ (겹치지 않는 3분할)
            "incorrect": lost + unread + notation_only,
            "revived": revived,
            "net": revived - lost,
            "lostRateOfBaseCorrect": round(100 * lost / base_correct, 4),
            "strictCorrect": sum(exact_ok.values()),
        }

    # Rebuild v5 candidate groups on the reviewed GT. Reuse old embedded crop
    # thumbnails where a group name is unchanged; a newly revealed group may
    # legitimately have no cached thumbnail.
    old_targets_path = HERE / "005_260804_1623" / "NEXT_TARGETS.json"
    old_targets = json.loads(old_targets_path.read_text(encoding="utf-8"))
    old_images: dict[str, list[str]] = {}
    for section in ("lost", "unread"):
        for item in old_targets.get(section, []):
            key = comparable(item.get("name", ""))
            images = old_images.setdefault(key, [])
            for image in item.get("crops64", []):
                if image not in images:
                    images.append(image)

    # The audit archive stores the actual v5-lost crops, split between
    # crops/ and crops_correct/.  Both directories retain the scan filename,
    # so join them back to scan rows by that stable filename rather than GT.
    # AWS 에서 따로 회수한 크롭 캐시(fetch_candidate_crops.py). 못 읽음 후보처럼
    # 감사 압축본에 없는 크롭의 실물을 여기서 채운다. 경로 그대로가 키다.
    path_cache: dict[str, str] = {}
    cache_file = HERE / "crop_cache.json"
    if cache_file.exists():
        path_cache = json.loads(cache_file.read_text(encoding="utf-8"))

    audit_images: dict[str, str] = {}
    archive_path = AUDIT / "lost_crops.tgz"
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            suffix = Path(member.name).suffix.lower()
            mime = "image/png" if suffix == ".png" else "image/jpeg"
            audit_images[Path(member.name).name] = (
                f"data:{mime};base64," + base64.b64encode(extracted.read()).decode("ascii")
            )

    grouped_paths: dict[str, list[str]] = defaultdict(list)
    display_name: dict[str, str] = {}
    for path in valid:
        gt = policy[path][0]
        group_key = comparable(gt)
        grouped_paths[group_key].append(path)
        display_name.setdefault(group_key, gt)

    def candidate_rows(kind: str, tag: str) -> list[dict]:
        scan = scans[tag]
        run_ok = candidate_ok_by_run[tag]
        result = []
        for group_key, paths in grouped_paths.items():
            if kind == "lost":
                selected = [path for path in paths if base_ok[path] and not run_ok[path]]
            else:
                selected = [path for path in paths if not run_ok[path]]
                if len(selected) != len(paths):
                    continue
            if not selected:
                continue
            wrong = Counter(scan[path]["pred"] for path in selected)
            images: list[str] = []

            # Prefer the exact audited crop for each selected scan path.
            for path in selected:
                image = audit_images.get(Path(path).name) or path_cache.get(path)
                if image and image not in images:
                    images.append(image)
                if len(images) == 3:
                    break

            # Unread groups and newly surfaced groups are not always present in
            # the lost-only archive. Reuse their old cached thumbnails through
            # every row's original GT, which remains stable across the review.
            if len(images) < 3:
                fallback_keys = [group_key]
                fallback_keys.extend(comparable(base[path]["gt"]) for path in paths)
                for fallback_key in fallback_keys:
                    for image in old_images.get(fallback_key, []):
                        if image not in images:
                            images.append(image)
                        if len(images) == 3:
                            break
                    if len(images) == 3:
                        break
            result.append({
                "name": display_name[group_key],
                "crops": len(paths),
                "hits": len(selected),
                "rate": round(100 * len(selected) / len(paths), 1),
                "wrong": [[text, count] for text, count in wrong.most_common(5)],
                "crops64": images,
            })
        return sorted(result, key=lambda item: (-item["hits"], -item["crops"], item["name"]))

    # 직전 최선 모델 대비 전이 경로. 전체 숫자가 좋아져도 손실 집합이 단조롭게
    # 줄지는 않으므로(6배->12배에서 169장 신규 손실), 신규 손실은 따로 뽑아 실물 확인한다.
    BASELINE_TAG = "260804_1623"
    transitions: dict[str, dict] = {}
    if BASELINE_TAG in candidate_ok_by_run:
        prev_ok = candidate_ok_by_run[BASELINE_TAG]
        for tag, cur_ok in candidate_ok_by_run.items():
            if tag <= BASELINE_TAG:
                continue
            new_loss = sorted(p for p in valid if prev_ok[p] and not cur_ok[p])
            new_gain = sorted(p for p in valid if not prev_ok[p] and cur_ok[p])
            transitions[tag] = {
                "vs": BASELINE_TAG,
                "newLoss": len(new_loss),
                "newGain": len(new_gain),
                "netVsPrev": len(new_gain) - len(new_loss),
                "newLossRows": [
                    {"path": p, "gt": policy[p][0],
                     "prevPred": scans[BASELINE_TAG][p]["pred"],
                     "pred": scans[tag][p]["pred"]}
                    for p in new_loss
                ],
            }
            (HERE / f"NEW_LOSS_{tag}_vs_{BASELINE_TAG}.txt").write_text(
                "\n".join(new_loss) + "\n", encoding="utf-8")
            print(f"[전이] {tag} vs {BASELINE_TAG}: 신규손실 {len(new_loss)} / "
                  f"신규회복 {len(new_gain)} / 순 {len(new_gain) - len(new_loss):+d}"
                  f"  -> NEW_LOSS_{tag}_vs_{BASELINE_TAG}.txt")

    payload = {
        "schemaVersion": "demo-reviewed-gt-recount.v1",
        "transitions": transitions,
        "basisCrops": len(common),
        "excludedCrops": len(common) - len(valid),
        "evaluatedCrops": len(valid),
        # 표기(공백·표 테두리·전각) 차이는 무시하고 글자만 본다.
        "verdictBasis": "normalized",
        "baseCorrect": base_correct,
        "baseIncorrect": len(valid) - base_correct,
        "baseCorrectStrict": base_correct_strict,
        **review_counts,
        "runs": run_results,
        # 모든 run 의 후보를 이미지까지 함께 만든다. 로컬에는 코퍼스 원본이 없어
        # NEXT_TARGETS 를 다시 만들면 썸네일이 비므로, 화면은 이 값을 쓴다.
        "candidates": {
            tag: {"lost": candidate_rows("lost", tag), "unread": candidate_rows("unread", tag)}
            for tag in scans
        },
        "v5LostCandidates": candidate_rows("lost", "260804_1623"),
        "v5UnreadCandidates": candidate_rows("unread", "260804_1623"),
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUTPUT} | evaluated={payload['evaluatedCrops']} "
        f"base_correct={payload['baseCorrect']} "
        f"v5_lost={run_results['260804_1623']['lost']} "
        f"v5_revived={run_results['260804_1623']['revived']}"
    )


if __name__ == "__main__":
    main()
