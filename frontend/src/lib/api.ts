import { useMutation, useQuery } from "@tanstack/react-query";
import type { UseMutationOptions, UseQueryOptions } from "@tanstack/react-query";

function isRealSessionId(id: string | null | undefined): id is string {
  if (!id) return false;
  const n = parseInt(id, 10);
  return Number.isInteger(n) && String(n) === id;
}

function toIntId(id: string): number {
  const n = parseInt(id, 10);
  if (!Number.isInteger(n) || String(n) !== id) {
    throw new Error(`invalid session id: ${id}`);
  }
  return n;
}

async function safeFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) message = `${message} - ${data.detail}`;
    } catch {}
    throw new Error(message);
  }
  return (await res.json()) as T;
}

export const getListSessionsQueryKey = () => ["/api/sessions"] as const;

export function useListSessions<TData = any, TError = unknown>(
  options?: { query?: UseQueryOptions<any, TError, TData> }
) {
  return useQuery<any, TError, TData>({
    queryKey: getListSessionsQueryKey(),
    queryFn: ({ signal }) => safeFetch<any[]>("/api/sessions", { signal }),
    retry: false,
    staleTime: 1000 * 30,
    ...options?.query,
  });
}

export const getGetEvidenceBlocksQueryKey = (sessionId: string) =>
  [`/api/media/evidence/${sessionId}`] as const;

export function useGetEvidenceBlocks<TData = any, TError = unknown>(
  sessionId: string | null | undefined,
  options?: { query?: UseQueryOptions<any, TError, TData> }
) {
  return useQuery<any, TError, TData>({
    queryKey: getGetEvidenceBlocksQueryKey(sessionId || ""),
    queryFn: ({ signal }) =>
      safeFetch<any[]>(`/api/media/evidence/${toIntId(sessionId!)}`, { signal }),
    enabled: isRealSessionId(sessionId),
    retry: false,
    ...options?.query,
  });
}

export const getGetMaterialsQueryKey = (sessionId: string) =>
  [`/api/media/session/${sessionId}/materials`] as const;

export function useGetMaterials<TData = any[], TError = unknown>(
  sessionId: string | null | undefined,
  options?: { query?: UseQueryOptions<any, TError, TData> }
) {
  return useQuery<any, TError, TData>({
    queryKey: getGetMaterialsQueryKey(sessionId || ""),
    queryFn: ({ signal }) =>
      safeFetch<any[]>(`/api/media/session/${toIntId(sessionId!)}/materials`, { signal }),
    enabled: isRealSessionId(sessionId),
    retry: false,
    ...options?.query,
  });
}

export const getGetSummaryResultQueryKey = (sessionId: string) =>
  [`/api/summary/result/${sessionId}`] as const;

export function useGetSummaryResult<TData = any, TError = unknown>(
  sessionId: string | null | undefined,
  options?: { query?: UseQueryOptions<any, TError, TData> }
) {
  return useQuery<any, TError, TData>({
    queryKey: getGetSummaryResultQueryKey(sessionId || ""),
    queryFn: ({ signal }) =>
      safeFetch<any>(`/api/summary/result/${toIntId(sessionId!)}`, { signal }),
    enabled: isRealSessionId(sessionId),
    retry: false,
    ...options?.query,
  });
}

export const useCreateSession = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { title?: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { title?: string }, TContext>({
    mutationFn: ({ title }) =>
      safeFetch<any>("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title || "Untitled" }),
      }),
    ...options?.mutation,
  });
};

export const useUploadFile = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<
      any,
      TError,
      { sessionId: string; file: File; sortOrder?: number },
      TContext
    >;
  }
) => {
  return useMutation<any, TError, { sessionId: string; file: File; sortOrder?: number }, TContext>({
    mutationFn: ({ sessionId, file, sortOrder = 0 }) => {
      const fd = new FormData();
      fd.append("session_id", String(toIntId(sessionId)));
      fd.append("sort_order", String(sortOrder));
      fd.append("file", file);
      return safeFetch<any>("/api/media/upload", { method: "POST", body: fd });
    },
    ...options?.mutation,
  });
};

export const useDownloadLink = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<
      any,
      TError,
      { sessionId: string; url: string },
      TContext
    >;
  }
) => {
  return useMutation<any, TError, { sessionId: string; url: string }, TContext>({
    mutationFn: ({ sessionId, url }) =>
      safeFetch<any>(`/api/media/download/${toIntId(sessionId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      }),
    ...options?.mutation,
  });
};

export const useProcessSession = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string }, TContext>({
    mutationFn: ({ sessionId }) =>
      safeFetch<any>(`/api/media/session/${toIntId(sessionId)}/process`, { method: "POST" }),
    ...options?.mutation,
  });
};

export const useDeleteSession = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string }, TContext>({
    mutationFn: ({ sessionId }) =>
      safeFetch<any>(`/api/sessions/${toIntId(sessionId)}`, { method: "DELETE" }),
    ...options?.mutation,
  });
};

export const useRenameSession = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string; title: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string; title: string }, TContext>({
    mutationFn: ({ sessionId, title }) =>
      safeFetch<any>(`/api/sessions/${toIntId(sessionId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      }),
    ...options?.mutation,
  });
};

export const useTranscribe = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string }, TContext>({
    mutationFn: ({ sessionId }) =>
      safeFetch<any>(`/api/speech/transcribe/${toIntId(sessionId)}`, { method: "POST" }),
    ...options?.mutation,
  });
};

export const useMatchEvidence = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string }, TContext>({
    mutationFn: ({ sessionId }) =>
      safeFetch<any>(`/api/summary/match/${toIntId(sessionId)}`, { method: "POST" }),
    ...options?.mutation,
  });
};

export const useGenerateSummary = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string }, TContext>({
    mutationFn: ({ sessionId }) =>
      safeFetch<any>(`/api/summary/generate/${toIntId(sessionId)}`, { method: "POST" }),
    ...options?.mutation,
  });
};

export const getGetSettingsQueryKey = () => ["/api/settings"] as const;

export function useGetSettings<TData = any, TError = unknown>(
  options?: { query?: UseQueryOptions<any, TError, TData> }
) {
  return useQuery<any, TError, TData>({
    queryKey: getGetSettingsQueryKey(),
    queryFn: ({ signal }) => safeFetch<any[]>("/api/settings", { signal }),
    retry: false,
    staleTime: 1000 * 30,
    ...options?.query,
  });
}

export const useUpdateSettings = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { settings: { key: string; value: string; is_required: boolean }[] }, TContext>;
  }
) => {
  return useMutation<any, TError, { settings: { key: string; value: string; is_required: boolean }[] }, TContext>({
    mutationFn: ({ settings }) =>
      safeFetch<any>("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings }),
      }),
    ...options?.mutation,
  });
};

export const getEphemeralQueryKey = () => ["/api/settings/ephemeral"] as const;

export function useGetEphemeral<TData = any, TError = unknown>(
  options?: { query?: UseQueryOptions<any, TError, TData> }
) {
  return useQuery<any, TError, TData>({
    queryKey: getEphemeralQueryKey(),
    queryFn: ({ signal }) => safeFetch<any>("/api/settings/ephemeral", { signal }),
    retry: false,
    staleTime: 1000 * 60,
    ...options?.query,
  });
}
