import { Button } from "@/components/ui/button";
import type { RetrievalMode } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  mode: RetrievalMode;
  onChange: (m: RetrievalMode) => void;
}

const MODES: { value: RetrievalMode; label: string; hint: string }[] = [
  { value: "lexical", label: "Lexical", hint: "BM25 keyword matching" },
  { value: "semantic", label: "Semantic", hint: "Soft overlap + heading boost" },
  { value: "hybrid", label: "Hybrid", hint: "Reciprocal rank fusion" },
];

export function RetrievalModeToggle({ mode, onChange }: Props) {
  return (
    <div className="inline-flex rounded-md border border-border bg-card p-0.5">
      {MODES.map((m) => (
        <Button
          key={m.value}
          variant="ghost"
          size="sm"
          title={m.hint}
          onClick={() => onChange(m.value)}
          className={cn(
            "h-7 rounded-sm px-3 text-xs font-medium",
            mode === m.value
              ? "bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"
              : "text-muted-foreground hover:bg-muted",
          )}
        >
          {m.label}
        </Button>
      ))}
    </div>
  );
}
