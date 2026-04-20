import type { Block, Chunk, DocKind } from "./types";
import { splitSentences, tokenize } from "./text";

/* ---------------- PDF ---------------- */
async function parsePdf(file: File): Promise<{ blocks: Block[]; pages: number }> {
  const pdfjs = await import("pdfjs-dist");
  const workerMod = (await import(
    /* @vite-ignore */ "pdfjs-dist/build/pdf.worker.min.mjs?url"
  )) as { default: string };
  pdfjs.GlobalWorkerOptions.workerSrc = workerMod.default;

  const buf = await file.arrayBuffer();
  const pdf = await pdfjs.getDocument({ data: buf }).promise;
  const blocks: Block[] = [];
  let i = 0;
  let currentHeading: string | undefined;

  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    const tc = await page.getTextContent();
    type Item = { str: string; height: number; y: number };
    const items: Item[] = [];
    for (const it of tc.items as unknown as Array<{ str: string; transform: number[]; height?: number }>) {
      const h = it.height ?? Math.abs(it.transform[3] ?? 12);
      const y = it.transform[5] ?? 0;
      if (it.str) items.push({ str: it.str, height: h, y });
    }
    if (!items.length) continue;

    // Group items into lines by y proximity
    const sorted = [...items].sort((a, b) => b.y - a.y || 0);
    const lines: { text: string; size: number }[] = [];
    let cur: { ys: number; size: number; parts: string[] } | null = null;
    for (const it of sorted) {
      if (!cur || Math.abs(cur.ys - it.y) > 2) {
        if (cur) lines.push({ text: cur.parts.join(" ").replace(/\s+/g, " ").trim(), size: cur.size });
        cur = { ys: it.y, size: it.height, parts: [it.str] };
      } else {
        cur.parts.push(it.str);
        cur.size = Math.max(cur.size, it.height);
      }
    }
    if (cur) lines.push({ text: cur.parts.join(" ").replace(/\s+/g, " ").trim(), size: cur.size });

    // Estimate body size as median
    const sizes = lines.map((l) => l.size).sort((a, b) => a - b);
    const median = sizes[Math.floor(sizes.length / 2)] || 12;

    // Merge contiguous body lines into paragraphs; emit headings standalone
    let buffer: string[] = [];
    const flush = () => {
      const text = buffer.join(" ").replace(/\s+/g, " ").trim();
      buffer = [];
      if (text) blocks.push({ i: i++, page: p, heading: currentHeading, text });
    };
    for (const ln of lines) {
      if (!ln.text) continue;
      const isHeading = ln.size >= median * 1.18 && ln.text.length < 140 && !/[.?!]\s*$/.test(ln.text);
      if (isHeading) {
        flush();
        currentHeading = ln.text;
        const level = ln.size >= median * 1.6 ? 1 : ln.size >= median * 1.35 ? 2 : 3;
        blocks.push({ i: i++, page: p, heading: currentHeading, text: ln.text, headingLevel: level });
      } else {
        buffer.push(ln.text);
      }
    }
    flush();
  }
  return { blocks, pages: pdf.numPages };
}

/* ---------------- DOCX ---------------- */
async function parseDocx(file: File): Promise<{ blocks: Block[]; pages: number }> {
  const mammoth = await import("mammoth/mammoth.browser");
  const buf = await file.arrayBuffer();
  const { value: html } = await mammoth.convertToHtml({ arrayBuffer: buf });
  return parseHtmlString(html);
}

/* ---------------- HTML ---------------- */
async function parseHtml(file: File): Promise<{ blocks: Block[]; pages: number }> {
  return parseHtmlString(await file.text());
}

function parseHtmlString(html: string): { blocks: Block[]; pages: number } {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const blocks: Block[] = [];
  let i = 0;
  let page = 1;
  let heading: string | undefined;
  const walk = (node: Element) => {
    for (const child of Array.from(node.children)) {
      const tag = child.tagName.toLowerCase();
      if (/^h[1-6]$/.test(tag)) {
        heading = (child.textContent || "").trim();
        const level = Number(tag.slice(1));
        if (heading) blocks.push({ i: i++, page, heading, text: heading, headingLevel: level });
        // Synthetic page break on H1
        if (level === 1 && i > 1) page += 1;
      } else if (["p", "li", "blockquote", "pre"].includes(tag)) {
        const t = (child.textContent || "").replace(/\s+/g, " ").trim();
        if (t) blocks.push({ i: i++, page, heading, text: t });
      } else if (child.children.length) {
        walk(child);
      } else {
        const t = (child.textContent || "").replace(/\s+/g, " ").trim();
        if (t) blocks.push({ i: i++, page, heading, text: t });
      }
    }
  };
  walk(doc.body);
  return { blocks, pages: page };
}

/* ---------------- Markdown ---------------- */
async function parseMd(file: File): Promise<{ blocks: Block[]; pages: number }> {
  const { marked } = await import("marked");
  const html = await marked.parse(await file.text());
  return parseHtmlString(html);
}

/* ---------------- TXT ---------------- */
async function parseTxt(file: File): Promise<{ blocks: Block[]; pages: number }> {
  const text = await file.text();
  const paragraphs = text.split(/\n\s*\n+/).map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean);
  const PER_PAGE = 12;
  const blocks: Block[] = paragraphs.map((t, i) => ({
    i,
    page: Math.floor(i / PER_PAGE) + 1,
    text: t,
  }));
  return { blocks, pages: Math.max(1, Math.ceil(paragraphs.length / PER_PAGE)) };
}

export function detectKind(file: File): DocKind {
  const n = file.name.toLowerCase();
  if (n.endsWith(".pdf")) return "pdf";
  if (n.endsWith(".docx")) return "docx";
  if (n.endsWith(".md") || n.endsWith(".markdown")) return "md";
  if (n.endsWith(".html") || n.endsWith(".htm")) return "html";
  return "txt";
}

export async function parseFile(file: File, kind: DocKind) {
  switch (kind) {
    case "pdf":
      return parsePdf(file);
    case "docx":
      return parseDocx(file);
    case "md":
      return parseMd(file);
    case "html":
      return parseHtml(file);
    default:
      return parseTxt(file);
  }
}

/** Adaptive sliding-window chunker (sentence-based). */
export function chunkBlocks(
  docId: string,
  blocks: Block[],
  opts: { sentences: number; overlap: number },
): Chunk[] {
  const chunks: Chunk[] = [];
  let idx = 0;
  for (const b of blocks) {
    if (b.headingLevel) continue; // headings used as metadata only
    const sentences = splitSentences(b.text);
    if (!sentences.length) continue;
    const step = Math.max(1, opts.sentences - opts.overlap);
    for (let s = 0; s < sentences.length; s += step) {
      const window = sentences.slice(s, s + opts.sentences);
      if (!window.length) break;
      const text = window.join(" ");
      chunks.push({
        id: `${docId}:${idx}`,
        docId,
        i: idx++,
        page: b.page,
        heading: b.heading,
        text,
        tokens: tokenize(text),
      });
      if (s + opts.sentences >= sentences.length) break;
    }
  }
  return chunks;
}
