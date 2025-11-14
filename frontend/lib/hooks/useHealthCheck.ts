import { useQuery } from "@tanstack/react-query";
import { healthCheck, detailedHealthCheck } from "@/lib/api/endpoints";

// Query keys
export const healthKeys = {
  basic: ["health", "basic"] as const,
  detailed: ["health", "detailed"] as const,
};

// Hook for basic health check
export const useHealthCheck = (options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: healthKeys.basic,
    queryFn: healthCheck,
    enabled: options?.enabled ?? true,
    staleTime: 60000, // 1 minute
    retry: 1,
  });
};

// Hook for detailed health check
export const useDetailedHealthCheck = (options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: healthKeys.detailed,
    queryFn: detailedHealthCheck,
    enabled: options?.enabled ?? true,
    staleTime: 60000, // 1 minute
    retry: 1,
  });
};
