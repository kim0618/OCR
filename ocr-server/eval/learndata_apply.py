"""learndata_apply — learndata json(learndata_build 출력)을 {읽기→코드} 룩업으로 → replay 행에 적용.

측정1/측정2 용: replay_compare 가 itemCode 옆에 learndata 적용 결과를 나란히 채점하도록,
ext행·GT행에 새 키(itemCodeLearnA/B)를 주입한다. compare_table 이 GT행 키를 동적 채점하므로
(compare_table.py:30) 키만 넣으면 자동으로 컬럼이 생긴다.

캐스케이드(war ocr.xml selectMasterItemLearnData 재현):
  게이트 = learn_count(그 ocr_item_nm 총 학습수) >= 3.
  다중코드 = ★majority(most_common). war 는 SIMILARITY(master 정식명,입력)+|bp1-단가| tiebreak인데,
            여기선 master_dict/단가 없이 근사(majority). 다중코드는 ~10%(26,649/276,919)라 영향 제한적.
            → 정밀 tiebreak 필요시 master_dict 조인 버전으로 교체.
  적용 = 읽기가 룩업에 있으면 그 cd, 없으면 기존 itemCode(=②master) fallback → 캐스케이드 learndata→master.
"""
from __future__ import annotations
import json
from collections import defaultdict, Counter


def load_lookup(path: str, min_count: int = 3) -> dict[str, str]:
    """learndata json → {ocr_item_nm: dominant_cd}. learn_count>=min_count 인 읽기만."""
    data = json.load(open(path, encoding="utf-8"))
    by_reading: dict[str, Counter] = defaultdict(Counter)
    for r in data.get("rows") or []:
        rd = (r.get("ocr_item_nm") or "").strip()
        cd = (r.get("user_item_cd") or "").strip()
        if rd and cd:
            by_reading[rd][cd] += 1
    lut: dict[str, str] = {}
    for rd, counter in by_reading.items():
        if sum(counter.values()) >= min_count:
            lut[rd] = counter.most_common(1)[0][0]
    return lut


def apply_to_rows(ext_rows: list[dict] | None, gt_rows: list[dict] | None,
                  lut: dict[str, str], out_key: str) -> None:
    """양쪽에 out_key 주입 → compare_table 이 동적 채점.
      ext: 읽기(itemName raw) → learndata cd, 없으면 기존 itemCode(②master) fallback.
      gt : out_key = itemCode(정답). itemCode 없는 행은 채점대상 아님(주입 안 함)."""
    for r in ext_rows or []:
        reading = (r.get("itemName") or "").strip()
        r[out_key] = lut.get(reading) or (r.get("itemCode") or "")
    for g in gt_rows or []:
        code = (g.get("itemCode") or "").strip()
        if code:
            g[out_key] = code
