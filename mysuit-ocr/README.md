# mysuit-ocr (drop-in)

이 폴더는 **Next.js(App Router)** 프로젝트에 그대로 추가해서 `/ocr` 라우트를 제공하는 **프론트 전용 OCR 영역 지정 화면**입니다.

- Konva/react-konva를 제거하고 **순수 DOM 오버레이 방식**으로 구현해서
  - `canvas`(node-canvas) 의존성 문제
  - SSR/서버 번들에서 `konva/cmj/index-node.js`가 끌려오는 문제
  를 원천 차단했습니다.

---

## 1) 어디에 넣어야 하나?

### A. 지금 AI Chat이 `http://localhost:3000/chat` 로 떠 있다면 (권장)
OCR도 **같은 Next 서버 인스턴스**에 붙이는 게 맞습니다.

- 예) 모노레포 구조
  - `apps/web-assistant/src/app/chat/page.tsx` 가 존재

➡️ 이 경우, 이 폴더의 `src/` 아래 내용을 **그대로** 아래 경로에 **병합(merge)** 하세요.

- 대상 경로: `apps/web-assistant/src/`
- 병합 결과:
  - `apps/web-assistant/src/app/ocr/page.tsx`
  - `apps/web-assistant/src/app/ocr/page.client.tsx`
  - `apps/web-assistant/src/components/ocr/OcrAnnotator.tsx`

### B. 단일 앱 구조라면
- 대상 경로: 프로젝트 루트의 `src/` (즉, `src/app/...`가 있는 곳)

---

## 2) 포트는 3000? 3001?

- **같은 Next 앱**이면 `/chat`과 `/ocr`은 **무조건 같은 포트**입니다.
  - `http://localhost:3000/chat`
  - `http://localhost:3000/ocr`

- 만약 `pnpm dev:mysuit-ocr`가 **별도의 Next 앱을 따로 띄우는 스크립트**라면 포트가 3001로 뜰 수도 있습니다.
  - Next는 3000이 이미 사용 중이면 자동으로 3001로 올립니다.

✅ 결론: "OCR도 3000에서 호출"하려면
- **chat을 띄운 동일한 dev 서버를 사용**하거나,
- dev 스크립트에 `-p 3000`(또는 `PORT=3000`)을 강제하고,
- 3000을 이미 점유한 다른 dev 서버를 종료해야 합니다.

---

## 3) 실행

```bash
pnpm dev:mysuit-ocr
# 또는 (해당 앱에서)
# pnpm dev
```

콘솔에 아래처럼 찍히는지 확인하세요.
- `ready - started server on 0.0.0.0:3000, url: http://localhost:3000`

---

## 4) 기능
- 이미지 업로드
- 드래그로 영역 생성
- 영역 선택/이동/리사이즈(코너 핸들)
- 영역 목록/이름 변경/삭제
- JSON 내보내기(클립보드/다운로드)

> 모든 좌표는 **원본 이미지 기준(px)** 으로 저장/내보내기 됩니다.
