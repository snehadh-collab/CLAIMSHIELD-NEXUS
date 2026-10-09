import type { FC } from "react";

export interface ParsedCitation { label: string; section: string; body: string }
export function parseCitation(raw: unknown): ParsedCitation;
export function useCaseContext(caseId: string): {
  status: "loading" | "ready" | "error";
  rules: string[];
  citations: ParsedCitation[];
  error: string;
  retry: () => void;
};
declare const CaseWorkspaceView: FC<{ caseId: string }>;
export default CaseWorkspaceView;
