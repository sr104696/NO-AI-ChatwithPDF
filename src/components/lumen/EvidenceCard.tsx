import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  citation: Citation;
  index: number;
  active: boolean;
  onHover: (chunkId: string | null) => void;
  onClick: (c: Citation) => void;
}

export function EvidenceCard({ citation, index, active, onHover, onClick }: Props) {
  const lex = Math.round(citation.lexical * 100);
  const sem = Math.round(citation.semantic * 100);
  const provenance: "lexical" | "semantic" | "hybrid" =
    lex > 0 && sem === 0 ? "lexical" : sem > 0 && lex === 0 ? "semantic" : "hybrid";
  const provColor =
    provenance === "lexical"
      ? "bg-highlight-lexical"
      : provenance === "semantic"
      ? "bg-highlight-semantic"
      : "bg-highlight-hybrid";

  return (
    <button
      onMouseEnter={() => onHover(citation.chunkId)}
      onMouseLeave={() => onHover(null)}
      onClick={() => onClick(citation)}
      className={cn(
        "block w-full rounded-md border border-shell-border/60 bg-shell-muted/40 p-3 text-left text-sm transition hover:border-shell-accent/60 hover:bg-shell-muted",
        active && "border-shell-accent bg-shell-muted ring-1 ring-shell-accent/50",
      )}
    >
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[10px] uppercase tracking-widest text-shell-muted-foreground">
        <span className="font-mono">
          #{index + 1} · p.{citation.page}
          {citation.heading ? ` · ${citation.heading.slice(0, 40)}` : ""}
        </span>
        <span className="flex items-center gap-1">
          <span className={cn("h-1.5 w-1.5 rounded-full", provColor)} />
          <span className="font-mono">{provenance}</span>
        </span>
      </div>
      <p className="line-clamp-3 text-shell-foreground/90">{citation.snippet}</p>
      <div className="mt-2 flex items-center gap-1">
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-shell-muted">
          <div
            className="h-full bg-highlight-lexical"
            style={{ width: `${lex}%` }}
            title={`lexical ${lex}%`}
          />
        </div>
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-shell-muted">
          <div
            className="h-full bg-highlight-semantic"
            style={{ width: `${sem}%` }}
            title={`semantic ${sem}%`}
          />
        </div>
      </div>
    </button>
  );
}
