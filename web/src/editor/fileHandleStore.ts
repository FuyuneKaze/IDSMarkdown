/**
 * fileHandleStore — IndexedDB 持久化 FileSystemFileHandle
 *
 * File System Access API 的文件句柄可通过 structured clone 存入 IndexedDB,
 * 下次访问时查询权限即可重新读写同一文件, 实现"原地保存"和"最近文件"功能。
 */

import Dexie from "dexie";

interface StoredHandle {
  id?: number;
  name: string;
  handle: FileSystemFileHandle;
  timestamp: number;
}

class FileHandleDB extends Dexie {
  handles!: Dexie.Table<StoredHandle, number>;

  constructor() {
    super("IdsEditorHandles");
    this.version(1).stores({
      handles: "++id, name",
    });
  }
}

const db = new FileHandleDB();

export async function storeHandle(name: string, handle: FileSystemFileHandle): Promise<number> {
  // 同名句柄先删旧
  const existing = await db.handles.where("name").equals(name).first();
  if (existing?.id != null) {
    await db.handles.delete(existing.id);
  }
  return db.handles.add({ name, handle, timestamp: Date.now() });
}

export async function getHandle(id: number): Promise<FileSystemFileHandle | null> {
  const entry = await db.handles.get(id);
  return entry?.handle ?? null;
}

export async function removeHandle(id: number): Promise<void> {
  await db.handles.delete(id);
}

export async function updateHandleName(id: number, name: string): Promise<void> {
  await db.handles.update(id, { name, timestamp: Date.now() });
}

/** 清理 orphan 句柄(最近文件列表中已删除的条目) */
export async function cleanupOrphans(validIds: number[]): Promise<void> {
  const all = await db.handles.toArray();
  for (const entry of all) {
    if (entry.id != null && !validIds.includes(entry.id)) {
      await db.handles.delete(entry.id);
    }
  }
}

/**
 * 检测 File System Access API 是否可用
 */
export function isFsaAvailable(): boolean {
  return typeof window !== "undefined" && "showOpenFilePicker" in window;
}
