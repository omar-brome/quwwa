/** Consume an NDJSON coaching stream: deltas accumulate, last line is the result. */

export interface StreamResult<T> {
  content: T;
  generated_at: string;
  request?: Record<string, unknown>;
}

export async function streamCoaching<T>(
  url: string,
  onDelta: (accumulated: string) => void,
): Promise<StreamResult<T>> {
  const res = await fetch("/api" + url, { method: "POST" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  if (!res.body) throw new Error("Streaming not supported by this browser");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulated = "";
  let result: StreamResult<T> | null = null;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (!line) continue;
      const event = JSON.parse(line) as {
        type: string;
        text?: string;
        detail?: string;
        content?: T;
        generated_at?: string;
        request?: Record<string, unknown>;
      };
      if (event.type === "delta") {
        accumulated += event.text ?? "";
        onDelta(accumulated);
      } else if (event.type === "result") {
        result = {
          content: event.content as T,
          generated_at: event.generated_at ?? new Date().toISOString(),
          request: event.request,
        };
      } else if (event.type === "error") {
        throw new Error(event.detail ?? "Coaching generation failed");
      }
    }
  }
  if (!result) throw new Error("Stream ended without a result");
  return result;
}

/** Pull a human-readable preview out of partially-streamed JSON so the user
 * sees coach text appearing rather than raw braces. */
const PREVIEW_KEYS = ["coaching_note", "headline", "trend_summary", "rationale", "session_focus"];

export function streamPreview(partialJson: string): string | null {
  for (const key of PREVIEW_KEYS) {
    const match = partialJson.match(
      new RegExp(`"${key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)`),
    );
    if (match && match[1]) {
      try {
        return JSON.parse(`"${match[1].replace(/\\$/, "")}"`) as string;
      } catch {
        return match[1];
      }
    }
  }
  return null;
}
