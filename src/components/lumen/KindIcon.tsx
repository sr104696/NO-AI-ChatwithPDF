import { FileText, FileType2, FileCode2, FileType, BookText } from "lucide-react";
import type { DocKind } from "@/lib/types";

export function KindIcon({ kind, className }: { kind: DocKind; className?: string }) {
  const Icon =
    kind === "pdf" ? BookText : kind === "docx" ? FileType : kind === "md" ? FileType2 : kind === "html" ? FileCode2 : FileText;
  return <Icon className={className} />;
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
