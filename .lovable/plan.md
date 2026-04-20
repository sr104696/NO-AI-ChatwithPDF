
## Reimagined: "Lumen" — Private Document Intelligence

A complete rebuild of the Streamlit "No-AI Document Chat" as a **100% in-browser** React web app. Documents never leave the device, no server, no API keys. Every element is rethought, not ported.

### Core philosophy changes vs. original
| Original | Reimagined |
|---|---|
| Single-file Streamlit script | Modular React + TypeScript with workers |
| One PDF at a time, re-indexed each load | Persistent multi-document **library** in IndexedDB |
| BM25 only, blocks UI thread | **Hybrid retrieval**: BM25F + semantic embeddings (Transformers.js, MiniLM) running in a Web Worker |
| 3-sentence fixed chunks | Adaptive sliding-window chunking with heading inheritance |
| Plain quote cards | **Split-pane**: document preview left, chat + citations right, click a citation → jumps & highlights the exact passage in the doc |
| PDF + TXT | PDF, TXT, Markdown, DOCX, HTML — all parsed client-side |
| Manual highlight via regex | Token-level highlight overlay with match scoring badges |
| No history | Per-document chat threads saved locally |

### Layout (editorial split-pane)
- **Left rail (collapsible sidebar)**: document library, upload, search across library, per-doc actions (rename / delete / export thread).
- **Center pane — Document Reader**: rendered PDF (via `pdfjs-dist`) or formatted text view. Sticky page/section indicator. Citations from the chat highlight the matching passage and auto-scroll.
- **Right pane — Conversation**: clean message stream. Each assistant reply shows ranked **evidence cards** (snippet + page + heading + score bar). Hovering a card outlines the source on the left; clicking jumps to it.
- **Top bar**: doc title, indexing progress, retrieval mode toggle (Lexical / Semantic / Hybrid), settings.

### Retrieval pipeline (all in a Web Worker, off main thread)
1. **Parse** (pdfjs-dist / mammoth for DOCX / marked for MD) → structured blocks with page + heading metadata via font-size heuristics (kept from original, improved).
2. **Chunk**: sliding window of ~3 sentences with 1-sentence overlap; carry nearest heading.
3. **Index**:
   - BM25F with field boosts (heading 3×, body 1×) + light fuzzy/stem normalization.
   - Semantic embeddings via `@xenova/transformers` (`all-MiniLM-L6-v2`, quantized, ~25 MB, cached in browser after first load).
4. **Query**: reciprocal-rank fusion of BM25 + cosine similarity. Phrase/proximity bonus when query bigrams co-occur.
5. **Persist**: chunks + embeddings + BM25 stats stored per document in IndexedDB so reopening is instant.

### Reading & citation experience
- Click an evidence card → reader scrolls to the page, highlights the chunk with a soft accent overlay, badges the matched query terms.
- Keyboard: `↑/↓` cycle citations, `Enter` opens in reader, `/` focuses chat.
- "Why this match?" popover explains contributing terms and lexical-vs-semantic share.

### Look & feel
- **Editorial split-pane**, neutral parchment surface for the reader, warm dark sidebar/chat. Serif (Source Serif) for document body, geometric sans for UI, mono for scores/metadata. Subtle accent (amber) for highlights, cool teal for semantic-only matches, slate for lexical-only — so users see *where* a result came from at a glance.
- Fully responsive: on narrow viewports the reader and chat become swipeable tabs with a persistent citation strip.

### What's intentionally NOT included (vs. what you asked)
- No backend, no Lovable Cloud, no AI Gateway — keeps it private and matches the original spirit.
- No login. Library lives in the browser. Optional "Export library" / "Import library" JSON for portability.

### Build steps
1. Add libs: `pdfjs-dist`, `@xenova/transformers`, `mammoth`, `marked`, `idb`.
2. Design system: update `index.css` + `tailwind.config.ts` with the editorial palette, serif/sans/mono font stack, semantic tokens for `highlight-lexical`, `highlight-semantic`, `highlight-hybrid`.
3. Workers: `src/workers/parser.worker.ts`, `src/workers/index.worker.ts` (BM25F + embeddings + RRF).
4. Storage: `src/lib/db.ts` (IndexedDB schema: documents, chunks, embeddings, threads).
5. Components: `AppShell`, `LibrarySidebar`, `DocumentReader`, `ChatPane`, `EvidenceCard`, `RetrievalModeToggle`, `IndexingProgress`, `HighlightOverlay`.
6. Pages: replace `Index.tsx` with the split-pane app; routes `/` (library landing), `/doc/:id` (workspace).
7. Empty state: friendly hero explaining "Drop a PDF — it never leaves your browser."
8. Settings drawer: chunk size, results count, fuzzy tolerance, embedding model on/off, clear library.

After approval I'll implement, then ask you to drop in a sample PDF to verify parsing, indexing progress, citation jumps, and hybrid ranking end-to-end.
