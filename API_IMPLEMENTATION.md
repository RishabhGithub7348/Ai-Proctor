# API Implementation with TanStack Query

## Overview

The AI Proctor frontend now uses **TanStack Query (React Query)** for all API calls instead of plain fetch/axios. This provides better developer experience and user experience through:

✅ **Automatic Caching** - Reduces unnecessary API calls
✅ **Background Refetching** - Keeps data fresh automatically
✅ **Loading & Error States** - Built-in state management
✅ **Optimistic Updates** - Instant UI feedback
✅ **Request Deduplication** - Prevents duplicate requests
✅ **Auto Retry** - Handles network failures gracefully
✅ **DevTools** - Visual debugging of queries

## Architecture

### Before (Plain API Calls)
```tsx
// ❌ Manual state management
const [data, setData] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);

const fetchData = async () => {
  setLoading(true);
  try {
    const response = await fetch('/api/session');
    const data = await response.json();
    setData(data);
  } catch (err) {
    setError(err);
  } finally {
    setLoading(false);
  }
};
```

### After (TanStack Query)
```tsx
// ✅ Automatic state management
import { useSession } from "@/lib/hooks";

const { data, isLoading, error } = useSession(sessionId);
// Done! Caching, refetching, error handling all automatic
```

## File Structure

```
frontend/lib/
├── api/
│   ├── client.ts       # Axios instance with interceptors
│   ├── types.ts        # All TypeScript interfaces
│   └── endpoints.ts    # API endpoint functions
├── hooks/
│   ├── useSession.ts       # Session CRUD operations
│   ├── useProctoring.ts    # Proctoring status & alerts
│   ├── useWebSocket.ts     # WebSocket management
│   ├── useHealthCheck.ts   # Health checks
│   └── index.ts            # Export all hooks
└── providers/
    └── QueryProvider.tsx   # TanStack Query setup
```

## Key Features Implemented

### 1. Session Management
```tsx
// Create session
const createSession = useCreateSession();
const session = await createSession.mutateAsync({
  candidate_name: "John Doe",
  interview_type: "technical",
});

// Get session
const { data: session } = useSession(sessionId);

// End session
const endSession = useEndSession();
await endSession.mutateAsync(sessionId);
```

### 2. Real-time Proctoring
```tsx
// Get status with auto-polling
const { data: status } = useProctoringStatus(sessionId, {
  enabled: true,
  refetchInterval: 5000, // Poll every 5 seconds
});

// Get alerts
const { data: alerts } = useAlerts(sessionId, 100);

// Create alert
const createAlert = useCreateAlert();
await createAlert.mutateAsync({ sessionId, alert });
```

### 3. WebSocket Integration
```tsx
const {
  isConnected,
  sendMessage,
  sendBlob,
  disconnect,
} = useWebSocket(sessionId, {
  onMessage: (data) => console.log(data),
  onAlert: (alerts) => setAlerts(alerts),
  onConnect: () => console.log("Connected"),
});

// Auto-reconnect on disconnect
// Exponential backoff retry
// Clean disconnect on unmount
```

### 4. Health Monitoring
```tsx
// Basic health check
const { data: health } = useHealthCheck();

// Detailed health
const { data: detailed } = useDetailedHealthCheck();
```

## Benefits

### For Developers

1. **Less Boilerplate**
   - No manual state management
   - No manual error handling
   - No manual loading states

2. **Better DX**
   - TypeScript autocomplete
   - DevTools for debugging
   - Centralized configuration

3. **Maintainability**
   - Single source of truth
   - Reusable hooks
   - Consistent patterns

### For Users

1. **Faster Experience**
   - Cached data = instant loading
   - Background refetching = always fresh
   - Optimistic updates = instant feedback

2. **More Reliable**
   - Auto-retry on failure
   - Request deduplication
   - Smart refetching

3. **Better UX**
   - Proper loading states
   - Error boundaries
   - Smooth transitions

## Axios Client Configuration

**File**: `frontend/lib/api/client.ts`

