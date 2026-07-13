import { terminalApi } from "../api/client";
import { getDeviceId } from "./device";
import {
  addSyncHistory, countPendingScans, getPendingScans, removePendingScan, setMeta,
} from "./db";

async function syncRouteScans(routeScans, { workstationId, employeeId }) {
  if (routeScans.length === 0) return { accepted: 0, conflict: 0, failed: 0 };
  const clientBatchId = `batch-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const { data } = await terminalApi.post("/terminal/sync", {
    device_id: getDeviceId(),
    workstation_id: workstationId,
    employee_id: employeeId,
    client_batch_id: clientBatchId,
    scans: routeScans.map((s) => ({
      client_scan_id: s.client_scan_id,
      qr_token: s.qr_token,
      operation_code: s.operation_code,
      scanned_at_client: s.scanned_at_client,
    })),
  });
  for (const result of data.results) {
    if (result.status === "synced" || result.status === "conflict") {
      await removePendingScan(result.client_scan_id);
    }
  }
  await addSyncHistory({ batch_id: data.batch_id, accepted: data.accepted, conflict: data.conflict, failed: data.failed });
  return data;
}

async function syncPackagingScans(scans) {
  let accepted = 0, conflict = 0, failed = 0;
  for (const s of scans) {
    try {
      const { data } = await terminalApi.post("/packaging/scan", { package_id: s.payload.package_id, qr_token: s.qr_token });
      if (data.status === "ok") accepted += 1;
      else conflict += 1;
      await removePendingScan(s.client_scan_id);
    } catch {
      failed += 1;
    }
  }
  return { accepted, conflict, failed };
}

async function syncWarehouseScans(scans) {
  let accepted = 0, conflict = 0, failed = 0;
  for (const s of scans) {
    try {
      await terminalApi.post("/warehouse/receive", { qr_token: s.qr_token });
      accepted += 1;
      await removePendingScan(s.client_scan_id);
    } catch {
      conflict += 1;
    }
  }
  return { accepted, conflict, failed };
}

export async function runSync({ workstationId, employeeId }) {
  const all = await getPendingScans();
  if (all.length === 0) {
    return { accepted: 0, conflict: 0, failed: 0, skipped: true };
  }

  const routeScans = all.filter((s) => (s.kind || "route") === "route");
  const packagingScans = all.filter((s) => s.kind === "packaging");
  const warehouseScans = all.filter((s) => s.kind === "warehouse_receive");

  try {
    const [routeResult, packagingResult, warehouseResult] = await Promise.all([
      syncRouteScans(routeScans, { workstationId, employeeId }),
      syncPackagingScans(packagingScans),
      syncWarehouseScans(warehouseScans),
    ]);
    await setMeta("last_sync_at", new Date().toISOString());
    return {
      accepted: routeResult.accepted + packagingResult.accepted + warehouseResult.accepted,
      conflict: routeResult.conflict + packagingResult.conflict + warehouseResult.conflict,
      failed: (routeResult.failed || 0) + packagingResult.failed + warehouseResult.failed,
    };
  } catch (err) {
    await addSyncHistory({ error: err.message || "network error" });
    throw err;
  }
}

export async function getPendingCount() {
  return countPendingScans();
}
