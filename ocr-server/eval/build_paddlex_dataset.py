"""build_paddlex_dataset — arrange the corpus into a PaddleX MSTextRecDataset.

build_dataset.py writes dataset/{train,val,test}.txt with image paths relative to
the corpus dir (`crops/..` / `crops_correct/..`). PaddleX's text-recognition trainer
(check_dataset, MSTextRecDataset) wants a `dataset_dir` that DIRECTLY contains
train.txt / val.txt (/ test.txt) + dict.txt, with each `file_name` resolvable via
os.path.join(dataset_dir, file_name). Our crops already live under <corpus>/crops[_correct]/,
so the corpus dir IS the dataset_dir — we only:
  1) surface the split lists at the corpus root (copy from dataset/), and
  2) drop in dict.txt = the SERVED model's OWN character set.

dict.txt is extracted verbatim from the downloaded model's inference.yml
`character_dict` (korean_PP-OCRv5_mobile_rec), NOT built from our labels: a dict that
differs from the pretrained head's char set breaks fine-tuning (head dim / label
encoding mismatch). Run on the host where the model is downloaded (the server box),
so ~/.paddlex/official_models/<model>/ exists.

    .venv/bin/python eval/build_paddlex_dataset.py
      -> writes <corpus>/{train,val,test}.txt + <corpus>/dict.txt
      -> prints the dataset_dir to set as Global.dataset_dir in the fine-tune config
"""
from __future__ import annotations

import glob
import os
import shutil
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finetune_ledger import CORPUS_DIR  # noqa: E402

MODEL = "korean_PP-OCRv5_mobile_rec"          # main.py:1135 (text_recognition_model_name)
DATASET_SUBDIR = os.path.join(CORPUS_DIR, "dataset")


def find_model_yml() -> str | None:
    """The downloaded PaddleX official model's inference.yml (holds character_dict)."""
    direct = os.path.expanduser(f"~/.paddlex/official_models/{MODEL}/inference.yml")
    if os.path.isfile(direct):
        return direct
    hits = glob.glob(os.path.expanduser(f"~/.paddlex/**/{MODEL}/inference.yml"), recursive=True)
    return hits[0] if hits else None


def extract_char_dict(yml_path: str) -> list:
    """Pull the `character_dict` list out of the inference.yml (nested-key tolerant)."""
    doc = yaml.safe_load(open(yml_path, encoding="utf-8"))

    def find(o, key):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == key:
                    return v
                r = find(v, key)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = find(v, key)
                if r is not None:
                    return r
        return None

    cd = find(doc, "character_dict")
    if not cd:
        raise SystemExit(f"no `character_dict` found in {yml_path}")
    return cd


def main() -> int:
    yml = find_model_yml()
    if not yml:
        raise SystemExit(
            f"model '{MODEL}' not found under ~/.paddlex/official_models — run the "
            "server once so PaddleX downloads it, then re-run this.")
    chars = extract_char_dict(yml)
    dict_path = os.path.join(CORPUS_DIR, "dict.txt")
    with open(dict_path, "w", encoding="utf-8") as fh:
        for c in chars:
            fh.write(f"{c}\n")

    copied = []
    for tag in ("train", "val", "test"):
        src = os.path.join(DATASET_SUBDIR, f"{tag}.txt")
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(CORPUS_DIR, f"{tag}.txt"))
            copied.append(tag)
    if "train" not in copied or "val" not in copied:
        raise SystemExit(
            f"train.txt/val.txt missing in {DATASET_SUBDIR} — run build_dataset.py first")
    # PaddleX's TextRecDatasetChecker.get_dataset_root globs `**/train.txt` under
    # dataset_dir and asserts EXACTLY ONE. The nested dataset/ copies would be a second
    # match → AssertionError. The surfaced root copies are now the canonical PaddleX
    # inputs, so drop the nested list files (regenerable anytime via build_dataset.py;
    # manifest.json is kept). Re-run order is always build_dataset → build_paddlex_dataset.
    for tag in ("train", "val", "test"):
        nested = os.path.join(DATASET_SUBDIR, f"{tag}.txt")
        if os.path.isfile(nested):
            os.remove(nested)

    sys.stdout.reconfigure(errors="replace")
    print(f"[paddlex-dataset] dict.txt = {len(chars):,} chars (from served model) -> {dict_path}")
    print(f"[paddlex-dataset] lists surfaced at corpus root: {copied}")
    print(f"[paddlex-dataset] dataset_dir = {CORPUS_DIR}")
    print("  -> set Global.dataset_dir to this path in config_ppocrv5_rec_finetune.yaml,")
    print("     then: python -m paddlex --config eval/finetune/config_ppocrv5_rec_finetune.yaml -o Global.mode=check_dataset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