Features:
- Base URL configuration
- Request/Response interceptors
- Authentication token handling
- Error handling
- Timeout configuration

```typescript
export const apiClient = axios.create({
  baseURL: "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
});

// Auto-add auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

## Query Keys Strategy

Centralized query keys for easy cache management:

```typescript
// Session keys
sessionKeys.all              // ["sessions"]
sessionKeys.detail(id)       // ["sessions", id]

// Proctoring keys
proctoringKeys.all           // ["proctoring"]
proctoringKeys.status(id)    // ["proctoring", "status", id]
proctoringKeys.alerts(id)    // ["proctoring", "alerts", id]
```

Benefits:
- Easy cache invalidation
- Type-safe query keys
- Consistent naming
- Easy refactoring

## Cache Management

### Automatic Cache Invalidation
```typescript
// After creating session
onSuccess: (data) => {
  queryClient.invalidateQueries({ queryKey: sessionKeys.all });
  queryClient.setQueryData(sessionKeys.detail(data.session_id), data);
}
```

### Manual Cache Updates
```typescript
const queryClient = useQueryClient();

// Invalidate specific query
queryClient.invalidateQueries({
  queryKey: proctoringKeys.status(sessionId)
});

// Update cache directly
queryClient.setQueryData(sessionKeys.detail(id), newData);
```

## Error Handling

### Global Error Handling
```typescript
// In QueryProvider
new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 60000,
    },
  },
});
```

### Per-Hook Error Handling
```typescript
const { data, error, isError } = useSession(sessionId);

if (isError) {
  return <ErrorMessage error={error} />;
}
```

## DevTools

React Query DevTools included in development:

```tsx
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

<QueryClientProvider client={queryClient}>
  {children}
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

Access via floating button in bottom-right corner.

## Environment Variables

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Migration Guide

### Old Code (Manual)
```tsx
const [session, setSession] = useState(null);
const [loading, setLoading] = useState(false);

const createSession = async () => {
  setLoading(true);
  try {
    const res = await fetch('/api/v1/session/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    const session = await res.json();
    setSession(session);
  } catch (error) {
    console.error(error);
  } finally {
    setLoading(false);
  }
};
```

### New Code (TanStack Query)
```tsx
import { useCreateSession } from "@/lib/hooks";

const createSession = useCreateSession();

const handleCreate = async () => {
  const session = await createSession.mutateAsync(data);
  // Done! Error handling, loading states all automatic
};

// Access states
createSession.isPending  // loading
createSession.isError    // error
createSession.data       // result
```

## Best Practices

1. **Always use hooks from `@/lib/hooks`**
   ```tsx
   import { useSession, useCreateSession } from "@/lib/hooks";
   ```

2. **Use `enabled` option for conditional queries**
   ```tsx
   const { data } = useSession(sessionId, {
     enabled: !!sessionId,
   });
   ```

3. **Handle loading and error states**
   ```tsx
   if (isLoading) return <Spinner />;
   if (error) return <Error />;
   ```

4. **Use mutations for data modification**
   ```tsx
   const mutation = useCreateSession();
   await mutation.mutateAsync(data);
   ```

5. **Leverage polling for real-time data**
   ```tsx
   const { data } = useProctoringStatus(sessionId, {
     refetchInterval: 5000,
   });
   ```

## Resources

- [TanStack Query Docs](https://tanstack.com/query/latest)
- [TANSTACK_QUERY_GUIDE.md](./TANSTACK_QUERY_GUIDE.md) - Detailed guide
- [API Types](./frontend/lib/api/types.ts) - All TypeScript types
- [Custom Hooks](./frontend/lib/hooks/) - Implementation details

## Next Steps

Potential enhancements:
- [ ] Add optimistic updates
- [ ] Implement pagination
- [ ] Add infinite queries for alerts
- [ ] Setup query persistence
- [ ] Add prefetching for better UX
- [ ] Implement offline support

---

**Summary**: The AI Proctor frontend now has a professional, production-ready API layer with TanStack Query, providing excellent developer experience and user experience through automatic caching, background refetching, and smart state management.
