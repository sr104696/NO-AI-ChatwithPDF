import { useEffect, useState, useCallback } from "react";
import { listDocs } from "@/lib/db";
import type { DocMeta } from "@/lib/types";

export function useLibrary() {
  const [docs, setDocs] = useState<DocMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true);
    setDocs(await listDocs());
    setLoading(false);
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  return { docs, loading, refresh };
}
