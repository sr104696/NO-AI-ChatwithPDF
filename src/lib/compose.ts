import type { Citation } from "./types";

/**
 * Compose a non-AI assistant reply from top citations.
 * Mirrors the original Streamlit "extract & quote" approach but cleaner.
 */
export function composeReply(query: string, citations: Citation[]): string {
  if (!citations.length) {
    return "I couldn't find anything in this document that matches your question. Try rephrasing or using more specific terms.";
  }
  const top = citations[0];
  const where = top.heading ? `under "${top.heading}" (page ${top.page})` : `on page ${top.page}`;
  const more = citations.length > 1 ? ` I found ${citations.length} relevant passages — top one is shown below; check the others on the right.` : "";
  return `Here's what the document says about your question, ${where}.${more}`;
}
