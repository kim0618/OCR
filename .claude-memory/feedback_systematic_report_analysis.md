---
name: feedback_systematic_report_analysis
description: "eval 리포트 분석 필수 프로토콜 — 결론 전 전수 분해 강제. 1~2케이스로 일반화·조기단정(\"floor/멈춤/인식\") 금지"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f9063492-4db1-4118-a63e-d01600f72018
---

리포트 분석할 때 **결론을 내기 전에 아래 전수 분해를 반드시** 한다. 안 그래서 신뢰를 잃음: 2026-06-15 사용자 — "이렇게 계속 내가 보여줄 때마다 '맞습니다' 하면 내가 널 어떻게 믿고 진행하지?" 패턴=부분(1~2 cherry-pick)만 보고 "floor/최적이니 멈추자/인식이라 못고침" 단정 → 사용자가 전체 리포트 보여주면 그제야 정정. **검증을 사용자에게 떠넘긴 것.**

**금지(반복한 잘못):** ① 약한 필드 몇 개 표본만 보고 전체를 "floor/인식"으로 뭉뚱그리기. ② "여기서 멈추자/최적이다/GPU 몫"을 전수 근거 없이 말하기. ③ 내 "이제 다 됐다" 직감 믿기(반복적으로 틀림).

**필수 프로토콜 (결론 전):**
1. **전수**: 약한 필드 *전부*의 *모든* 실패를 분해(샘플 1~2개로 일반화 금지).
2. **누락(ext_missing) 갈래**: GT 값이 OCR에 있나? → `extract_debug.invoice_statement.party_candidates`(bizs/companies) + `full_text`에 GT토큰 검색. **있음=파서(읽힘, CPU로 줍음) / 없음=인식(안읽힘, 사전/모델).**
3. **불일치(mismatch) 갈래**: ext를 (a)상대 party GT와 비교→매칭=**cross-party(파서)** (b)자기 GT와 글자유사도→높음=**char오류(인식)** (c)공백/괄호만=**정규화(P3-b류)** (d)엉뚱한 라인=**오배정(파서)**. 각 **건수 집계**.
4. **정량화 후에만 결론** — "파서 N건 / 인식 M건 / cross-party K건" 숫자로. 숫자 없이 "대부분 floor" 금지.
5. 도구: 비교는 `eval/runs/<ts>/study/compare/*.json`(gt/ext/status per field), 읽힘확인은 서버 probe(full_text+party_candidates). 추측 금지 [[feedback_no_speculation_use_run_data]].

**핵심 마인드셋:** 기본가정 = "읽혔는데 파서가 떨어뜨린 것일 수 있다, 전수로 확인 전엔 floor 단정 안 함." 사용자가 리포트 보여주기 *전에* 내가 먼저 완전한 분류표를 내놔야 신뢰가 생긴다. [[feedback_analysis_prioritize]] [[project_free_vs_template_gaps]]
