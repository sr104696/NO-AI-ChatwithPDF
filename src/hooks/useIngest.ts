import { useCallback, useState } from "react";
import { saveBlob, saveChunks, saveDoc } from "@/lib/db";
import { chunkBlocks, detectKind, parseFile } from "@/lib/parsers";
import type { DocMeta, Settings } from "@/lib/types";

export interface IngestProgress {
  stage: "idle" | "reading" | "parsing" | "chunking" | "indexing" | "saving" | "done" | "error";
  message?: string;
  pct: number;
}

export function useIngest(settings: Settings) {
  const [progress, setProgress] = useState<IngestProgress>({ stage: "idle", pct: 0 });

  const ingest = useCallback(
    async (file: File): Promise<DocMeta | null> => {
      try {
        setProgress({ stage: "reading", pct: 10, message: `Reading ${file.name}` });
        const kind = detectKind(file);
        setProgress({ stage: "parsing", pct: 30, message: "Extracting text" });
        const { blocks, pages } = await parseFile(file, kind);
        if (!blocks.length) {
          setProgress({ stage: "error", pct: 0, message: "No text found in file" });
          return null;
        }
        const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
        setProgress({ stage: "chunking", pct: 60, message: "Chunking" });
        const chunks = chunkBlocks(id, blocks, {
          sentences: settings.chunkSentences,
          overlap: settings.chunkOverlap,
        });
        setProgress({ stage: "indexing", pct: 80, message: "Indexing terms" });
        await saveChunks(id, chunks);
        setProgress({ stage: "saving", pct: 92, message: "Saving" });
        await saveBlob(id, file);
        const meta: DocMeta = {
          id,
          name: file.name,
          kind,
          bytes: file.size,
          pages,
          chunkCount: chunks.length,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        await saveDoc(meta);
        setProgress({ stage: "done", pct: 100, message: "Ready" });
        return meta;
      } catch (e) {
        console.error(e);
        setProgress({ stage: "error", pct: 0, message: e instanceof Error ? e.message : "Unknown error" });
        return null;
      }
    },
    [settings],
  );

  return { progress, ingest, reset: () => setProgress({ stage: "idle", pct: 0 }) };
}
