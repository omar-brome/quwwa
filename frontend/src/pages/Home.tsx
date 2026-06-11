import { Play, TrendingDown } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { CoachingCard } from "@/components/CoachingCard";
import { SessionListItem } from "@/components/SessionListItem";
import { VolumeTargets } from "@/components/VolumeTargets";
import { WeeklyReviewCard } from "@/components/WeeklyReviewCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { usePlateauAlerts, useProfile, useSessions } from "@/hooks/queries";
import { useStartSessionFlow } from "@/hooks/useStartSession";
import { useActiveSession } from "@/stores/activeSession";

export function Home() {
  const { data: profile } = useProfile();
  const { data: sessions, isLoading: sessionsLoading } = useSessions(5);
  const { data: alerts } = usePlateauAlerts();
  const { startOrResume, starting, error, hasActive } = useStartSessionFlow();
  const activeStarted = useActiveSession((s) => s.startedAt);
  const [preset, setPreset] = useState("Auto");

  const units = profile?.units ?? "kg";

  return (
    <div className="space-y-4">
      <header className="flex items-center gap-3 pt-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary font-arabic text-lg font-bold text-primary-foreground">
          قوة
        </div>
        <div>
          <h1 className="text-xl font-bold leading-tight">Quwwa</h1>
          <p className="text-xs text-muted-foreground">Log it. The coach handles the rest.</p>
        </div>
      </header>

      {hasActive && (
        <button
          onClick={() => void startOrResume()}
          className="flex w-full items-center justify-between rounded-xl border border-primary/40 bg-primary/10 p-3 text-sm"
        >
          <span className="font-medium text-primary">Session in progress</span>
          <span className="text-xs text-muted-foreground">
            started{" "}
            {activeStarted &&
              new Date(activeStarted).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
            — tap to resume
          </span>
        </button>
      )}

      <CoachingCard units={units} preset={preset} onPresetChange={setPreset} />

      {alerts && alerts.alerts.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {alerts.alerts.map((a) => (
            <Link key={a.exercise_id} to={`/exercise/${a.exercise_id}`}>
              <Badge variant={a.status === "regressing" ? "destructive" : "warning"}>
                <TrendingDown size={12} /> {a.exercise_name}: {a.status}
              </Badge>
            </Link>
          ))}
        </div>
      )}

      <WeeklyReviewCard />
      <VolumeTargets />

      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Recent sessions
          </h2>
          {sessions && sessions.total > 5 && (
            <span className="text-xs text-muted-foreground">{sessions.total} total</span>
          )}
        </div>
        {sessionsLoading && <Skeleton className="h-20 w-full" />}
        {sessions?.items.map((s) => (
          <SessionListItem key={s.id} session={s} units={units} />
        ))}
        {sessions && sessions.items.length === 0 && (
          <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            No sessions yet — hit start and log your first set.
          </p>
        )}
      </section>

      {!hasActive && (
        <Button size="lg" className="w-full" onClick={() => void startOrResume()} disabled={starting}>
          <Play size={18} /> Start session
        </Button>
      )}
      {error && <p className="text-center text-xs text-destructive">{error}</p>}
    </div>
  );
}
