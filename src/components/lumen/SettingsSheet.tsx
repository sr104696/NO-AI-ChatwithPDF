import { Settings as SettingsIcon, Trash2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { useSettings } from "@/hooks/useSettings";
import { clearAll } from "@/lib/db";

export function SettingsSheet({ onCleared }: { onCleared: () => void }) {
  const [settings, setSettings] = useSettings();
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <SettingsIcon className="h-4 w-4" />
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle className="font-serif">Settings</SheetTitle>
          <SheetDescription>Tune retrieval and chunking. All changes are local.</SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-6">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <Label>Top results</Label>
              <span className="font-mono text-xs text-muted-foreground">{settings.topK}</span>
            </div>
            <Slider
              min={1}
              max={10}
              step={1}
              value={[settings.topK]}
              onValueChange={([v]) => setSettings((s) => ({ ...s, topK: v }))}
            />
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <Label>Chunk sentences</Label>
              <span className="font-mono text-xs text-muted-foreground">{settings.chunkSentences}</span>
            </div>
            <Slider
              min={1}
              max={6}
              step={1}
              value={[settings.chunkSentences]}
              onValueChange={([v]) => setSettings((s) => ({ ...s, chunkSentences: v }))}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              New chunk size applies on next document import.
            </p>
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <Label>Chunk overlap</Label>
              <span className="font-mono text-xs text-muted-foreground">{settings.chunkOverlap}</span>
            </div>
            <Slider
              min={0}
              max={Math.max(0, settings.chunkSentences - 1)}
              step={1}
              value={[Math.min(settings.chunkOverlap, Math.max(0, settings.chunkSentences - 1))]}
              onValueChange={([v]) => setSettings((s) => ({ ...s, chunkOverlap: v }))}
            />
          </div>

          <div className="border-t border-border pt-4">
            <Button
              variant="destructive"
              size="sm"
              onClick={async () => {
                if (confirm("Delete all documents and chats from this browser?")) {
                  await clearAll();
                  onCleared();
                }
              }}
            >
              <Trash2 className="mr-2 h-4 w-4" /> Clear library
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
