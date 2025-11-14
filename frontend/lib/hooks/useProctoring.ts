import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getProctoringStatus,
  getAlerts,
  createAlert,
} from "@/lib/api/endpoints";
import { Alert } from "@/lib/api/types";

// Query keys
export const proctoringKeys = {
  all: ["proctoring"] as const,
  status: (sessionId: string) => [...proctoringKeys.all, "status", sessionId] as const,
  alerts: (sessionId: string) => [...proctoringKeys.all, "alerts", sessionId] as const,
};

// Hook to get proctoring status
export const useProctoringStatus = (
  sessionId: string | null,
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
) => {
  return useQuery({
    queryKey: proctoringKeys.status(sessionId || ""),
    queryFn: () => getProctoringStatus(sessionId!),
    enabled: options?.enabled && !!sessionId,
    refetchInterval: options?.refetchInterval || false,
    staleTime: 5000, // 5 seconds
  });
};

// Hook to get alerts
export const useAlerts = (
  sessionId: string | null,
  limit: number = 100,
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
) => {
  return useQuery({
    queryKey: [...proctoringKeys.alerts(sessionId || ""), limit],
    queryFn: () => getAlerts(sessionId!, limit),
    enabled: options?.enabled && !!sessionId,
    refetchInterval: options?.refetchInterval || false,
    staleTime: 3000, // 3 seconds
  });
};

// Hook to create an alert
export const useCreateAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      alert,
    }: {
      sessionId: string;
      alert: Omit<Alert, "alert_id">;
    }) => createAlert(sessionId, alert),
    onSuccess: (_, variables) => {
      // Invalidate alerts to refetch
      queryClient.invalidateQueries({
        queryKey: proctoringKeys.alerts(variables.sessionId),
      });
      queryClient.invalidateQueries({
        queryKey: proctoringKeys.status(variables.sessionId),
      });
    },
    onError: (error) => {
      console.error("Failed to create alert:", error);
    },
  });
};
