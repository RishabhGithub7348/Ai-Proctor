# TanStack Query (React Query) Implementation Guide

## Overview

We've implemented TanStack Query for all API calls in the AI Proctor system. This provides:
- Automatic caching and background refetching
- Optimistic updates
- Loading and error states
- Request deduplication
- Retry logic

## Project Structure

```
frontend/
├── lib/
│   ├── api/
│   │   ├── client.ts          # Axios client configuration
│   │   ├── types.ts           # TypeScript types
│   │   └── endpoints.ts       # API endpoint functions
│   ├── hooks/
│   │   ├── useSession.ts      # Session management hooks
│   │   ├── useProctoring.ts   # Proctoring hooks
│   │   ├── useWebSocket.ts    # WebSocket hook
│   │   ├── useHealthCheck.ts  # Health check hooks
│   │   └── index.ts           # Export all hooks
│   └── providers/
│       └── QueryProvider.tsx  # React Query provider
└── app/
    └── layout.tsx             # Root layout with QueryProvider
```

## Available Hooks

### 1. Session Management

#### `useCreateSession()`
Creates a new proctoring session.

```tsx
import { useCreateSession } from "@/lib/hooks";

const createSession = useCreateSession();

// Usage
const handleCreate = async () => {
  const session = await createSession.mutateAsync({
    candidate_name: "John Doe",
    interview_type: "technical",
    duration_minutes: 60,
  });

  console.log(session.session_id);
};

// Access state
createSession.isPending   // Loading state
createSession.isError     // Error state
createSession.error       // Error object
```

#### `useSession(sessionId)`
Fetches session details.

```tsx
import { useSession } from "@/lib/hooks";

const { data, isLoading, error } = useSession(sessionId);

// data: SessionResponse | undefined
// isLoading: boolean
// error: Error | null
```

#### `useEndSession()`
Ends a session.

```tsx
import { useEndSession } from "@/lib/hooks";

const endSession = useEndSession();

await endSession.mutateAsync(sessionId);
```

### 2. Proctoring Operations

#### `useProctoringStatus(sessionId, options)`
Gets current proctoring status with optional polling.

```tsx
import { useProctoringStatus } from "@/lib/hooks";

const { data: status } = useProctoringStatus(sessionId, {
  enabled: isActive,
  refetchInterval: 5000, // Poll every 5 seconds
});

// status: ProctoringStatus | undefined
```

#### `useAlerts(sessionId, limit, options)`
Fetches alerts for a session.

```tsx
import { useAlerts } from "@/lib/hooks";

const { data: alertsData } = useAlerts(sessionId, 100, {
  enabled: true,
  refetchInterval: 3000,
});

// alertsData: { session_id: string; alerts: Alert[] }
```

#### `useCreateAlert()`
Creates a new alert.

```tsx
import { useCreateAlert } from "@/lib/hooks";

const createAlert = useCreateAlert();

await createAlert.mutateAsync({
  sessionId,
  alert: {
    type: "eyes_looking_away",
    severity: "medium",
    message: "Candidate looking away",
    timestamp: new Date().toISOString(),
    requires_attention: false,
  },
});
```

### 3. WebSocket

#### `useWebSocket(sessionId, options)`
Manages WebSocket connection with auto-reconnect.

```tsx
import { useWebSocket } from "@/lib/hooks";

const {
  isConnected,
  lastMessage,
  sendMessage,
  sendBlob,
  connect,
  disconnect,
} = useWebSocket(sessionId, {
  onMessage: (data) => console.log("Received:", data),
  onAlert: (alerts) => console.log("New alerts:", alerts),
  onConnect: () => console.log("Connected"),
  onDisconnect: () => console.log("Disconnected"),
  onError: (error) => console.error("Error:", error),
});

// Send JSON
sendMessage({ type: "ping" });

// Send video frame
sendBlob(blob);
```

### 4. Health Check

#### `useHealthCheck()`
Basic health check.

```tsx
import { useHealthCheck } from "@/lib/hooks";

const { data: health } = useHealthCheck();
// health: { status: string; message: string; version: string }
```

#### `useDetailedHealthCheck()`
Detailed health information.

```tsx
import { useDetailedHealthCheck } from "@/lib/hooks";

const { data: detailedHealth } = useDetailedHealthCheck();
// detailedHealth: { status: string; environment: string; debug: boolean }
```

## Query Keys

Query keys are centralized for easy cache management:

