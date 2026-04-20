import { useEffect, useMemo, useRef } from "react";
import type { Chunk, Citation } from "@/lib/types";
import { tokenize, normalize } from "@/lib/text";
import { cn } from "@/lib/utils";

interface Props {
  chunks: Chunk[];
  activeCitation: Citation | null;
  hoveredChunkId: string | null;
}

function highlightTokens(text: string, matched: string[]): React.ReactNode {
  if (!matched.length) return text;
  // Build a regex that matches whole words whose stem is in `matched`.
  // We highlight by walking word positions instead of regex on stems.
  const wordRe = /[A-Za-z0-9'-]+|[^A-Za-z0-9'-]+/g;
  const parts: React.ReactNode[] = [];
  let m: RegExpExecArray | null;
  let i = 0;
  const matchedSet = new Set(matched);
  while ((m = wordRe.exec(text))) {
    const w = m[0];
    if (/[A-Za-z0-9]/.test(w[0])) {
      const tok = tokenize(w)[0];
      if (tok && matchedSet.has(tok)) {
        parts.push(
          <mark key={i++} className="lumen-hl">
            {w}
          </mark>,
        );
        continue;
      }
    }
    parts.push(<span key={i++}>{w}</span>);
  }
  return parts;
}

export function DocumentReader({ chunks, activeCitation, hoveredChunkId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const refs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Group chunks by page for sticky page headers
  const grouped = useMemo(() => {
    const map = new Map<number, Chunk[]>();
    for (const c of chunks) {
      const arr = map.get(c.page) ?? [];
      arr.push(c);
      map.set(c.page, arr);
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }, [chunks]);

  useEffect(() => {
    if (!activeCitation) return;
    const el = refs.current.get(activeCitation.chunkId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.remove("lumen-chunk-flash");
      // Reflow to restart animation
      void el.offsetWidth;
      el.classList.add("lumen-chunk-flash");
    }
  }, [activeCitation]);

  return (
    <div ref={containerRef} className="h-full overflow-y-auto bg-background">
      <div className="mx-auto max-w-3xl px-8 py-10">
        {grouped.map(([page, list]) => {
          const headingShown = new Set<string>();
          return (
            <section key={page} className="mb-10">
              <div className="sticky top-0 z-10 -mx-8 mb-4 border-b border-border/60 bg-background/85 px-8 py-2 backdrop-blur">
                <span className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
                  Page {page}
                </span>
              </div>
              <div className="reader-prose">
                {list.map((c) => {
                  const isActive = activeCitation?.chunkId === c.id;
                  const isHover = hoveredChunkId === c.id;
                  const matched = isActive && activeCitation ? activeCitation.matched : [];
                  const showHeading = c.heading && !headingShown.has(c.heading);
                  if (c.heading) headingShown.add(c.heading);
                  return (
                    <div key={c.id}>
                      {showHeading && <h2>{c.heading}</h2>}
                      <p
                        ref={(el) => {
                          if (el) refs.current.set(c.id, el);
                        }}
                        className={cn(
                          "rounded-md transition-colors",
                          isActive && "bg-highlight-hybrid/15 ring-1 ring-highlight-hybrid/40",
                          !isActive && isHover && "bg-muted",
                        )}
                      >
                        {highlightTokens(c.text, matched)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
        <div className="py-8 text-center font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          end of document · {chunks.length} passages indexed
        </div>
      </div>
    </div>
  );
}

// Avoid unused warning if normalize not imported elsewhere
void normalize;
