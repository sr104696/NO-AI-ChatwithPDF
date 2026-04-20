/**
 * Lightweight English tokenization with stopword filtering and a tiny stemmer.
 * Pure functions, safe to use in workers and tests.
 */

const STOP = new Set(
  "a an and are as at be by for from has have he her him his i if in is it its of on or our she that the their them they this to was we were will with you your".split(
    " ",
  ),
);

export function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
}

/** Trim suffixes (very small Porter-ish stemmer). */
export function stem(w: string): string {
  if (w.length <= 3) return w;
  if (w.endsWith("ing") && w.length > 5) return w.slice(0, -3);
  if (w.endsWith("ed") && w.length > 4) return w.slice(0, -2);
  if (w.endsWith("ies") && w.length > 4) return w.slice(0, -3) + "y";
  if (w.endsWith("es") && w.length > 4) return w.slice(0, -2);
  if (w.endsWith("s") && !w.endsWith("ss") && w.length > 3) return w.slice(0, -1);
  return w;
}

export function tokenize(text: string, opts: { keepStop?: boolean } = {}): string[] {
  const out: string[] = [];
  const re = /[a-z0-9][a-z0-9'-]*/g;
  const norm = normalize(text);
  let m: RegExpExecArray | null;
  while ((m = re.exec(norm))) {
    const w = m[0].replace(/^'+|'+$/g, "");
    if (!w) continue;
    if (!opts.keepStop && STOP.has(w)) continue;
    out.push(stem(w));
  }
  return out;
}

/** Naive sentence splitter that handles ., !, ?, and common abbreviations. */
export function splitSentences(text: string): string[] {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) return [];
  // Protect a few common abbreviations
  const protectedText = cleaned.replace(/\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|Inc|Ltd|e\.g|i\.e|vs|etc)\./gi, "$1<DOT>");
  const parts = protectedText.split(/(?<=[.!?])\s+(?=[A-Z(0-9"'\u201C])/);
  return parts.map((p) => p.replace(/<DOT>/g, ".").trim()).filter(Boolean);
}
