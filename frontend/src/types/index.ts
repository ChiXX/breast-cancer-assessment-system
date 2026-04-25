export type RiskLevel = 'High' | 'Medium' | 'Low';

export interface Assessment {
  id: number;
  session_id: string;
  user_input: string;
  risk_level: RiskLevel;
  advice: string;
  evidence: string;
  matched_rule_id: string;
  contact_team: boolean;
  version: string;
  created_at: string;
}

export enum EventName {
  ASSESSMENT_STARTED = 'assessment_started',
  ASSESSMENT_SUBMITTED = 'assessment_submitted',
  RESULT_VIEWED = 'result_viewed',
  CONTACT_TEAM_CLICKED = 'contact_team_clicked',
  ASSESSMENT_CLOSED = 'assessment_closed',
}
