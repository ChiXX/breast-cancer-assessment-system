export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW' | '未知';

export interface Assessment {
  id: number;
  session_id: string;
  user_input: string;
  risk_level: RiskLevel;
  action_required?: string;
  ctcae_grade?: string;
  advice: string;
  evidence: string;
  matched_rule_id: string;
  display_text?: string;
  contact_team: boolean;
  version: string;
  created_at: string;
}

export const EventName = {
  ASSESSMENT_STARTED: 'assessment_started',
  ASSESSMENT_SUBMITTED: 'assessment_submitted',
  RESULT_VIEWED: 'result_viewed',
  CONTACT_TEAM_CLICKED: 'contact_team_clicked',
  ASSESSMENT_CLOSED: 'assessment_closed',
} as const;

export type EventName = typeof EventName[keyof typeof EventName];
