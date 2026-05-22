/**
 * RunOCR 결과 화면 layout 전용 presentational 컴포넌트.
 *
 * 역할:
 * - viewer / resultPanel / scanOverlay / hiddenFileInput 4개 node 를
 *   `uw-result-root > uw-result-doc / uw-result-panel + 숨겨진 input` DOM
 *   구조에 배치한다.
 *
 * Boundary (반드시 지킬 것):
 * - OCR 도메인 상태/핸들러/API/매핑/history/autofill 을 알지 않는다.
 * - OcrDocViewer / OcrResultPanel / CornerAdjust 등 자식 컴포넌트를 직접
 *   import 하지 않는다 (node composition 만 수행).
 * - props 는 4개를 크게 넘기지 않는다 — direct props 방식 회피용 결정.
 */
import React from "react";

/**
 * RunOcrResultLayout 의 노드 컴포지션 props.
 * 모든 필드는 사전에 RunOcrWorkspace 에서 구성한 JSX 노드만 받는다.
 */
export type RunOcrResultLayoutProps = {
  viewer: React.ReactNode;
  resultPanel: React.ReactNode;
  scanOverlay?: React.ReactNode;
  hiddenFileInput?: React.ReactNode;
};

/**
 * 결과 화면 layout. `uw-result-doc` 내부에 viewer 와 scanOverlay 를 함께
 * 배치하고, 우측에 resultPanel, 그리고 형제 노드로 hiddenFileInput 을 둔다.
 * 조건 분기는 호출 측(RunOcrWorkspace)에서 결정한다.
 */
export default function RunOcrResultLayout({
  viewer,
  resultPanel,
  scanOverlay,
  hiddenFileInput,
}: RunOcrResultLayoutProps) {
  return (
    <div className="uw-result-root">
      {/* 왼쪽: Custom 탭이면 OcrCanvasPane, 아니면 OcrDocViewer */}
      <div className="uw-result-doc" style={{ position: "relative" }}>
        {viewer}
        {scanOverlay}
      </div>

      {/* 오른쪽: 결과 패널 */}
      <div className="uw-result-panel">
        {resultPanel}
      </div>

      {/* 숨겨진 파일 인풋 */}
      {hiddenFileInput}
    </div>
  );
}
