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
];

export const DATASET_FOLDERS: Record<string, string> = Object.fromEntries(
  TESTSETS.map((testset) => [testset.id, testset.folder]),
);

export function getTestset(dataset: string | null) {
  return TESTSETS.find((testset) => testset.id === dataset) ?? TESTSETS[0];
}
