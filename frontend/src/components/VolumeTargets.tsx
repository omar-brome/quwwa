import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWeeklyVolume } from "@/hooks/queries";
import { cn } from "@/lib/utils";

export function VolumeTargets() {
  const { data, isLoading } = useWeeklyVolume();

  return (
    <Card>
      <CardTitle className="mb-3">Weekly sets vs target</CardTitle>
      {isLoading && <Skeleton className="h-24 w-full" />}
      {data && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
          {data.muscles
            .filter((m) => m.min_sets !== null || m.sets > 0)
            .map((m) => {
              const max = m.max_sets ?? Math.max(m.sets, 1);
              const pct = Math.min(100, (m.sets / max) * 100);
              const under = m.min_sets !== null && m.sets < m.min_sets;
              const over = m.max_sets !== null && m.sets > m.max_sets;
              return (
                <div key={m.muscle}>
                  <div className="mb-1 flex items-baseline justify-between text-xs">
                    <span className="capitalize text-muted-foreground">{m.muscle}</span>
                    <span
                      className={cn(
                        "tabular-nums",
                        over ? "text-destructive" : under ? "text-muted-foreground" : "text-success",
                      )}
                    >
                      {m.sets}
                      {m.min_sets !== null && (
                        <span className="text-muted-foreground">
                          /{m.min_sets}–{m.max_sets}
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        over ? "bg-destructive" : under ? "bg-primary/50" : "bg-success",
                      )}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </Card>
  );
}
