import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createSession,
  getSession,
  endSession,
} from "@/lib/api/endpoints";
import { SessionCreate } from "@/lib/api/types";

// Query keys
export const sessionKeys = {
  all: ["sessions"] as const,
  detail: (id: string) => [...sessionKeys.all, id] as const,
};

// Hook to create a new session
export const useCreateSession = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionData: SessionCreate) => createSession(sessionData),
    onSuccess: (data) => {
      // Invalidate and refetch sessions list
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
      // Set the data in cache for immediate access
      queryClient.setQueryData(sessionKeys.detail(data.session_id), data);
    },
    onError: (error) => {
      console.error("Failed to create session:", error);
    },
  });
};

// Hook to get session details
export const useSession = (sessionId: string | null) => {
  return useQuery({
    queryKey: sessionKeys.detail(sessionId || ""),
    queryFn: () => getSession(sessionId!),
    enabled: !!sessionId, // Only run if sessionId exists
    staleTime: 30000, // Consider data fresh for 30 seconds
    retry: 2,
  });
};

// Hook to end a session
export const useEndSession = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => endSession(sessionId),
    onSuccess: (_, sessionId) => {
      // Invalidate the session data
      queryClient.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) });
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
    onError: (error) => {
      console.error("Failed to end session:", error);
    },
  });
};
