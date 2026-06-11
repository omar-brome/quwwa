import { Minus, Plus } from "lucide-react";

import { cn } from "@/lib/utils";

interface StepperProps {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  step: number;
  min?: number;
  decimals?: number;
}

/** Number input with ± buttons — fat-finger friendly for mid-set logging. */
export function Stepper({ label, value, onChange, step, min = 0, decimals = 1 }: StepperProps) {
  const nudge = (dir: 1 | -1) => {
    const next = Math.max(min, (value ?? 0) + dir * step);
    onChange(Math.round(next * 10 ** decimals) / 10 ** decimals);
  };
  return (
    <div className="flex-1">
      <div className="mb-1 text-center text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => nudge(-1)}
          className="flex h-11 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground active:bg-border"
          aria-label={`decrease ${label}`}
        >
          <Minus size={16} />
        </button>
        <input
          inputMode="decimal"
          value={value ?? ""}
          onChange={(e) => {
            const raw = e.target.value.replace(",", ".");
            if (raw === "") return onChange(null);
            const parsed = Number(raw);
            if (!Number.isNaN(parsed)) onChange(parsed);
          }}
          className="h-11 w-full min-w-0 rounded-lg border border-border bg-muted/50 text-center text-base font-semibold tabular-nums focus:outline-none focus:ring-2 focus:ring-primary/60"
        />
        <button
          type="button"
          onClick={() => nudge(1)}
          className="flex h-11 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground active:bg-border"
          aria-label={`increase ${label}`}
        >
          <Plus size={16} />
        </button>
      </div>
    </div>
  );
}

interface RpeInputProps {
  value: number | null;
  onChange: (value: number | null) => void;
}

/** Optional by design: tapping the active chip clears it. */
export function RpeInput({ value, onChange }: RpeInputProps) {
  return (
    <div>
      <div className="mb-1 text-center text-[11px] uppercase tracking-wide text-muted-foreground">
        RPE <span className="normal-case">(optional)</span>
      </div>
      <div className="flex gap-1">
        {[6, 7, 8, 9, 10].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(value === n ? null : n)}
            className={cn(
              "h-9 flex-1 rounded-lg text-sm font-semibold tabular-nums",
              value === n ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
            )}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}
