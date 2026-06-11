import { AlertTriangle, RefreshCw } from "lucide-react";

import { DeloadCard } from "@/components/DeloadCard";
import { NoApiKeyNote } from "@/components/NoApiKeyCard";
import { StreamingNote } from "@/components/StreamingNote";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCoaching } from "@/hooks/useCoaching";
import { MUSCLE_PRESETS, type NextSessionPlan } from "@/lib/api";
import { formatWeight, type Units } from "@/lib/units";
import { cn } from "@/lib/utils";

interface Props {
  units: Units;
  preset: string;
  onPresetChange: (preset: string) => void;
}

export function CoachingCard({ units, preset, onPresetChange }: Props) {
  const muscles = MUSCLE_PRESETS[preset];
  const path = muscles
    ? `/coaching/next-session?muscles=${muscles.join(",")}`
    : "/coaching/next-session";
  const coaching = useCoaching<NextSessionPlan>(path, { auto: true });
  const plan = coaching.content;

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <CardTitle>Today's coaching</CardTitle>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground"
          onClick={() => void coaching.generate()}
          disabled={coaching.phase === "streaming" || coaching.phase === "no_key"}
          aria-label="Regenerate plan"
        >
          <RefreshCw size={15} className={cn(coaching.phase === "streaming" && "animate-spin")} />
        </Button>
      </div>

      <div className="no-scrollbar -mx-1 mb-3 flex gap-1.5 overflow-x-auto px-1">
        {Object.keys(MUSCLE_PRESETS).map((p) => (
          <button
            key={p}
            onClick={() => onPresetChange(p)}
            className={cn(
              "shrink-0 rounded-full px-3 py-1 text-xs font-medium",
              p === preset ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
            )}
          >
            {p}
          </button>
        ))}
      </div>

      {coaching.phase === "loading" && (
        <div className="space-y-2">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {coaching.phase === "streaming" && <StreamingNote streamText={coaching.streamText} />}

      {coaching.phase === "no_key" && <NoApiKeyNote />}

      {coaching.phase === "error" && (
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle size={16} /> {coaching.error}
          </div>
          <Button variant="outline" size="sm" onClick={() => void coaching.generate()}>
            Try again
          </Button>
        </div>
      )}

      {coaching.phase === "ready" && plan && (
        <div className="space-y-3">
          <div>
            <div className="text-base font-semibold">{plan.session_focus}</div>
            {coaching.request?.muscles && (
              <div className="mt-1 flex flex-wrap gap-1">
                {coaching.request.muscles.map((m) => (
                  <Badge key={m} variant="muted">
                    {m}
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">{plan.coaching_note}</p>

          <div className="divide-y divide-border rounded-lg border border-border">
            {plan.exercises.map((ex, i) => (
              <div key={i} className="p-3">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-medium">{ex.exercise_name}</span>
                  <Badge variant="outline">RPE {ex.rpe_target}</Badge>
                </div>
                <div className="mt-0.5 text-sm text-primary">
                  {ex.sets} × {ex.target_reps} @ {formatWeight(ex.target_weight_kg, units)}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">{ex.progression_reason}</div>
              </div>
            ))}
          </div>

          {plan.deload_recommended && (
            <div className="space-y-2 rounded-lg border border-warning/40 bg-warning/10 p-3">
              <div className="flex items-center gap-2 text-sm font-medium text-warning">
                <AlertTriangle size={16} /> Deload recommended
              </div>
              {plan.deload_reason && (
                <p className="text-xs text-muted-foreground">{plan.deload_reason}</p>
              )}
              <DeloadCard units={units} compact />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
