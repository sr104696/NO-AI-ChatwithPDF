import { useEffect, useState } from "react";
import { DEFAULT_SETTINGS, type Settings } from "@/lib/types";

const KEY = "lumen-settings";

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
    } catch {
      /* ignore */
    }
    return DEFAULT_SETTINGS;
  });
  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(settings));
  }, [settings]);
  return [settings, setSettings] as const;
}
