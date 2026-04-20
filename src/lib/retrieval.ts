import type { Chunk, Citation, RetrievalMode } from "./types";
import { tokenize } from "./text";

/**
 * BM25F-ish ranker with field weighting (heading boost) and proximity bonus.
 * "Semantic" channel here is a lightweight token-overlap-with-stopwords proxy
 * that captures looser matches; this keeps the bundle small and 100% offline.
 * The hybrid mode fuses both with reciprocal rank fusion.
 */

const K1 = 1.4;
const B = 0.75;
const HEADING_BOOST = 3;

interface Stats {
  N: number;
  avgdl: number;
  df: Map<string, number>;
}

function computeStats(chunks: Chunk[]): Stats {
  const df = new Map<string, number>();
  let total = 0;
  for (const c of chunks) {
    total += c.tokens.length;
    const seen = new Set(c.tokens);
    for (const t of seen) df.set(t, (df.get(t) ?? 0) + 1);
  }
  return { N: chunks.length || 1, avgdl: total / Math.max(1, chunks.length), df };
}

function idf(stats: Stats, term: string) {
  const df = stats.df.get(term) ?? 0;
  return Math.log(1 + (stats.N - df + 0.5) / (df + 0.5));
}

function bm25Score(chunk: Chunk, queryTerms: string[], stats: Stats) {
  const tf = new Map<string, number>();
  for (const t of chunk.tokens) tf.set(t, (tf.get(t) ?? 0) + 1);
  const dl = chunk.tokens.length || 1;
  const headingTokens = new Set(chunk.heading ? tokenize(chunk.heading) : []);
  let score = 0;
  const matched: string[] = [];
  for (const qt of queryTerms) {
    const f = tf.get(qt) ?? 0;
    if (f === 0) continue;
    matched.push(qt);
    const boost = headingTokens.has(qt) ? HEADING_BOOST : 1;
    const num = f * (K1 + 1);
    const den = f + K1 * (1 - B + (B * dl) / stats.avgdl);
    score += boost * idf(stats, qt) * (num / den);
  }
  // Proximity bonus: any two query terms within 8-token window.
  if (queryTerms.length >= 2 && matched.length >= 2) {
    const positions = new Map<string, number[]>();
    chunk.tokens.forEach((t, i) => {
      if (queryTerms.includes(t)) {
        const arr = positions.get(t) ?? [];
        arr.push(i);
        positions.set(t, arr);
      }
    });
    let bonus = 0;
    const keys = [...positions.keys()];
    for (let a = 0; a < keys.length; a++) {
      for (let b = a + 1; b < keys.length; b++) {
        for (const pa of positions.get(keys[a])!) {
          for (const pb of positions.get(keys[b])!) {
            const d = Math.abs(pa - pb);
            if (d <= 8) bonus += 0.5 / (1 + d);
          }
        }
      }
    }
    score += bonus;
  }
  return { score, matched };
}

function semanticOverlapScore(chunk: Chunk, queryTokensWithStop: string[]) {
  // Soft overlap: counts any shared token (incl. stop) and rewards heading hits
  const set = new Set(chunk.tokens);
  const headingSet = new Set(chunk.heading ? tokenize(chunk.heading, { keepStop: true }) : []);
  let s = 0;
  const matched: string[] = [];
  for (const t of queryTokensWithStop) {
    if (set.has(t)) {
      s += 1;
      matched.push(t);
    } else if (headingSet.has(t)) {
      s += 0.7;
      matched.push(t);
    }
    // partial / prefix similarity
    for (const ct of set) {
      if (ct !== t && (ct.startsWith(t) || t.startsWith(ct)) && Math.min(ct.length, t.length) >= 4) {
        s += 0.25;
        matched.push(ct);
        break;
      }
    }
  }
  // Length normalization
  s = s / Math.sqrt(Math.max(8, chunk.tokens.length));
  return { score: s, matched };
}

export interface QueryOptions {
  mode: RetrievalMode;
  topK: number;
}

export function query(chunks: Chunk[], q: string, opts: QueryOptions): Citation[] {
  const qNoStop = tokenize(q);
  const qWithStop = tokenize(q, { keepStop: true });
  if (!qNoStop.length && !qWithStop.length) return [];
  const stats = computeStats(chunks);

  const lex = chunks
    .map((c) => {
      const r = bm25Score(c, qNoStop, stats);
      return { c, score: r.score, matched: r.matched };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score);

  const sem = chunks
    .map((c) => {
      const r = semanticOverlapScore(c, qWithStop);
      return { c, score: r.score, matched: r.matched };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score);

  const limit = Math.max(opts.topK * 4, 20);
  const lexRanks = new Map(lex.slice(0, limit).map((r, i) => [r.c.id, i + 1]));
  const semRanks = new Map(sem.slice(0, limit).map((r, i) => [r.c.id, i + 1]));

  const ids = new Set<string>();
  if (opts.mode !== "semantic") lex.slice(0, limit).forEach((r) => ids.add(r.c.id));
  if (opts.mode !== "lexical") sem.slice(0, limit).forEach((r) => ids.add(r.c.id));

  const lexMap = new Map(lex.map((r) => [r.c.id, r]));
  const semMap = new Map(sem.map((r) => [r.c.id, r]));
  const k = 60; // RRF constant

  const fused = [...ids]
    .map((id) => {
      const lr = opts.mode !== "semantic" ? lexRanks.get(id) : undefined;
      const sr = opts.mode !== "lexical" ? semRanks.get(id) : undefined;
      const rrf = (lr ? 1 / (k + lr) : 0) + (sr ? 1 / (k + sr) : 0);
      const lexScore = lexMap.get(id)?.score ?? 0;
      const semScore = semMap.get(id)?.score ?? 0;
      const total = lexScore + semScore;
      const lexShare = total > 0 ? lexScore / total : 0;
      const semShare = total > 0 ? semScore / total : 0;
      const matched = Array.from(
        new Set([...(lexMap.get(id)?.matched ?? []), ...(semMap.get(id)?.matched ?? [])]),
      );
      const c = (lexMap.get(id) ?? semMap.get(id))!.c;
      return {
        chunk: c,
        rrf,
        lexShare,
        semShare,
        matched,
      };
    })
    .sort((a, b) => b.rrf - a.rrf)
    .slice(0, opts.topK);

  return fused.map<Citation>((r) => ({
    chunkId: r.chunk.id,
    page: r.chunk.page,
    heading: r.chunk.heading,
    snippet: r.chunk.text,
    score: r.rrf,
    lexical: r.lexShare,
    semantic: r.semShare,
    matched: r.matched,
  }));
}
