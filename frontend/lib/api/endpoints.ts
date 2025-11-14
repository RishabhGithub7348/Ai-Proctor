import apiClient from "./client";
import {
  SessionCreate,
  SessionResponse,
  ProctoringStatus,
  Alert,
  HealthCheck,
  DetailedHealthCheck,
} from "./types";

// Health Check
export const healthCheck = async (): Promise<HealthCheck> => {
  const { data } = await apiClient.get("/");
  return data;
};

export const detailedHealthCheck = async (): Promise<DetailedHealthCheck> => {
  const { data } = await apiClient.get("/health");
  return data;
};

// Session Management
export const createSession = async (
  sessionData: SessionCreate
): Promise<SessionResponse> => {
  const { data } = await apiClient.post("/api/v1/session/create", sessionData);
  return data;
};

export const getSession = async (sessionId: string): Promise<SessionResponse> => {
  const { data } = await apiClient.get(`/api/v1/session/${sessionId}`);
  return data;
};

export const endSession = async (
  sessionId: string
): Promise<{ status: string; message: string }> => {
  const { data } = await apiClient.post(`/api/v1/session/${sessionId}/end`);
  return data;
};

// Proctoring
export const getProctoringStatus = async (
  sessionId: string
): Promise<ProctoringStatus> => {
  const { data } = await apiClient.get(
    `/api/v1/proctoring/status/${sessionId}`
  );
  return data;
};

export const getAlerts = async (
  sessionId: string,
  limit: number = 100
): Promise<{ session_id: string; alerts: Alert[] }> => {
  const { data } = await apiClient.get(
    `/api/v1/proctoring/alerts/${sessionId}`,
    {
      params: { limit },
    }
  );
  return data;
};

export const createAlert = async (
  sessionId: string,
  alert: Omit<Alert, "alert_id">
): Promise<{ status: string; alert: Alert }> => {
  const { data } = await apiClient.post(
    `/api/v1/proctoring/alerts/${sessionId}`,
    alert
  );
  return data;
};
