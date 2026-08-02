---
name: feedback-frontend-build-before-typecheck
description: "mysuit-ocr standalone `npm run typecheck` fails on stale .next/types; run `next build` first"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dc28e7c5-526c-4ef4-9b8c-c6961b6bba92
---

In `mysuit-ocr`, running `npm run typecheck` (`tsc --noEmit`) standalone can FAIL with
`TS2307: Cannot find module '../../src/app/test/page.js'` and `.../api/test-images/route.js`.

**Why:** The `test` page and `test-images` API route were removed in earlier cleanup tasks, but
`.next/types/**` retains stale generated `.ts` files referencing the deleted sources. `tsc` picks
up those stale generated files. It is NOT a real type error and is unrelated to source edits.

**How to apply:** Run `npm run build` (`next build`) FIRST — it regenerates `.next/types` cleanly —
then `npm run typecheck` passes (exit 0). So the correct verification order is build → typecheck,
not typecheck → build. (Alternatively delete `.next` before typecheck.) When a task spec lists
"typecheck then build", reorder to build-first or the typecheck step spuriously fails.
