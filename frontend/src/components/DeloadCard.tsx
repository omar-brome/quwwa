import { BatteryLow } from "lucide-react";

import { NoApiKeyNote } from "@/components/NoApiKeyCard";
import { StreamingNote } from "@/components/StreamingNote";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useCoaching } from "@/hooks/useCoaching";
import type { DeloadAdvice } from "@/lib/api";
import type { Units } from "@/lib/units";

/** Deload advisor. Renders inline ("Am I overtraining?") or compact when
 * embedded under a next-session deload recommendation. */
export function DeloadCard({ compact = false }: { units?: Units; compact?: boolean }) {
  const coaching = useCoaching<DeloadAdvice>("/coaching/deload-check");
  const advice = coaching.content;

  if (coaching.phase === "insufficient" && compact) return null;

  return (
    <div className={compact ? "" : "space-y-2"}>
      {coaching.phase === "stale" && (
        <Button variant="outline" size="sm" onClick={() => void coaching.generate()}>
          <BatteryLow size={15} /> Am I overtraining?
        </Button>
      )}
      {coaching.phase === "streaming" && <StreamingNote streamText={coaching.streamText} />}
      {coaching.phase === "no_key" && !compact && <NoApiKeyNote />}
      {coaching.phase === "insufficient" && (
        <p className="text-xs text-muted-foreground">{coaching.detail}</p>
      )}
      {coaching.phase === "error" && (
        <p className="text-xs text-destructive">{coaching.error}</p>
      )}
      {coaching.phase === "ready" && advice && (
        <div className="space-y-1.5 text-sm">
          <div className="flex items-center gap-2">
            <span className="font-medium">
              {advice.deload_needed ? "Deload needed" : "No deload needed"}
            </span>
            <Badge variant={advice.deload_needed ? "warning" : "success"}>
              {advice.confidence} confidence
            </Badge>
            {advice.deload_type && <Badge variant="muted">{advice.deload_type}</Badge>}
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground">{advice.rationale}</p>
          {advice.deload_protocol && (
            <p className="rounded-md bg-muted/60 p-2 text-xs">{advice.deload_protocol}</p>
          )}
        </div>
      )}
    </div>
  );
}
