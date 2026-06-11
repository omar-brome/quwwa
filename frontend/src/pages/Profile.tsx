import { Check, Sparkles, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { DeloadCard } from "@/components/DeloadCard";
import { Stepper } from "@/components/inputs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useHealth, useImportCsv, useProfile, useUpdateProfile } from "@/hooks/queries";
import { EQUIPMENT_TYPES, type Profile as ProfileType } from "@/lib/api";
import { cn } from "@/lib/utils";

const selectClass =
  "h-11 w-full rounded-lg border border-border bg-muted/50 px-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/60";

export function Profile() {
  const { data: profile, isLoading } = useProfile();
  const { data: health } = useHealth();
  const updateProfile = useUpdateProfile();
  const importCsv = useImportCsv();
  const fileInput = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState<Omit<ProfileType, "user_id"> | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (profile && !form) {
      const { user_id: _ignored, ...rest } = profile;
      setForm(rest);
    }
  }, [profile, form]);

  if (isLoading || !form) return <Skeleton className="mt-4 h-64 w-full" />;

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm({ ...form, [key]: value });
    setSaved(false);
  };

  const save = async () => {
    await updateProfile.mutateAsync(form);
    setSaved(true);
  };

  return (
    <div className="space-y-4">
      <header className="pt-2">
        <h1 className="text-xl font-bold">Profile</h1>
        <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Sparkles size={13} className="text-primary" />
          Everything here is fed straight into your AI coach — the more accurate it is, the
          better the coaching.
        </p>
      </header>

      <Card className="space-y-4">
        <div>
          <Label>Training goal</Label>
          <select
            className={selectClass}
            value={form.training_goal}
            onChange={(e) => set("training_goal", e.target.value as ProfileType["training_goal"])}
          >
            <option value="strength">Strength</option>
            <option value="hypertrophy">Hypertrophy</option>
            <option value="recomp">Recomp</option>
            <option value="endurance">Endurance</option>
          </select>
        </div>

        <div>
          <Label>Experience</Label>
          <select
            className={selectClass}
            value={form.experience}
            onChange={(e) => set("experience", e.target.value as ProfileType["experience"])}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <div>
          <Label>Training days per week</Label>
          <Stepper
            label=""
            value={form.training_days}
            onChange={(v) => set("training_days", Math.max(1, Math.min(7, Math.round(v ?? 1))))}
            step={1}
            min={1}
            decimals={0}
          />
        </div>

        <div>
          <Label>Available equipment</Label>
          <div className="flex flex-wrap gap-1.5">
            {EQUIPMENT_TYPES.map((eq) => (
              <button
                key={eq}
                type="button"
                onClick={() =>
                  set(
                    "equipment",
                    form.equipment.includes(eq)
                      ? form.equipment.filter((x) => x !== eq)
                      : [...form.equipment, eq],
                  )
                }
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-medium",
                  form.equipment.includes(eq)
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {eq}
              </button>
            ))}
          </div>
        </div>

        <div>
          <Label>Injury notes</Label>
          <Textarea
            placeholder="e.g. left shoulder impingement — the coach will never prescribe around it"
            value={form.injury_notes ?? ""}
            onChange={(e) => set("injury_notes", e.target.value || null)}
          />
        </div>

        <div>
          <Label>Units</Label>
          <div className="flex gap-1.5">
            {(["kg", "lbs"] as const).map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => set("units", u)}
                className={cn(
                  "h-10 flex-1 rounded-lg text-sm font-semibold",
                  form.units === u
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {u}
              </button>
            ))}
          </div>
        </div>

        <Button className="w-full" onClick={() => void save()} disabled={updateProfile.isPending}>
          {saved ? (
            <>
              <Check size={16} /> Saved
            </>
          ) : updateProfile.isPending ? (
            "Saving…"
          ) : (
            "Save profile"
          )}
        </Button>
        {updateProfile.isError && (
          <p className="text-xs text-destructive">
            {updateProfile.error instanceof Error ? updateProfile.error.message : "Save failed"}
          </p>
        )}
      </Card>

      <Card className="space-y-2">
        <CardTitle>Fatigue check</CardTitle>
        <DeloadCard units={form.units} />
      </Card>

      <Card className="space-y-3">
        <CardTitle>Import lift history</CardTitle>
        <p className="text-xs text-muted-foreground">
          Seed the coach with your existing numbers. CSV columns:{" "}
          <code className="text-foreground">date,exercise,weight_kg,reps</code> plus optional{" "}
          <code className="text-foreground">rpe,is_warmup,notes</code>. One session is created
          per date.
        </p>
        <input
          ref={fileInput}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) importCsv.mutate(file);
            e.target.value = "";
          }}
        />
        <Button
          variant="outline"
          onClick={() => fileInput.current?.click()}
          disabled={importCsv.isPending}
        >
          <Upload size={15} /> {importCsv.isPending ? "Importing…" : "Choose CSV"}
        </Button>
        {importCsv.data && (
          <div className="space-y-1 rounded-lg bg-muted/60 p-3 text-xs">
            <div>
              Imported <b>{importCsv.data.sets_created}</b> sets across{" "}
              <b>{importCsv.data.sessions_created}</b> sessions.
            </div>
            {importCsv.data.exercises_created.length > 0 && (
              <div className="text-muted-foreground">
                New exercises: {importCsv.data.exercises_created.join(", ")}
              </div>
            )}
            {importCsv.data.warnings.slice(0, 5).map((w, i) => (
              <div key={i} className="text-warning">
                {w}
              </div>
            ))}
          </div>
        )}
        {importCsv.isError && (
          <p className="text-xs text-destructive">
            {importCsv.error instanceof Error ? importCsv.error.message : "Import failed"}
          </p>
        )}
      </Card>

      <div className="flex items-center justify-center gap-2 pb-2 text-xs text-muted-foreground">
        AI coaching:
        {health?.ai_configured ? (
          <Badge variant="success">{health.model}</Badge>
        ) : (
          <Badge variant="warning">not configured</Badge>
        )}
      </div>
    </div>
  );
}