```tsx
// Session keys
sessionKeys.all              // ["sessions"]
sessionKeys.detail(id)       // ["sessions", id]

// Proctoring keys
proctoringKeys.all           // ["proctoring"]
proctoringKeys.status(id)    // ["proctoring", "status", id]
proctoringKeys.alerts(id)    // ["proctoring", "alerts", id]

// Health keys
healthKeys.basic             // ["health", "basic"]
healthKeys.detailed          // ["health", "detailed"]
```

## Manual Cache Updates

### Invalidate queries
```tsx
import { useQueryClient } from "@tanstack/react-query";
import { sessionKeys } from "@/lib/hooks";

const queryClient = useQueryClient();

// Invalidate all sessions
queryClient.invalidateQueries({ queryKey: sessionKeys.all });

// Invalidate specific session
queryClient.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) });
```

### Update cache directly
```tsx
import { useQueryClient } from "@tanstack/react-query";

const queryClient = useQueryClient();

// Set data in cache
queryClient.setQueryData(sessionKeys.detail(sessionId), newData);

// Get data from cache
const data = queryClient.getQueryData(sessionKeys.detail(sessionId));
```

## Configuration

### Global defaults (in QueryProvider.tsx)
```tsx
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,        // 1 minute
      refetchOnWindowFocus: false,
      retry: 1,
    },
    mutations: {
      retry: 1,
    },
  },
});
```

### Per-hook configuration
```tsx
const { data } = useSession(sessionId, {
  staleTime: 30000,     // Override staleTime
  retry: 3,             // Override retry count
  enabled: !!sessionId, // Conditional fetching
  refetchInterval: 5000, // Auto-refetch every 5s
});
```

## Best Practices

### 1. Always provide query keys
```tsx
// Good
queryKey: sessionKeys.detail(sessionId)

// Bad
queryKey: ["session", sessionId]
```

### 2. Use enabled option for conditional queries
```tsx
const { data } = useSession(sessionId, {
  enabled: !!sessionId, // Only fetch if sessionId exists
});
```

### 3. Handle loading and error states
```tsx
const { data, isLoading, error } = useSession(sessionId);

if (isLoading) return <Spinner />;
if (error) return <Error message={error.message} />;
return <SessionDetails data={data} />;
```

### 4. Use mutations for data modification
```tsx
// Good - using mutation
const createSession = useCreateSession();
await createSession.mutateAsync(data);

// Bad - direct API call
await createSession(data);
```

### 5. Leverage optimistic updates
```tsx
const updateSession = useMutation({
  mutationFn: updateSessionAPI,
  onMutate: async (newData) => {
    // Optimistically update cache
    await queryClient.cancelQueries({ queryKey: sessionKeys.detail(id) });
    const previous = queryClient.getQueryData(sessionKeys.detail(id));
    queryClient.setQueryData(sessionKeys.detail(id), newData);
    return { previous };
  },
  onError: (err, newData, context) => {
    // Rollback on error
    queryClient.setQueryData(sessionKeys.detail(id), context.previous);
  },
});
```

## DevTools

React Query DevTools are included in development mode. Access them via the floating icon in the bottom-right corner.

Features:
- View all queries and their states
- See cached data
- Force refetch
- Explore query timeline

## Environment Variables

```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Example: Complete Interview Flow

```tsx
"use client";

import {
  useCreateSession,
  useEndSession,
  useWebSocket,
  useProctoringStatus,
} from "@/lib/hooks";

export default function InterviewPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Hooks
  const createSession = useCreateSession();
  const endSession = useEndSession();
  const { isConnected, sendBlob } = useWebSocket(sessionId);
  const { data: status } = useProctoringStatus(sessionId, {
    enabled: !!sessionId,
    refetchInterval: 5000,
  });

  // Start session
  const handleStart = async () => {
    const session = await createSession.mutateAsync({
      candidate_name: "John Doe",
      interview_type: "technical",
    });
    setSessionId(session.session_id);
  };

  // End session
  const handleEnd = async () => {
    if (sessionId) {
      await endSession.mutateAsync(sessionId);
      setSessionId(null);
    }
  };

  return (
    <div>
      <button onClick={handleStart}>Start</button>
      <button onClick={handleEnd}>End</button>
      <p>Connected: {isConnected ? "Yes" : "No"}</p>
      <p>Status: {status?.is_active ? "Active" : "Inactive"}</p>
    </div>
  );
}
```

## Troubleshooting

### Queries not refetching
- Check `staleTime` configuration
- Ensure `enabled` option is set correctly
- Verify query key is consistent

### WebSocket not connecting
- Check WS URL in environment variables
- Verify backend is running
- Check browser console for errors

### Cache not updating
- Use `invalidateQueries` after mutations
- Check query keys match exactly
- Use DevTools to inspect cache

---

For more information, visit: https://tanstack.com/query/latest
