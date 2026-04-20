import { useNavigate, useParams } from "react-router-dom";
import { useState } from "react";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { Dropzone } from "./Dropzone";
import { IngestProgressBar } from "./IngestProgressBar";
import { KindIcon, formatBytes } from "./KindIcon";
import { useIngest } from "@/hooks/useIngest";
import { useSettings } from "@/hooks/useSettings";
import { deleteDoc, renameDoc } from "@/lib/db";
import type { DocMeta } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface Props {
  docs: DocMeta[];
  onChange: () => void | Promise<void>;
}

export function LibrarySidebar({ docs, onChange }: Props) {
  const navigate = useNavigate();
  const { id: activeId } = useParams();
  const [settings] = useSettings();
  const { progress, ingest, reset } = useIngest(settings);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [filter, setFilter] = useState("");

  const handleFiles = async (files: File[]) => {
    let last: DocMeta | null = null;
    for (const f of files) {
      const m = await ingest(f);
      if (m) last = m;
      await onChange();
    }
    if (last) navigate(`/doc/${last.id}`);
    setTimeout(reset, 1500);
  };

  const filtered = filter
    ? docs.filter((d) => d.name.toLowerCase().includes(filter.toLowerCase()))
    : docs;

  return (
    <aside className="flex h-full w-72 flex-col border-r border-shell-border bg-shell text-shell-foreground">
      <div className="border-b border-shell-border p-4">
        <button
          onClick={() => navigate("/")}
          className="flex items-baseline gap-2 text-left transition hover:opacity-80"
        >
          <span className="font-serif text-2xl font-semibold tracking-tight">Lumen</span>
          <span className="font-mono text-[10px] uppercase tracking-widest text-shell-muted-foreground">
            private · offline
          </span>
        </button>
      </div>

      <div className="space-y-3 p-3">
        <Dropzone onFiles={handleFiles} compact />
        <IngestProgressBar progress={progress} />
        <Input
          placeholder="Filter library…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="h-8 border-shell-border bg-shell-muted text-shell-foreground placeholder:text-shell-muted-foreground"
        />
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {filtered.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-shell-muted-foreground">
            {docs.length === 0 ? "No documents yet." : "No matches."}
          </div>
        ) : (
          <ul className="space-y-1">
            {filtered.map((d) => {
              const active = d.id === activeId;
              return (
                <li
                  key={d.id}
                  className={cn(
                    "group flex items-center gap-2 rounded-md px-2 py-2 text-sm transition",
                    active
                      ? "bg-shell-muted text-shell-foreground"
                      : "hover:bg-shell-muted/60 text-shell-foreground/90",
                  )}
                >
                  <KindIcon kind={d.kind} className="h-4 w-4 shrink-0 text-shell-accent" />
                  <button
                    onClick={() => navigate(`/doc/${d.id}`)}
                    className="flex-1 truncate text-left"
                  >
                    {renaming === d.id ? (
                      <Input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={async (e) => {
                          if (e.key === "Enter") {
                            await renameDoc(d.id, renameValue.trim() || d.name);
                            setRenaming(null);
                            await onChange();
                          } else if (e.key === "Escape") {
                            setRenaming(null);
                          }
                        }}
                        className="h-6 border-shell-border bg-shell-muted text-shell-foreground"
                      />
                    ) : (
                      <>
                        <div className="truncate">{d.name}</div>
                        <div className="font-mono text-[10px] uppercase text-shell-muted-foreground">
                          {d.kind} · {d.pages}p · {formatBytes(d.bytes)}
                        </div>
                      </>
                    )}
                  </button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-6 w-6 text-shell-muted-foreground opacity-0 hover:bg-shell-muted hover:text-shell-foreground group-hover:opacity-100"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => {
                          setRenameValue(d.name);
                          setRenaming(d.id);
                        }}
                      >
                        <Pencil className="mr-2 h-4 w-4" /> Rename
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={async () => {
                          await deleteDoc(d.id);
                          await onChange();
                          if (active) navigate("/");
                        }}
                      >
                        <Trash2 className="mr-2 h-4 w-4" /> Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="border-t border-shell-border p-3 text-[11px] text-shell-muted-foreground">
        <div className="font-mono">{docs.length} document{docs.length === 1 ? "" : "s"} · indexed locally</div>
      </div>
    </aside>
  );
}
