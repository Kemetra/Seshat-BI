/**
 * GENERATED FILE -- do not edit by hand.
 *
 * Source: specs/139-seshat-studio-foundation/contracts/studio-api.yaml
 * Regenerate: python scripts/generate_studio_types.py
 *
 * `studio-api.yaml` is the authority for every payload Studio serves. These types are
 * derived from it so the browser cannot drift from the contract; a stale copy is a
 * failing test, not a runtime surprise.
 */

export type ReadinessStage = "source_ready" | "mapping_ready" | "silver_ready" | "gold_ready" | "semantic_model_ready" | "dashboard_ready" | "publish_ready";

export interface EvidenceRef {
  label: string;
  source_ref: string;
  kind: string;
  live_state: "verified" | "pending_live_profile" | "not_applicable";
}

export interface BlockingReason {
  code: string | null;
  message: string;
  source_ref: string | null;
}

export interface ActionSummary {
  id: string;
  label: string;
  explanation: string;
  requires_agent: boolean;
  requires_named_human: boolean;
}

export interface StageState {
  stage: ReadinessStage;
  status: "not_started" | "blocked" | "warning" | "pass";
  evidence: EvidenceRef[];
  blocking_reasons: BlockingReason[];
  required_authority: string[];
}

export interface TableJourney {
  table_id: string;
  display_name: string;
  current_stage: ReadinessStage | null;
  stages: StageState[];
  next_action?: ActionSummary | null;
  forbidden_scope: string[];
}

export interface InputDefect {
  code: string;
  message: string;
  source_ref: string | null;
  recovery_action: string;
}

export interface WorkspaceIdentity {
  display_name: string;
  root_fingerprint: string;
  branch: string | null;
  revision: string;
}

export interface AgentHealth {
  state: "healthy" | "missing" | "signed_out" | "incompatible" | "quota_limited" | "crashed" | "disabled";
  summary: string;
  recovery_action: string;
  provider: "codex" | "disabled";
  version: string | null;
}

export interface WorkspaceSnapshot {
  identity: WorkspaceIdentity;
  generated_at: string;
  tables: TableJourney[];
  next_action?: ActionSummary | null;
  pending_decision_count: number;
  input_defects: InputDefect[];
  agent_health: AgentHealth;
}

export interface BootstrapState {
  workspace: WorkspaceSnapshot;
  navigation: "command_room"[];
  authentication_mode: "subscription" | "operator_configured_alternate";
  capabilities: {
    agent_turns: boolean;
    technical_approvals: boolean;
    business_decision_recording: false;
  };
}

export interface PreparedDecisionSummary {
  decision_id: string;
  question: string;
  required_authority: string;
  affected_scope: string[];
  status: "prepared";
}

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail: string;
  recovery_action: string;
  source_ref?: string | null;
}
