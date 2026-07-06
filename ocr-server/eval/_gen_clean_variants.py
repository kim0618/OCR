"""G0 harness: _match_sim.csv -> _match_clean.csv (정규화된 매칭키 변형 컬럼).
psql `_score_clean.sql`이 이 CSV를 채점한다. 데이터준비 스크립트(읽기전용 입력)."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import item_name_clean as C

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'invoice_war')
SRC = os.path.join(DATA, '_match_sim.csv')
OUT = os.path.join(DATA, '_match_clean.csv')

rows = list(csv.DictReader(open(SRC, encoding='utf-8')))
cols = ['gt_code', 'gt_norm'] + list(C.LEVELS) + ['changed']
nchg = 0
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in rows:
        e = r['ext_name']
        vals = [C.clean(e, lv) for lv in C.LEVELS]
        raw = vals[C.LEVELS.index('raw')]
        # 오염 여부: strip/form 중 하나라도 raw와 달라졌으면 클린이 개입한 행
        changed = int(any(v != raw for lv, v in zip(C.LEVELS, vals) if lv in ('strip', 'form', 'core')))
        nchg += changed
        w.writerow([r['gt_code'], C._norm(r['gt_name'])] + vals + [changed])
print(f'wrote {OUT}  rows={len(rows)}  levels={C.LEVELS}  changed={nchg} ({100*nchg/len(rows):.1f}%)')
