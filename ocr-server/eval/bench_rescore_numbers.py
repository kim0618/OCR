"""숫자 컬럼 재채점 — 콤마 포맷 무시(자릿수 비교). 벤치 콤마왜곡 교정용.
학습라벨=콤마재구성(819,800) vs 벤치GT=원본(819800) 불일치를 정규화로 중립화.
raw(콤마 그대로)와 norm(콤마·공백 제거) 둘 다 출력 + 예측 jsonl 저장(재사용)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finetune_ledger import CORPUS_DIR
from finetune_report import find_ft_inference, predict_all, BASE_MODEL

NUM = {"quantity","unitPrice","amount","supplyAmount","taxAmount","totalAmount","discountAmount"}
def norm(s): return s.replace(",","").replace(" ","").strip()

def load(path):
    rows=[]
    for ln in open(path,encoding="utf-8"):
        p=ln.rstrip("\n").split("\t")
        if len(p)>=3 and p[2] in NUM:
            fp=os.path.join(CORPUS_DIR,p[0])
            if os.path.isfile(fp): rows.append((fp,p[0],p[1],p[2]))
    return rows

from paddlex import create_model
base=create_model(BASE_MODEL); ft=create_model(BASE_MODEL, find_ft_inference())
out=open(os.path.join(HERE,"finetune","BENCH_NUM_PREDICTIONS.jsonl"),"w",encoding="utf-8")
for tab,path in (("unseen","bench_unseen.txt"),("seen","bench_seen.txt")):
    rows=load(os.path.join(CORPUS_DIR,path))
    print(f"[{tab}] number crops: {len(rows):,}", flush=True)
    paths=[r[0] for r in rows]
    bp=predict_all(base,paths); fp_=predict_all(ft,paths)
    stat={}
    for (_,rel,gt,col),b,f in zip(rows,bp,fp_):
        s=stat.setdefault(col,[0,0,0,0,0])  # n, b_raw, f_raw, b_norm, f_norm
        s[0]+=1
        s[1]+=int(b.strip()==gt.strip()); s[2]+=int(f.strip()==gt.strip())
        s[3]+=int(norm(b)==norm(gt));     s[4]+=int(norm(f)==norm(gt))
        out.write(json.dumps({"tab":tab,"path":rel,"col":col,"gt":gt,"base":b,"ft":f},ensure_ascii=False)+"\n")
    print(f"=== {tab.upper()} (콤마무시=norm 기준이 진짜) ===", flush=True)
    print(f"{'col':14s}{'n':>7s}{'b_raw':>8s}{'f_raw':>8s}{'b_norm':>8s}{'f_norm':>8s}{'Δnorm':>8s}")
    for col,(n,br,fr,bn,fn) in sorted(stat.items(),key=lambda x:-x[1][0]):
        print(f"{col:14s}{n:>7,}{100*br/n:>7.1f}%{100*fr/n:>7.1f}%{100*bn/n:>7.1f}%{100*fn/n:>7.1f}%{100*(fn-bn)/n:>+7.1f}", flush=True)
out.close()
