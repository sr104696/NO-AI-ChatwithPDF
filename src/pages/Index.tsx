import { useNavigate } from "react-router-dom";
import { Sparkles, Lock, Search, Library } from "lucide-react";
import { Dropzone } from "@/components/lumen/Dropzone";
import { IngestProgressBar } from "@/components/lumen/IngestProgressBar";
import { LibrarySidebar } from "@/components/lumen/LibrarySidebar";
import { useIngest } from "@/hooks/useIngest";
import { useLibrary } from "@/hooks/useLibrary";
import { useSettings } from "@/hooks/useSettings";

const Index = () => {
  const navigate = useNavigate();
  const { docs, refresh } = useLibrary();
  const [settings] = useSettings();
  const { progress, ingest, reset } = useIngest(settings);

  const handleFiles = async (files: File[]) => {
    let lastId: string | null = null;
    for (const f of files) {
      const m = await ingest(f);
      if (m) lastId = m.id;
      await refresh();
    }
    if (lastId) navigate(`/doc/${lastId}`);
    setTimeout(reset, 1500);
  };

  return (
    <div className="flex h-screen w-full">
      <LibrarySidebar docs={docs} onChange={refresh} />
      <main className="flex flex-1 items-center justify-center overflow-y-auto bg-background px-6 py-10">
        <div className="w-full max-w-2xl">
          <header className="mb-8 text-center">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              <Lock className="h-3 w-3" /> 100% in-browser · no uploads
            </div>
            <h1 className="font-serif text-5xl font-semibold tracking-tight text-foreground">
              Lumen
            </h1>
            <p className="mt-3 text-base text-muted-foreground">
              Private document intelligence. Drop a file — it never leaves your browser.
            </p>
          </header>

          <Dropzone onFiles={handleFiles} className="bg-card text-foreground" />
          <div className="mt-4">
            <IngestProgressBar progress={progress} />
          </div>

          <section className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              { icon: Library, title: "Multi-doc library", body: "Indexed locally in IndexedDB. Reopens instantly." },
              { icon: Search, title: "Hybrid retrieval", body: "BM25 keyword + soft semantic, fused with RRF." },
              { icon: Sparkles, title: "Citation-first", body: "Click any evidence card to jump to the source." },
            ].map(({ icon: Icon, title, body }) => (
              <div key={title} className="rounded-lg border border-border bg-card p-4">
                <Icon className="mb-2 h-4 w-4 text-primary" />
                <div className="font-serif text-base font-semibold">{title}</div>
                <p className="mt-1 text-xs text-muted-foreground">{body}</p>
              </div>
            ))}
          </section>

          {docs.length > 0 && (
            <p className="mt-8 text-center text-xs text-muted-foreground">
              Or pick from your <span className="font-medium text-foreground">{docs.length}</span> indexed document
              {docs.length === 1 ? "" : "s"} in the sidebar.
            </p>
          )}
        </div>
      </main>
    </div>
  );
};

export default Index;
