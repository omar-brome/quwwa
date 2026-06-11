import { Check, CircleAlert } from "lucide-react";

import { StreamingNote } from "@/components/StreamingNote";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCoaching } from "@/hooks/useCoaching";
import type { WeeklyReview } from "@/lib/api";

const STATUS_VARIANT = { under: "warning", optimal: "success", over: "destructive" } as const;

export function WeeklyReviewCard() {
  const coaching = useCoaching<WeeklyReview>("/coaching/weekly-review", { auto: true });
  const review = coaching.content;

  // Nothing logged this week (or AI not configured): the home screen stays clean.
  if (["empty", "no_key", "insufficient", "error"].includes(coaching.phase)) return null;

  return (
    <Card>
      <CardTitle className="mb-3">This week</CardTitle>
      {coaching.phase === "loading" && <Skeleton className="h-16 w-full" />}
      {coaching.phase === "streaming" && <StreamingNote streamText={coaching.streamText} />}
      {coaching.phase === "ready" && review && (
        <div className="space-y-3">
          <p className="font-medium leading-snug">{review.headline}</p>
          <div className="space-y-1.5">
            {review.positives.map((p, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                <Check size={15} className="mt-0.5 shrink-0 text-success" /> {p}
              </div>
            ))}
            {review.concerns.map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                <CircleAlert size={15} className="mt-0.5 shrink-0 text-warning" /> {c}
              </div>
            ))}
          </div>
          <div className="rounded-lg bg-muted/60 p-3 text-sm">
            <span className="font-medium text-primary">Next week: </span>
            {review.focus_next_week}
          </div>
          {review.volume_status.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {review.volume_status.map((v) => (
                <Badge key={v.muscle_group} variant={STATUS_VARIANT[v.status]}>
                  {v.muscle_group}: {v.status}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
