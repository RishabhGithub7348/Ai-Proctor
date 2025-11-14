// API Request/Response Types

export interface SessionCreate {
  candidate_name: string;
  interview_type: string;
  duration_minutes?: number;
}

export interface SessionResponse {
  session_id: string;
  candidate_name: string;
  interview_type: string;
  start_time: string;
  status: string;
}

export interface Alert {
  alert_id: string;
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  message: string;
  timestamp: string;
  requires_attention: boolean;
}

export interface ProctoringStatus {
  session_id: string;
  is_active: boolean;
  alerts: Alert[];
  current_violations: string[];
}

export interface Violation {
  type: string;
  severity: string;
  description: string;
  timestamp: string;
  data?: any;
}

export interface FrameProcessingResult {
  timestamp: string;
  session_id: string;
  violations: Violation[];
  alerts: Alert[];
  face_detection: any;
  eye_tracking: any;
  object_detection: any;
  status: string;
}

export interface HealthCheck {
  status: string;
  message: string;
  version: string;
}

export interface DetailedHealthCheck {
  status: string;
  environment: string;
  debug: boolean;
}
