#!/usr/bin/env bash
# run-vlm-smoke-box.sh — 좌표(box)까지 요구하는 스모크 50장. **진단 전용**이다.
#
#   ~/OCR/run-vlm-smoke-box.sh            # qwen
#
# 왜 도나 (2026-09-17)
#   지금 VLM 경로는 좌표를 안 받는다. 그래서 (1) 틀린 값이 어디서 왔는지 못 짚고
#   (2) structure/recognition 을 못 가르고 (3) 좌표 기반 Base 룰 11개를 못 태운다.
#   값싼 단계에서 이걸 안 재고 500장을 돌린 게 이번 검토의 설계 실수였다.
#
# ⚠️ 이 run 의 숫자는 **채택 판단에 섞지 않는다**. 500장 결과(66.3%)는 v1 기준 그대로다.
#    기준선은 같은 50장의 v1 스모크 B: 50/50 · 176.1장/h · 잘림 0.
# ⚠️ 잘리면 max_tokens 를 올리지 말 것. "이 컨텍스트로는 좌표를 감당 못 한다"가 결과다.
set -eo pipefail

KEY="${1:-qwen}"
source ~/OCR/vlm-env.sh

REPO="$HOME/OCR/ocr-server"
RUN="vlm_${KEY}_smoke_box"
LIST="eval/LLM/inputs/smoke_50.txt"
PROMPT="eval/LLM/inputs/prompt_v1_box.md"
LOG="$HOME/OCR/logs/${RUN}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$HOME/OCR/logs"
cd "$REPO"
exec > >(tee -a "$LOG") 2>&1

WANT="$(vlm_repo "$KEY")"
vlm_say "$RUN  ·  $WANT  ·  로그 $LOG"

# ── 전제 가드 ───────────────────────────────────────────────────────────────
SERVED="$(curl -sf http://127.0.0.1:8000/v1/models | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null || true)"
[[ "$SERVED" == "$WANT" ]] || {
  echo "✗ 서버가 $WANT 가 아니다 (지금: ${SERVED:-없음}). run-vlm-serve.sh $KEY 먼저." >&2; exit 1; }
[[ -f "$PROMPT" ]] || { echo "✗ 프롬프트가 없다: $PROMPT - git pull 먼저." >&2; exit 1; }
[[ -f "$LIST" ]] || { echo "✗ 목록이 없다: $LIST" >&2; exit 1; }
grep -q '"box"' eval/llm_runner.py || {
  echo "✗ llm_runner.py 가 옛 버전이다 - box 를 저장하지 않고 버린다. git pull 먼저." >&2; exit 1; }
[[ -d "eval/runs/$RUN" ]] && { echo "✗ 이미 있다: eval/runs/$RUN - 지우거나 이름을 바꾸고 다시." >&2; exit 1; }

# ── 실행 (v1 스모크 B 와 같은 설정 · 프롬프트만 다르다) ──────────────────────
python3 -u eval/llm_runner.py \
  --model "$WANT" \
  --list "$LIST" \
  --run "$RUN" \
  --prompt "$PROMPT" \
  --no-fulltext \
  --max-tokens "$VLM_MAX_TOKENS" \
  --timeout 2400 \
  --concurrency 8 || true

# ── 요약 ───────────────────────────────────────────────────────────────────
vlm_say "게이트 요약"
python3 - "$RUN" <<'PY'
import json, os, sys
run = sys.argv[1]
d = os.path.join("eval/runs", run)
m = json.load(open(os.path.join(d, "run_meta.json"), encoding="utf-8"))
rows = boxed = zero = cut = 0
docs = 0
for fn in os.listdir(os.path.join(d, "samples")):
    s = json.load(open(os.path.join(d, "samples", fn), encoding="utf-8"))
    docs += 1
    v = s.get("vlm") or {}
    if v.get("finishReason") not in (None, "stop"):
        cut += 1
    for r in ((s.get("documentFields") or {}).get("tableRows") or []):
        rows += 1
        b = r.get("box")
        if isinstance(b, list) and len(b) == 4:
            boxed += 1
            if b == [0, 0, 0, 0]:
                zero += 1
print("%s  %s/%s장 · %s초 · %s장/시간 · 실패 %s"
      % (run, m.get("ok"), m.get("docs"), m.get("elapsedSec"), m.get("docsPerHour"), m.get("fail")))
print("  행 %d개 중 박스 달린 행 %d (%.1f%%) · 그중 [0,0,0,0] %d" % (rows, boxed, 100 * boxed / max(1, rows), zero))
print("  잘림(finish_reason != stop) %d장" % cut)
print()
print("기준선 (같은 50장 · v1 · full_text 제외)  50/50 · 176.1장/h · 잘림 0")
PY

cat <<EOF

로컬에서 이어서
  scp -r ubuntu@<ip>:'~/OCR/ocr-server/eval/runs/$RUN' eval/runs/
  # 좌표 눈 검증: 박스대로 잘라 10장 보기
  python eval/llm_box_check.py --run $RUN

⚠️ 이 run 은 진단용이다. 계획서 500장 표·비용 표에 넣지 않는다.
EOF
