# Fine-tune RECIPE (PP-OCR rec) — operational steps

The data side is automated (corpus → crops → dataset lists). The training side is
documented here as commands, NOT a blind auto-wrapper: PaddleOCR's training
flags/config are version-specific and can't be verified from this repo without the
training stack + real data. Build the wrapper only after a successful manual run.

> Gate before starting: corpus must hold ENOUGH recurring `cropReady` candidates
> (see FINETUNE_LEDGER + `labels.txt` size, `seenCount` in ledger.jsonl). A few
> dozen on the 24-base is a PIPELINE smoke only — the resulting model is throwaway
> (6 docs, train≈test). Real fine-tune waits for thousands + a held-out test set.

## 0. Prereqs (AWS GPU box)
- PaddlePaddle-GPU + the PaddleOCR **training** repo (we serve inference; training
  code/deps are extra). Verify `tools/train.py` runs.
- The served rec model's **pretrained weights** (.pdparams) and its **official
  config** (to copy Architecture/Transforms verbatim into our template).

## 1. Build the dataset (automated, no GPU)
```
python eval/build_dataset.py --balance-ratio 1.0   # combine failure + balance crops, split
```
→ `eval/finetune_corpus/dataset/{train,val,test}.txt` + manifest.json
   data_dir for PaddleOCR = `eval/finetune_corpus/`

## 2. Dict
Reuse the served model's Korean dict. Extend ONLY if the ledger shows out-of-charset
glyphs (and then you MUST have training samples for them). Point config
`character_dict_path` at it.

## 3. Config
Fill `eval/finetune/config_rec_finetune.yml` placeholders. CRITICAL: copy
Architecture / Loss / RecResizeImg image_shape from the pretrained model's OWN
official config — these must match exactly or fine-tune is invalid.

## 4. Train (GPU)
```
python <PaddleOCR>/tools/train.py -c eval/finetune/config_rec_finetune.yml
```
Watch val `acc`. Early-stop when it plateaus or starts dropping (overfitting).
batch_size_per_card is the "한번에 몇 장" (GPU-memory bound); whole set runs many epochs.

## 5. Evaluate — TWO gates (both must pass)
- **Domain**: rec accuracy on `dataset/test.txt` (held-out) goes UP vs the old model.
- **No forgetting**: accuracy on the BASELINE LOCK set (docs/BASELINE_LOCK_*) does
  NOT meaningfully drop. (This is why balance crops exist.)
Keep the new model only if domain ↑ AND general not ↓.

## 6. Export → swap → re-measure
```
python <PaddleOCR>/tools/export_model.py -c <config> -o Global.pretrained_model=<best> \
       Global.save_inference_dir=<inf_dir>
```
Point the server's rec inference model at `<inf_dir>`, then re-run the eval loop:
```
bash ~/OCR/run-eval.sh     # field/cell improvement end-to-end, same scoreboard
```

## 7. Loop
Better recognition → fewer recognition defects, BUT newly-read values may expose
NEW parser gaps → rules resume. Next fine-tune cycle when the corpus re-accumulates
enough. Rules ↔ fine-tune alternate.

---
Automated here: corpus (ledger/crops/balance) + `build_dataset.py`.
Manual/documented (steps 2–6): dict, config fill, train, eval, export — wrap into a
script only after one clean manual run proves the flags on the actual stack.
