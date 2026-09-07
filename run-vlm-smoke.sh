#!/bin/bash
# run-vlm-smoke — 스모크 50장을 full_text 있음(A)/없음(B) 두 번 돌리고 게이트를 요약한다.
#
#   bash ~/OCR/run-vlm-smoke.sh            # qwen
#   bash ~/OCR/run-vlm-smoke.sh minicpm
#
# 이 자리는 **환경 확정 게이트**다. 형식만 고치고 정확도 튜닝은 하지 않는다 -
# 프롬프트 v2 는 승자 확정 후 + 전량 재실행과만 함께 간다.
#
# 표본(eval/LLM/inputs/smoke_50.txt)은 500 표본 밖에서 뽑았고 **행수 상위 10장을 일부러 넣었다**.
# 무작위 50장은 행수 중앙값이 10이라 max_tokens 잘림을 못 잡는데, 잘리면 "행수 불일치"로 오해된다.
set -eo pipefail
source ~/OCR/vlm-env.sh
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs

KEY="${1:-qwen}"
REPO=$(vlm_repo "$KEY")
LIST=eval/LLM/inputs/smoke_50.txt
RUN_A="vlm_${KEY}_smoke_A"
RUN_B="vlm_${KEY}_smoke_B"

curl -sf "http://localhost:$VLM_PORT/v1/models" >/dev/null 2>&1 \
  || { echo "✗ vLLM 서버가 안 떠 있다. bash ~/OCR/run-vlm-serve.sh $KEY 먼저." >&2; exit 1; }

# 러너는 표준 라이브러리(urllib)만 쓴다 - venv 불필요.
run_one() {   # run_one <run 이름> [추가 인자...]
  local name="$1"; shift
  rm -rf "eval/runs/$name"
  # 러너는 한 장이라도 실패하면 exit 1 을 낸다. set -e 가 그걸 받아 스크립트를 죽이면
  # B런과 게이트 요약까지 통째로 날아간다(2026-09-07 실제로 그랬다: A 48/50 -> B 미실행).
  # 배치는 실패를 안고 끝까지 가는 게 맞고, 판정은 아래 요약이 한다.
  stdbuf -oL -eL python3 -u eval/llm_runner.py \
    --server "$VLM_SERVER" --model "$REPO" \
    --list "$LIST" --run "$name" --max-tokens "$VLM_MAX_TOKENS" "$@" 2>&1 \
    | tee -a ~/OCR/logs/vlm_smoke.log || true
}

vlm_say "A · full_text 포함  ($RUN_A)"
run_one "$RUN_A"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader

vlm_say "B · full_text 제거  ($RUN_B)"
run_one "$RUN_B" --no-fulltext

vlm_say "게이트 요약"
VLM_MAX_TOKENS="$VLM_MAX_TOKENS" python3 - "$RUN_A" "$RUN_B" "$LIST" <<'PY'
import json, os, sys
runs, list_path = sys.argv[1:3], sys.argv[3]
want = sum(1 for l in open(list_path, encoding='utf-8') if l.strip())
meta = {}
for r in runs:
    d = os.path.join('eval/runs', r)
    m = json.load(open(os.path.join(d, 'run_meta.json'), encoding='utf-8'))
    errs = os.path.join(d, 'errors.jsonl')
    n_err = sum(1 for _ in open(errs, encoding='utf-8')) if os.path.exists(errs) else 0
    rows, empty, cut, ctok = [], 0, [], []
    for fn in os.listdir(os.path.join(d, 'samples')):
        s = json.load(open(os.path.join(d, 'samples', fn), encoding='utf-8'))
        rc = int(s.get('rowCount') or 0)
        rows.append(rc)
        empty += rc == 0
        v = s.get('vlm') or {}
        if v.get('finishReason') not in (None, 'stop'):
            cut.append((s.get('sourceFile'), v.get('finishReason'), rc))
        if v.get('completionTokens'):
            ctok.append(v['completionTokens'])
    meta[r] = dict(m, nErr=n_err, docs=len(rows), maxRow=max(rows or [0]),
                   zeroRow=empty, cut=len(cut))
    print(f"\n[{r}]  {m.get('docs', len(rows))}/{want}장 · {m.get('elapsedSec')}초 · "
          f"{m.get('docsPerHour')}장/시간 · 오류 {n_err}")
    print(f"  행수 상위10 {sorted(rows, reverse=True)[:10]}   행수 0 인 문서 {empty}")
    if ctok:
        cap = int(os.environ.get('VLM_MAX_TOKENS') or 6144)
        print(f"  출력 토큰 최대 {max(ctok):,} / 중앙 {sorted(ctok)[len(ctok)//2]:,}"
              f"   (max_tokens {cap:,} 대비 {100*max(ctok)/cap:.0f}%)")
    if cut:
        print(f"  X 잘림 {len(cut)}장 - finish_reason != stop:")
        for sf, fr, rc in cut[:5]:
            print(f"      {fr:<8} {rc:>3}행  {sf}")
    else:
        print("  O 잘림 없음 (전 문서 finish_reason=stop)")

a, b = (meta[r] for r in runs)
ha, hb = a.get('docsPerHour'), b.get('docsPerHour')
if ha and hb:
    print(f"\nfull_text 오버헤드 = {(hb/ha - 1)*100:.1f}%  "
          f"(A {ha}장/h 포함 · B {hb}장/h 제거)")
    for n, label in ((500*3, '500x3 모델'), (9001, '9,001 본판정')):
        h = n / ha
        print(f"  A 기준 {label:<12} {n:>6,}장 -> {h*60:6.1f}분 · ${h:.2f}")
print("""
판정할 것
  1 JSON 파싱률   오류 0 인가
  2 출력 잘림     위 '잘림 없음' 이 떴나 - finish_reason=stop 이 확정 신호다
                 스모크 최장 51행 = 9,001 전체 최장. 여기서 안 잘리면 500/9,001 도 안 잘린다
                 출력 토큰이 max_tokens 의 80% 를 넘으면 --max-tokens 를 올릴 것
  3 VRAM         위 nvidia-smi 피크가 24GB 안인가
  4 입력 해상도   tail -100 ~/OCR/logs/vllm.log 에서 이미지 토큰 수 확인
  5 소요 역산     위 500x3 / 9,001 추정치

통과하면 - 본 run 뒤에 로컬에서
  python eval/compare_run.py --ts <run> --testset invoice_replay --skip-missing
  python eval/llm_plan_fill.py --model qwen=<run> ... --write     # 계획서 자동 기입""")
PY
