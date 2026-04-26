export type TestsetMeta = {
  id: string;
  label: string;
  folder: string;
  path: string;
  description: string;
};

export const TESTSETS: TestsetMeta[] = [
  {
    id: "baseline",
    label: "기존 검증셋",
    folder: "baseline",
    path: "/data/testsets/baseline",
    description: "기존 10장 회귀 테스트용",
  },
  {
    id: "baseline_fast",
    label: "Baseline Fast",
    folder: "baseline_fast",
    path: "/data/testsets/baseline_fast",
    description: "빠른 회귀 확인용 5장 미니셋",
  },
  {
    id: "new_samples",
    label: "신규 샘플셋",
    folder: "new_samples",
    path: "/data/testsets/new_samples",
    description: "공개 샘플 기반 일반화 검증용",
  },
  {
    id: "google",
    label: "Google 샘플셋",
    folder: "google",
    path: "/data/testsets/google",
    description: "사용자가 Google 폴더에 추가한 검증 이미지",
  },
  {
    id: "google_fast",
    label: "Google Fast",
    folder: "google_fast",
    path: "/data/testsets/google_fast",
    description: "실전형 상단 필드 확인용 5장 미니셋",
  },
  {
    id: "receipt_generalization",
    label: "영수증 신규 일반화셋",
    folder: "receipt_generalization",
    path: "/data/testsets/receipt_generalization",
    description: "baseline/google 이후 신규 영수증 샘플 일반화 검증용",
  },
];

export const DATASET_FOLDERS: Record<string, string> = Object.fromEntries(
  TESTSETS.map((testset) => [testset.id, testset.folder]),
);

export function getTestset(dataset: string | null) {
  return TESTSETS.find((testset) => testset.id === dataset) ?? TESTSETS[0];
}

// ---------------------------------------------------------------------------
// Manifest metadata types (added for testset management stage)
// Used by manifest.json in each testset folder — not tied to OCR logic.
// ---------------------------------------------------------------------------

export type DocumentType =
  | "card_receipt"
  | "pos_receipt"
  | "food_cafe_receipt"
  | "finance_slip"
  | "medical_receipt"
  | "invoice_statement"
  | "unknown";

export type QualityTag =
  | "folded"
  | "curled"
  | "skewed"
  | "blurred"
  | "low_contrast"
  | "shadow"
  | "stamp"
  | "handwritten"
  | "cropped"
  | "rotated"
  | "ocr_noise"
  | "small_text"
  | "long_receipt";

export type Difficulty = "easy" | "medium" | "hard";

export type DatasetRole =
  | "fast_check"
  | "regression"
  | "generalization"
  | "experimental"
  | "document_type";

export type DatasetStatus = "locked" | "in_progress" | "draft";

export type ManifestItem = {
  filename: string;
  documentType: DocumentType;
  qualityTags: QualityTag[];
  difficulty: Difficulty;
  expectedStatus: string;
  notes?: string;
};

export type DatasetManifest = {
  datasetId: string;
  datasetRole: DatasetRole;
  status: DatasetStatus;
  lockDoc?: string;
  description: string;
  items: ManifestItem[];
};
