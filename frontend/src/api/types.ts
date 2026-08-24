// All TypeScript types matching the backend Pydantic schemas

export type CaseType = 'subscription_failure' | 'invoice_overdue' | 'checkout_abandoned'
export type CaseStatus = 'open' | 'in_progress' | 'recovered' | 'escalated' | 'written_off' | 'human_pending'
export type ActionType = 'retry_payment' | 'send_reminder' | 'send_offer' | 'escalate_to_human' | 'write_off' | 'generate_payment_link'
export type Channel = 'whatsapp' | 'sms' | 'email' | 'voice' | 'system'
export type InterventionResult = 'pending' | 'sent' | 'delivered' | 'failed' | 'responded'
export type OutcomeType = 'paid' | 'promised' | 'ignored' | 'disputed' | 'opted_out'
export type CustomerSegment = 'consumer' | 'smb' | 'enterprise'

export interface Customer {
  id: string
  name: string
  email?: string
  phone?: string
  segment: CustomerSegment
  risk_score: number
  dnd_opt_out: boolean
  channel_opts: Record<string, boolean>
  city?: string
  created_at: string
  tenure_days: number
}

export interface Diagnosis {
  id: string
  case_id: string
  root_cause: string
  confidence: number
  model_version: string
  reasoning_text: string
  suggested_channel: string
  created_at: string
}

export interface ScoredAction {
  action_type: string
  channel: string
  expected_recovery_prob: number
  reasoning: string
  requires_human_approval: boolean
}

export interface Intervention {
  id: string
  case_id: string
  action_type: ActionType
  channel: Channel
  payload: {
    message?: string
    tts_script?: string
    payment_link?: string
    offer_details?: string
    email_subject?: string
    action_scores?: ScoredAction[]
    retry_result?: Record<string, unknown>
    send_result?: Record<string, unknown>
  }
  scheduled_at: string
  executed_at?: string
  result: InterventionResult
  attempt_number: number
  approved_by_human: boolean
  expected_recovery_prob?: number
  reasoning?: string
}

export interface Outcome {
  id: string
  case_id: string
  intervention_id?: string
  outcome: OutcomeType
  amount: number
  promised_date?: string
  recorded_at: string
}

export interface Case {
  id: string
  customer_id: string
  customer?: Customer
  type: CaseType
  status: CaseStatus
  amount_at_risk: number
  recovered_amount: number
  opened_at: string
  closed_at?: string
  days_open: number
  attempt_count: number
  latest_root_cause?: string
  latest_confidence?: number
  diagnoses?: Diagnosis[]
  interventions?: Intervention[]
  outcomes?: Outcome[]
}

export interface PaginatedCases {
  items: Case[]
  total: number
  page: number
  size: number
  pages: number
}

export interface AuditLogEntry {
  id: string
  case_id?: string
  actor: 'system' | 'model' | 'human'
  action: string
  reasoning: string
  policy_version: string
  timestamp: string
  prev_hash: string
  hash: string
}

export interface AuditVerifyResult {
  valid: boolean
  total_entries: number
  broken_at?: string
  message: string
}

export interface StoppingRule {
  id: string
  name: string
  max_attempts: number
  cooldown_hours: number
  quiet_hours_start: number
  quiet_hours_end: number
  applies_to: string
  active: boolean
  created_at: string
  updated_at: string
}

export interface MetricsOverview {
  total_at_risk_paise: number
  total_recovered_paise: number
  recovery_rate_pct: number
  avg_time_to_recovery_hours: number
  cases_open: number
  cases_in_progress: number
  cases_recovered: number
  cases_escalated: number
  cases_written_off: number
  cases_human_pending: number
  total_cases: number
}

export interface FunnelStage {
  stage: string
  label: string
  count: number
  paise: number
  color: string
}

export interface TrendPoint {
  date: string
  recovered_paise: number
}

export interface AuthUser {
  user_id: string
  email: string
  name: string
  role: 'admin' | 'agent' | 'viewer'
  access_token: string
}
