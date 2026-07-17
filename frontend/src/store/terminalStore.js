import { create } from "zustand";
import { terminalApi, setTokens, getTokens } from "../api/client";
import { getDeviceId } from "../lib/device";
import { cacheParts, getCachedParts, getEmployeeSession, setEmployeeSession, clearEmployeeSession, setMeta, getMeta } from "../lib/db";
import { runSync, getPendingCount } from "../lib/sync";

export const useTerminalStore = create((set, get) => ({
  employee: null,
  workstation: null,
  sessionId: null,
  operations: [],
  machines: [],
  parts: [],
  online: navigator.onLine,
  pendingCount: 0,
  lastSyncAt: null,
  ready: false,

  async init() {
    const session = await getEmployeeSession();
    const tokens = getTokens("terminal");
    const pendingCount = await getPendingCount();
    const lastSyncAt = await getMeta("last_sync_at");
    if (session && tokens?.access) {
      set({ employee: session.employee, workstation: session.workstation, sessionId: session.sessionId, pendingCount, lastSyncAt });
      const cached = await getCachedParts();
      set({ parts: cached });
      get().refreshBootstrap().catch(() => {});
    }
    set({ ready: true });
  },

  async lookupPin(pinCode) {
    const { data } = await terminalApi.post("/auth/terminal-pin-lookup", { pin_code: pinCode });
    return data;
  },

  async loginWithPin(pinCode, workstation) {
    const deviceId = getDeviceId();
    const { data } = await terminalApi.post("/auth/terminal-login", {
      pin_code: pinCode,
      device_id: deviceId,
      workstation_id: workstation?.id,
    });
    setTokens("terminal", { access: data.access, refresh: data.refresh });
    await setEmployeeSession({ employee: data.employee, workstation, sessionId: data.session_id });
    set({ employee: data.employee, workstation, sessionId: data.session_id });
    await get().refreshBootstrap();
    return data.employee;
  },

  async refreshBootstrap() {
    const workstation = get().workstation;
    if (!workstation) return;
    try {
      const { data } = await terminalApi.get("/terminal/bootstrap", { params: { workstation_id: workstation.id } });
      await cacheParts(data.parts);
      await setMeta("last_bootstrap_at", new Date().toISOString());
      set({ operations: data.operations, machines: data.machines, parts: data.parts });
    } catch {
      // Offline — fall back silently to whatever is already cached in IndexedDB.
    }
  },

  async logout() {
    setTokens("terminal", null);
    await clearEmployeeSession();
    set({ employee: null, workstation: null, sessionId: null, parts: [] });
  },

  setOnline(online) {
    set({ online });
  },

  async refreshPendingCount() {
    set({ pendingCount: await getPendingCount() });
  },

  async sync() {
    const workstation = get().workstation;
    const employee = get().employee;
    const result = await runSync({ workstationId: workstation?.id, employeeId: employee?.id });
    await get().refreshPendingCount();
    set({ lastSyncAt: await getMeta("last_sync_at") });
    if (get().online) {
      get().refreshBootstrap().catch(() => {});
    }
    return result;
  },
}));

window.addEventListener("online", () => useTerminalStore.getState().setOnline(true));
window.addEventListener("offline", () => useTerminalStore.getState().setOnline(false));
