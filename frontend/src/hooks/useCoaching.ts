import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, type CoachingEnvelope } from "@/lib/api";
import { streamCoaching } from "@/lib/stream";

export type CoachingPhase =
  | "loading"
  | "streaming"
  | "ready"
  | "stale"
  | "no_key"
  | "insufficient"
  | "empty"
  | "error";

/**
 * Coaching cards follow a two-step protocol:
 *   GET  <path>           → fresh cached snapshot, or "stale" (generate needed)
 *   POST <path>/generate  → NDJSON stream; result is cached server-side
 *
 * With `auto`, generation kicks off as soon as a stale envelope arrives, so
 * the card streams in without blocking navigation.
 */
export function useCoaching<T>(path: string, { auto = false } = {}) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["coaching", path],
    queryFn: () => api.coachingGet<T>(path),
  });

  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const autoStarted = useRef<Set<string>>(new Set());

  const generate = useCallback(async () => {
    setStreaming(true);
    setError(null);
    setStreamText("");
    try {
      const result = await streamCoaching<T>(`${path}/generate`, setStreamText);
      const envelope: CoachingEnvelope<T> = {
        status: "fresh",
        content: result.content,
        generated_at: result.generated_at,
        request: result.request,
      };
      qc.setQueryData(["coaching", path], envelope);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStreaming(false);
    }
  }, [path, qc]);

  useEffect(() => {
    if (!auto) return;
    if (query.data?.status === "stale" && !autoStarted.current.has(path) && !streaming) {
      autoStarted.current.add(path);
      void generate();
    }
  }, [auto, query.data, path, streaming, generate]);

  const data = query.data;
  let phase: CoachingPhase;
  if (query.isLoading) phase = "loading";
  else if (streaming) phase = "streaming";
  else if (error) phase = "error";
  else if (data?.status === "fresh") phase = "ready";
  else if (data?.status === "no_api_key") phase = "no_key";
  else if (data?.status === "insufficient_data") phase = "insufficient";
  else if (data?.status === "empty") phase = "empty";
  else if (data?.status === "stale") phase = auto ? "streaming" : "stale";
  else phase = query.isError ? "error" : "loading";

  return {
    phase,
    content: data?.status === "fresh" ? data.content : undefined,
    cachedContent: data?.cached_content,
    generatedAt: data?.generated_at,
    request: data?.request,
    detail: data?.detail,
    streamText,
    error: error ?? (query.error instanceof Error ? query.error.message : null),
    generate,
  };
}
