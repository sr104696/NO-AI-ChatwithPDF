import { useCallback, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onFiles: (files: File[]) => void;
  compact?: boolean;
  className?: string;
}

const ACCEPT = ".pdf,.docx,.md,.markdown,.html,.htm,.txt";

export function Dropzone({ onFiles, compact, className }: Props) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length) onFiles(files);
    },
    [onFiles],
  );
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={cn(
        "cursor-pointer rounded-lg border-2 border-dashed border-shell-border bg-shell-muted/40 px-4 text-shell-muted-foreground transition hover:bg-shell-muted/70 hover:text-shell-foreground",
        drag && "border-shell-accent bg-shell-muted/80 text-shell-foreground",
        compact ? "py-3 text-xs" : "py-8 text-sm",
        className,
      )}
    >
      <div className="flex flex-col items-center gap-2 text-center">
        <Upload className={compact ? "h-4 w-4" : "h-6 w-6"} />
        <span>
          {compact ? "Add document" : "Drop a PDF, DOCX, MD, HTML, or TXT here"}
        </span>
        {!compact && <span className="text-xs opacity-70">Files never leave your browser.</span>}
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
