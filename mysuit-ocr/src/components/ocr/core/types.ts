export type FieldType = "field" | "multi" | "check" | "table";
export type CheckMode = "boxOnly"; // 라벨 기능 제거 → boxOnly만 유지

export type Rect = {
  /** 원본 이미지 기준(px) */
  x: number;
  y: number;
  width: number;
  height: number;
};

/** table 전용 메타 */
export type TableMeta = {
  /**
   * table 동작 모드
   * - repeat: 행 템플릿(rowTemplate)을 반복해 rows를 생성(기존 방식)
   * - auto: 컬럼(세로 가이드)만 고정하고, OCR 단계에서 텍스트/라인을 기반으로 행을 자동 감지(A안 완성형)
   */
  mode?: "repeat" | "auto";
  /** 표에서 “한 줄(행)” 템플릿 영역 */
  rowTemplate?: Rect;
  /** rowTemplate 기반 자동 생성된 행 영역들 */
  rows?: Rect[];
  /**
   * 세로 가이드선(열 경계선) 위치(0~1 비율).
   * - 0은 왼쪽 경계, 1은 오른쪽 경계이므로 저장하지 않습니다.
   * - 비율 기준은 rowTemplate이 있으면 rowTemplate.x~x+width, 없으면 table 영역(x~x+width)입니다.
   */
  colGuides?: number[]; 
  /** 표 종료 판단에 사용하는 키워드(쉼표 구분 입력) */
  stopKeywords?: string[];
};

export type Region = {
  id: string;
  name: string;
  fieldType: FieldType;

  /** 원본 이미지 기준(px) */
  x: number;
  y: number;
  width: number;
  height: number;

  /** multi 전용 */
  parts?: 2 | 3;
  /** multi 전용: parts 길이만큼 비율(합=1) */
  ratios?: number[];

  /** check 전용(라벨 기능 제거했지만, 호환 위해 값은 고정) */
  checkMode?: CheckMode;

  /** table 전용 */
  table?: TableMeta;
};

export type LoadedImage = {
  src: string;
  fileName: string;
  naturalWidth: number;
  naturalHeight: number;
};

export type DragKind =
  | {
      type: "move";
      id: string;
      startX: number;
      startY: number;
      baseX: number;
      baseY: number;
    }
  | {
      type: "resize";
      id: string;
      handle: "nw" | "ne" | "sw" | "se";
      startX: number;
      startY: number;
      base: Region;
    }
  | { type: "draw"; startX: number; startY: number; draftId: string }
  | {
      /** table: 행 템플릿(rowTemplate) 드래그 */
      type: "drawRowTemplate";
      tableId: string;
      startX: number;
      startY: number;
    }
  | {
      /** multi 분할선 드래그 */
      type: "split";
      id: string;
      index: number; // 0이면 1번째 경계(0|1), 1이면 2번째 경계(1|2)
      startX: number;
      baseRatios: number[];
    }
  | {
      /** table: 세로 가이드선(열 경계선) 드래그 */
      type: "tableCol";
      tableId: string;
      index: number;
      startX: number;
      baseGuides: number[];
    }
  | null;