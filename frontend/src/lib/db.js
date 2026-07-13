import { openDB } from "idb";

// IndexedDB structure per spec section 6.4.
const DB_NAME = "spp-terminal";
const DB_VERSION = 1;

let dbPromise;

export function getDb() {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains("app_cache_meta")) db.createObjectStore("app_cache_meta");
        if (!db.objectStoreNames.contains("terminal_settings")) db.createObjectStore("terminal_settings");
        if (!db.objectStoreNames.contains("cached_parts")) db.createObjectStore("cached_parts", { keyPath: "id" });
        if (!db.objectStoreNames.contains("employee_session")) db.createObjectStore("employee_session");
        if (!db.objectStoreNames.contains("pending_scans")) {
          db.createObjectStore("pending_scans", { keyPath: "client_scan_id" });
        }
        if (!db.objectStoreNames.contains("sync_history")) {
          db.createObjectStore("sync_history", { keyPath: "id", autoIncrement: true });
        }
        if (!db.objectStoreNames.contains("conflict_queue")) {
          db.createObjectStore("conflict_queue", { keyPath: "client_scan_id" });
        }
      },
    });
  }
  return dbPromise;
}

export async function setMeta(key, value) {
  const db = await getDb();
  await db.put("app_cache_meta", value, key);
}

export async function getMeta(key) {
  const db = await getDb();
  return db.get("app_cache_meta", key);
}

export async function setSetting(key, value) {
  const db = await getDb();
  await db.put("terminal_settings", value, key);
}

export async function getSetting(key) {
  const db = await getDb();
  return db.get("terminal_settings", key);
}

export async function cacheParts(parts) {
  const db = await getDb();
  const tx = db.transaction("cached_parts", "readwrite");
  await tx.store.clear();
  for (const part of parts) await tx.store.put(part);
  await tx.done;
}

export async function getCachedParts() {
  const db = await getDb();
  return db.getAll("cached_parts");
}

export async function findCachedPartByToken(qrToken) {
  const parts = await getCachedParts();
  return parts.find((p) => p.qr_token === qrToken);
}

export async function addPendingScan(scan) {
  const db = await getDb();
  await db.put("pending_scans", scan);
}

export async function getPendingScans() {
  const db = await getDb();
  return db.getAll("pending_scans");
}

export async function removePendingScan(clientScanId) {
  const db = await getDb();
  await db.delete("pending_scans", clientScanId);
}

export async function countPendingScans() {
  const db = await getDb();
  return db.count("pending_scans");
}

export async function addSyncHistory(entry) {
  const db = await getDb();
  await db.add("sync_history", { ...entry, at: new Date().toISOString() });
}

export async function getSyncHistory(limit = 20) {
  const db = await getDb();
  const all = await db.getAll("sync_history");
  return all.slice(-limit).reverse();
}

export async function addConflict(entry) {
  const db = await getDb();
  await db.put("conflict_queue", entry);
}

export async function getLocalConflicts() {
  const db = await getDb();
  return db.getAll("conflict_queue");
}

export async function clearEmployeeSession() {
  const db = await getDb();
  await db.clear("employee_session");
}

export async function setEmployeeSession(session) {
  const db = await getDb();
  await db.put("employee_session", session, "current");
}

export async function getEmployeeSession() {
  const db = await getDb();
  return db.get("employee_session", "current");
}
