export type ProjectInput = {
  customer: string; project_name: string; brief: string;
  product: string;
  fabric_id: string;
  quantity: number; width_m: number; height_m: number; due_date: string; site: string;
}
export type Fabric = { id: ProjectInput['fabric_id']; name: string; sku: string; roll_width_m: number;
  stock_lm: number; cost_per_lm: number; lead_days: number; transmission: string; color: string; compatible: string[]; source: string }
export type Trace = { agent: string; role: string; summary: string; recommendation: string; sources: string[];
  facts: Record<string, unknown>; mode: string; duration_ms: number; fallback_reason?: string;
  citations?: { id: string; title: string; heading: string; source_url: string; content: string }[] }
export type Report = {
  data_snapshot?: Catalog; knowledge_source?: string;
  id: string; created_at: string; status: 'blocked' | 'awaiting_review' | 'demo_approved';
  reasoning_mode: string; elapsed_ms: number; request: ProjectInput;
  requirements: { product_name: string; area_sqm: number; dimensions: string; quantity: number; scope: string };
  materials: { fabric: Fabric; required_lm: number; shortage_lm: number; in_stock: boolean; fits_roll: boolean;
    layout: string; lead_days: number; waste_percent?: number; alternatives: { id: ProjectInput['fabric_id']; name: string; stock_lm: number; reason: string }[] };
  quality: { blockers: string[]; checklist: string[]; note: string };
  costing: { lines: { description: string; quantity: number; unit: string; unit_cost: number; cost: number }[];
    currency: string; direct_cost: number; subtotal: number; vat: number; total: number; per_unit_incl_vat: number;
    gross_margin_percent: number; vat_percent?: number; valid: boolean; exclusions: string[]; note: string };
  production: { as_of: string; material_ready: string; manufacture_start: string; manufacture_end: string;
    quality_date: string; installation_start: string; completion_date: string; due_date: string; on_time: boolean;
    slack_days: number; factory_hours: number; installation_hours: number; assumptions: string[] };
  decision: { status: string; blockers: string[]; actions: string[]; headline: string; execution: string };
  traces: Trace[];
  approval?: { reviewer: string; approved_at: string; scope: string };
}
export type Health = { status: string; storage_mode: string; reasoning_mode: string; today: string; business_data_source?: string }
export type Catalog = {
  fabrics: Fabric[];
  products: Record<string, { name: string; estimation_kind: string; length_allowance_m: number; width_allowance_m: number; fullness: number }>;
  policy: { waste_fraction: number; margin_fraction: number; vat_fraction: number };
  scenarios: { id: string; title: string; category: string; description: string; deadline_days: number; request: Omit<ProjectInput, 'due_date'> }[];
  data_source: string; fetched_at: string; is_sample: boolean; provenance: string;
}
