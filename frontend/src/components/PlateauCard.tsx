import { StreamingNote } from "@/components/StreamingNote";
import { NoApiKeyNote } from "@/components/NoApiKeyCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCoaching } from "@/hooks/useCoaching";
import type { PlateauReport } from "@/lib/api";

const STATUS_VARIANT = {
  progressing: "success",
  plateaued: "warning",
  fatigued: "warning",
  regressing: "destructive",
} as const;

export function PlateauCard({ exerciseId }: { exerciseId: string }) {
  const coaching = useCoaching<PlateauReport>(`/coaching/plateau/${exerciseId}`, {
    auto: true,
  });
  const report = coaching.content;

  return (
    <Card>
      <CardTitle className="mb-3">Progression check</CardTitle>
      {coaching.phase === "loading" && <Skeleton className="h-12 w-full" />}
      {coaching.phase === "streaming" && <StreamingNote streamText={coaching.streamText} />}
      {coaching.phase === "no_key" && <NoApiKeyNote />}
      {coaching.phase === "insufficient" && (
        <p className="text-sm text-muted-foreground">{coaching.detail}</p>
      )}
      {coaching.phase === "error" && (
        <p className="text-sm text-destructive">{coaching.error}</p>
      )}
      {coaching.phase === "ready" && report && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_VARIANT[report.status]}>{report.status}</Badge>
            {report.status !== "progressing" && (
              <Badge variant="outline">{report.urgency} urgency</Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground">{report.trend_summary}</p>
          <p className="rounded-lg bg-muted/60 p-3 text-sm">{report.recommendation}</p>
        </div>
      )}
    </Card>
  );
}
