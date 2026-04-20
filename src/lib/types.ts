export type DocKind = "pdf" | "docx" | "md" | "html" | "txt";

export interface DocMeta {
  id: string;
  name: string;
  kind: DocKind;
  bytes: number;
  pages: number;
  chunkCount: number;
  createdAt: number;
  updatedAt: number;
}

export interface Block {
  /** Sequential index in the doc */
  i: number;
  /** Page number (1-based). For non-paged formats this is a synthetic section number. */
  page: number;
  /** Nearest enclosing heading text, if any */
  heading?: string;
  /** Raw text */
  text: string;
  /** Heading level (1-6) if this block IS a heading; undefined for body */
  headingLevel?: number;
}

export interface Chunk {
  id: string;
  docId: string;
  /** Index in doc */
  i: number;
  page: number;
  heading?: string;
  text: string;
  /** Token list (lowercased, normalized) for BM25 */
  tokens: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  ts: number;
}

export interface Citation {
  chunkId: string;
  page: number;
  heading?: string;
  snippet: string;
  score: number;
  /** 0..1 share of contribution from each retrieval channel */
  lexical: number;
  semantic: number;
  /** Matched query tokens (post-normalization) for highlighting */
  matched: string[];
}

export interface Thread {
  docId: string;
  messages: ChatMessage[];
  updatedAt: number;
}

export type RetrievalMode = "lexical" | "semantic" | "hybrid";

export interface Settings {
  mode: RetrievalMode;
  topK: number;
  chunkSentences: number;
  chunkOverlap: number;
}

export const DEFAULT_SETTINGS: Settings = {
  mode: "hybrid",
  topK: 5,
  chunkSentences: 3,
  chunkOverlap: 1,
};
