import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { Chunk, DocMeta, Thread } from "./types";

interface LumenDB extends DBSchema {
  docs: { key: string; value: DocMeta };
  chunks: { key: string; value: Chunk; indexes: { byDoc: string } };
  threads: { key: string; value: Thread };
  blobs: { key: string; value: { id: string; blob: Blob } };
}

let dbPromise: Promise<IDBPDatabase<LumenDB>> | null = null;

function db() {
  if (!dbPromise) {
    dbPromise = openDB<LumenDB>("lumen-db", 1, {
      upgrade(d) {
        d.createObjectStore("docs", { keyPath: "id" });
        const chunks = d.createObjectStore("chunks", { keyPath: "id" });
        chunks.createIndex("byDoc", "docId");
        d.createObjectStore("threads", { keyPath: "docId" });
        d.createObjectStore("blobs", { keyPath: "id" });
      },
    });
  }
  return dbPromise;
}

export async function listDocs(): Promise<DocMeta[]> {
  const all = await (await db()).getAll("docs");
  return all.sort((a, b) => b.updatedAt - a.updatedAt);
}

export async function getDoc(id: string) {
  return (await db()).get("docs", id);
}

export async function saveDoc(meta: DocMeta) {
  await (await db()).put("docs", meta);
}

export async function renameDoc(id: string, name: string) {
  const d = await getDoc(id);
  if (!d) return;
  d.name = name;
  d.updatedAt = Date.now();
  await saveDoc(d);
}

export async function deleteDoc(id: string) {
  const d = await db();
  const tx = d.transaction(["docs", "chunks", "threads", "blobs"], "readwrite");
  await tx.objectStore("docs").delete(id);
  await tx.objectStore("threads").delete(id);
  await tx.objectStore("blobs").delete(id);
  const idx = tx.objectStore("chunks").index("byDoc");
  let cursor = await idx.openCursor(id);
  while (cursor) {
    await cursor.delete();
    cursor = await cursor.continue();
  }
  await tx.done;
}

export async function saveChunks(docId: string, chunks: Chunk[]) {
  const d = await db();
  const tx = d.transaction("chunks", "readwrite");
  // Replace existing
  const idx = tx.store.index("byDoc");
  let cursor = await idx.openCursor(docId);
  while (cursor) {
    await cursor.delete();
    cursor = await cursor.continue();
  }
  for (const c of chunks) await tx.store.put(c);
  await tx.done;
}

export async function getChunks(docId: string): Promise<Chunk[]> {
  const d = await db();
  const all = await d.getAllFromIndex("chunks", "byDoc", docId);
  return all.sort((a, b) => a.i - b.i);
}

export async function saveBlob(id: string, blob: Blob) {
  await (await db()).put("blobs", { id, blob });
}

export async function getBlob(id: string): Promise<Blob | undefined> {
  const r = await (await db()).get("blobs", id);
  return r?.blob;
}

export async function getThread(docId: string): Promise<Thread> {
  const r = await (await db()).get("threads", docId);
  return r ?? { docId, messages: [], updatedAt: Date.now() };
}

export async function saveThread(t: Thread) {
  t.updatedAt = Date.now();
  await (await db()).put("threads", t);
}

export async function clearAll() {
  const d = await db();
  await Promise.all([
    d.clear("docs"),
    d.clear("chunks"),
    d.clear("threads"),
    d.clear("blobs"),
  ]);
}
