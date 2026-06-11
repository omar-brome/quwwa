import { KeyRound } from "lucide-react";

export function NoApiKeyNote() {
  return (
    <div className="flex items-start gap-3 rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
      <KeyRound size={18} className="mt-0.5 shrink-0 text-warning" />
      <div>
        AI coaching is off — no Anthropic API key configured.
        <div className="mt-1 text-xs">
          Add <code className="text-foreground">ANTHROPIC_API_KEY</code> to{" "}
          <code className="text-foreground">backend/.env</code> (or the compose{" "}
          <code className="text-foreground">.env</code>) and restart the backend.
        </div>
      </div>
    </div>
  );
}
