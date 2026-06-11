import { Sparkles } from "lucide-react";

import { streamPreview } from "@/lib/stream";

/** Shows coach text materializing from a partially-streamed JSON response. */
export function StreamingNote({ streamText }: { streamText: string }) {
  const preview = streamPreview(streamText);
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-xs text-primary">
        <Sparkles size={14} className="animate-pulse" />
        Coach is thinking…
      </div>
      {preview && (
        <p className="stream-cursor text-sm leading-relaxed text-muted-foreground">{preview}</p>
      )}
    </div>
  );
}
