import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LibrarySidebar } from "@/components/lumen/LibrarySidebar";
import { DocumentReader } from "@/components/lumen/DocumentReader";
import { ChatPane } from "@/components/lumen/ChatPane";
import { RetrievalModeToggle } from "@/components/lumen/RetrievalModeToggle";
import { SettingsSheet } from "@/components/lumen/SettingsSheet";
import { useLibrary } from "@/hooks/useLibrary";
import { useSettings } from "@/hooks/useSettings";
import { getChunks, getDoc, getThread, saveThread } from "@/lib/db";
import { query } from "@/lib/retrieval";
import { composeReply } from "@/lib/compose";
import type { ChatMessage, Chunk, Citation, DocMeta, Thread } from "@/lib/types";

const Workspace = () => {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { docs, refresh } = useLibrary();
  const [settings, setSettings] = useSettings();

  const [doc, setDoc] = useState<DocMeta | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [thread, setThread] = useState<Thread>({ docId: id, messages: [], updatedAt: Date.now() });
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [hoveredChunk, setHoveredChunk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<"reader" | "chat">("reader");

  useEffect(() => {
    let cancel = false;
    (async () => {
      const d = await getDoc(id);
      if (cancel) return;
      if (!d) {
        navigate("/");
        return;
      }
      setDoc(d);
      const [c, t] = await Promise.all([getChunks(id), getThread(id)]);
      if (cancel) return;
      setChunks(c);
      setThread(t);
      setActiveCitation(null);
    })();
    return () => {
      cancel = true;
    };
  }, [id, navigate]);

  const handleSend = async (text: string) => {
    if (!chunks.length) return;
    setBusy(true);
    const userMsg: ChatMessage = {
      id: `${Date.now()}-u`,
      role: "user",
      text,
      ts: Date.now(),
    };
    const citations = query(chunks, text, { mode: settings.mode, topK: settings.topK });
    const replyText = composeReply(text, citations);
    const reply: ChatMessage = {
      id: `${Date.now()}-a`,
      role: "assistant",
      text: replyText,
      citations,
      ts: Date.now() + 1,
    };
    const next: Thread = {
      docId: id,
      messages: [...thread.messages, userMsg, reply],
      updatedAt: Date.now(),
    };
    setThread(next);
    await saveThread(next);
    if (citations.length) {
      setActiveCitation(citations[0]);
      if (window.matchMedia("(max-width: 900px)").matches) setTab("reader");
    }
    setBusy(false);
  };

  const headerTitle = useMemo(() => doc?.name ?? "Loading…", [doc]);

  return (
    <div className="flex h-screen w-full">
      <LibrarySidebar docs={docs} onChange={refresh} />
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-card px-4">
          <div className="min-w-0 flex-1 truncate">
            <span className="font-serif text-base font-semibold tracking-tight">
              {headerTitle}
            </span>
            {doc && (
              <span className="ml-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                {doc.kind} · {doc.pages}p · {doc.chunkCount} chunks
              </span>
            )}
          </div>
          {/* Mobile tab switcher */}
          <div className="md:hidden inline-flex rounded-md border border-border bg-background p-0.5">
            {(["reader", "chat"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1 text-xs font-medium rounded-sm ${
                  tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                {t === "reader" ? "Read" : "Chat"}
              </button>
            ))}
          </div>
          <RetrievalModeToggle
            mode={settings.mode}
            onChange={(m) => setSettings((s) => ({ ...s, mode: m }))}
          />
          <SettingsSheet onCleared={() => navigate("/")} />
        </header>

        {/* Split panes */}
        <div className="flex min-h-0 flex-1">
          <section
            className={`min-w-0 flex-1 ${tab === "chat" ? "hidden md:block" : "block"}`}
          >
            <DocumentReader
              chunks={chunks}
              activeCitation={activeCitation}
              hoveredChunkId={hoveredChunk}
            />
          </section>
          <section
            className={`w-full border-l border-shell-border md:w-[420px] ${
              tab === "reader" ? "hidden md:block" : "block"
            }`}
          >
            <ChatPane
              messages={thread.messages}
              busy={busy}
              onSend={handleSend}
              activeCitation={activeCitation}
              onCitationHover={setHoveredChunk}
              onCitationClick={(c) => {
                setActiveCitation(c);
                setTab("reader");
              }}
            />
          </section>
        </div>
      </div>
    </div>
  );
};

export default Workspace;
