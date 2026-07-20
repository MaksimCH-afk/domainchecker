// Shared types mirroring the backend contract.

export type Tier = "A" | "B" | "C" | "Review" | "Rejected";

export interface ResultRow {
  Target: string;
  tier: Tier;
  score: number | null;
  reject_reason: string;
  "Domain Rating": number;
  rd_fol: number;
  fol_share: number;
  bl_rd: number;
  subnet_div: number;
  burn: number;
  "Organic / Traffic": number;
  cc: string;
  tld: string;
  flag_spam_floor: boolean;
  flag_burn: boolean;
  flag_geo_review: boolean;
  flag_cjk: boolean;
  tier_override_reason: string;
}

export interface CountPct {
  count: number;
  pct: number;
}

export interface Summary {
  total_input_rows: number;
  duplicates_removed: number;
  analyzed: number;
  tiers: Record<Tier, CountPct>;
  reject_reasons: Record<string, CountPct>;
  flags: Record<string, CountPct>;
  tier_overrides: Record<string, number>;
}

export interface AnalyzeResponse {
  summary: Summary;
  warnings: string[];
  rows: ResultRow[];
}

// Config is deeply nested and edited generically; keep it loose.
export type Config = any;

export interface UploadStats {
  dataset_id: string;
  filename?: string;
  recognized: number;
  total_rows: number;
  duplicates_removed: number;
}
