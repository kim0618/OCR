/**
 * /ocr/extract 요청 FormData 구성 helper.
 *
 * 역할:
 * - RunOCR `/ocr/extract` API 호출에 필요한 key/value 와 append 조건을
 *   한 곳에 모아두는 순수 함수. fetch / endpoint 결정은 runOcrRequest.ts 책임.
 *
 * 유지해야 할 FormData key (append 순서대로):
 * - "file"          : 항상 (selectedFile)
 * - "template_id"   : templateId 가 truthy 일 때만
 * - "regions"       : useRegionTemplate && regions?.length 일 때 JSON.stringify
 * - "model_id"      : isRunOcr 일 때만
 * - "documentType"  : documentType 이 truthy 일 때만
 * - "templateMode"  : RunOCR selected template mode marker
 * - "isUnstructuredTemplate" : "Y"/"N" dispatch hardening marker
 *
 * 변경 주의:
 * - key 이름 / append 순서 / 조건 / 값 직렬화(JSON.stringify) 정책을 바꾸면
 *   backend API contract 와 어긋난다. 변경 시 반드시 FormData key parity
 *   check (tmp/check_runocr_formdata_keys_2a.mjs) 와 backend 측 contract
 *   동시 검증 필요.
 */
import type { Region } from "../../../common/types/ocr";

/**
 * buildOcrFormData 의 입력. backend FormData append 조건을 그대로 표현한다.
 * - `useRegionTemplate` : region-based 템플릿 모드 여부 (regions 부착 여부).
 * - `isRunOcr`          : RunOCR 탭에서 호출됐는지 여부 (model_id 부착 여부).
 */
export type BuildOcrFormDataInput = {
  file: File;
  templateId?: string | null;
  useRegionTemplate: boolean;
  regions?: Region[];
  isRunOcr: boolean;
  modelId: string;
  documentType?: string | null;
  templateMode?: string | null;
  isUnstructuredTemplate?: boolean;
};

/**
 * 입력 객체로부터 `/ocr/extract` 용 FormData 인스턴스를 생성한다.
 * append 순서/조건은 파일 상단 주석에 명시된 contract 와 1:1.
 */
export function buildOcrFormData(input: BuildOcrFormDataInput): FormData {
  const formData = new FormData();
  formData.append("file", input.file);
  if (input.templateId) formData.append("template_id", input.templateId);
  if (input.useRegionTemplate && input.regions?.length) {
    formData.append("regions", JSON.stringify(input.regions));
  }
  if (input.isRunOcr) formData.append("model_id", input.modelId);
  if (input.documentType) {
    formData.append("documentType", input.documentType);
  }
  if (input.templateMode) {
    formData.append("templateMode", input.templateMode);
  }
  formData.append("isUnstructuredTemplate", input.isUnstructuredTemplate ? "Y" : "N");
  return formData;
}
