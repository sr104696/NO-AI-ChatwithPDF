import { Progress } from "@/components/ui/progress";
import type { IngestProgress } from "@/hooks/useIngest";

export function IngestProgressBar({ progress }: { progress: IngestProgress }) {
  if (progress.stage === "idle") return null;
  const isError = progress.stage === "error";
  return (
    <div className="rounded-md border border-shell-border bg-shell-muted/40 p-3 text-shell-foreground">
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="font-medium capitalize">{progress.stage}</span>
        <span className="font-mono text-shell-muted-foreground">{progress.pct}%</span>
      </div>
      <Progress value={progress.pct} className={isError ? "bg-destructive/30" : "bg-shell-muted"} />
      {progress.message && (
        <div className={`mt-1 text-xs ${isError ? "text-destructive" : "text-shell-muted-foreground"}`}>
          {progress.message}
        </div>
      )}
    </div>
  );
}
