import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { EvidenceCard } from "./EvidenceCard";
import type { ChatMessage, Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  busy: boolean;
  activeCitation: Citation | null;
  onCitationHover: (chunkId: string | null) => void;
  onCitationClick: (c: Citation) => void;
}

export function ChatPane({
  messages,
  onSend,
  busy,
  activeCitation,
  onCitationHover,
  onCitationClick,
}: Props) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    const t = draft.trim();
    if (!t || busy) return;
    setDraft("");
    onSend(t);
  };

  return (
    <div className="flex h-full flex-col bg-shell text-shell-foreground">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <div className="mx-auto max-w-md py-16 text-center">
            <Sparkles className="mx-auto mb-3 h-6 w-6 text-shell-accent" />
            <h3 className="font-serif text-xl font-semibold">Ask the document anything.</h3>
            <p className="mt-2 text-sm text-shell-muted-foreground">
              Lumen finds passages using lexical + semantic ranking. Click any evidence card to
              jump to the source on the left.
            </p>
            <div className="mt-6 grid gap-2 text-left text-xs text-shell-muted-foreground">
              {["What is this document about?", "Summarize the introduction", "Find the conclusion"].map(
                (s) => (
                  <button
                    key={s}
                    onClick={() => onSend(s)}
                    className="rounded-md border border-shell-border bg-shell-muted/40 px-3 py-2 transition hover:border-shell-accent/60 hover:bg-shell-muted"
                  >
                    {s}
                  </button>
                ),
              )}
            </div>
          </div>
        ) : (
          <ul className="mx-auto flex max-w-2xl flex-col gap-5">
            {messages.map((m) => (
              <li key={m.id} className="animate-fade-in">
                <div
                  className={cn(
                    "mb-1 font-mono text-[10px] uppercase tracking-widest",
                    m.role === "user" ? "text-shell-accent" : "text-shell-muted-foreground",
                  )}
                >
                  {m.role}
                </div>
                <div
                  className={cn(
                    "rounded-lg px-3 py-2 text-sm",
                    m.role === "user"
                      ? "bg-shell-muted/60 text-shell-foreground"
                      : "bg-transparent text-shell-foreground/95",
                  )}
                >
                  {m.text}
                </div>
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {m.citations.map((c, i) => (
                      <EvidenceCard
                        key={c.chunkId}
                        citation={c}
                        index={i}
                        active={activeCitation?.chunkId === c.chunkId}
                        onHover={onCitationHover}
                        onClick={onCitationClick}
                      />
                    ))}
                  </div>
                )}
              </li>
            ))}
            <div ref={endRef} />
          </ul>
        )}
      </div>

      <div className="border-t border-shell-border bg-shell p-3">
        <div className="mx-auto flex max-w-2xl items-end gap-2">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Ask a question about this document…"
            className="min-h-[44px] max-h-32 resize-none border-shell-border bg-shell-muted text-shell-foreground placeholder:text-shell-muted-foreground"
          />
          <Button
            onClick={submit}
            disabled={!draft.trim() || busy}
            size="icon"
            className="h-[44px] w-[44px] shrink-0 bg-shell-accent text-shell hover:bg-shell-accent/90"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <div className="mx-auto mt-2 max-w-2xl text-center font-mono text-[10px] uppercase tracking-widest text-shell-muted-foreground">
          Enter to send · Shift+Enter for newline · Answers are quoted, never generated
        </div>
      </div>
    </div>
  );
}
