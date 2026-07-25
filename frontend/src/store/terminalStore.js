import { create } from "zustand";
import { terminalApi, setTokens, getTokens } from "../api/client";
import { getDeviceId } from "../lib/device";
import { cacheParts, getCachedParts, getEmployeeSession, setEmployeeSession, clearEmployeeSession, setMeta, getMeta } from "../lib/db";
import { runSync, getPendingCount } from "../lib/sync";

export const useTerminalStore = create((set, get) => ({
  employee: null,
  stage: null, // { id, code, name } — the production stage ("Ishlab chiqarish bosqichi") the session is logged into
  machine: null, // { id, machine_id, name } — the specific stanok currently selected within the stage, or null
  sessionId: null,
  operations: [],
  machines: [], // stanok(s) available within the current stage
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
      set({ employee: session.employee, stage: session.stage, machine: session.machine, sessionId: session.sessionId, pendingCount, lastSyncAt });
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

  async loginWithPin(pinCode, stage) {
    const deviceId = getDeviceId();
    const { data } = await terminalApi.post("/auth/terminal-login", {
      pin_code: pinCode,
      device_id: deviceId,
      operation_id: stage?.id,
    });
    setTokens("terminal", { access: data.access, refresh: data.refresh });
    await setEmployeeSession({ employee: data.employee, stage, machine: null, sessionId: data.session_id });
    set({ employee: data.employee, stage, machine: null, sessionId: data.session_id });
    await get().refreshBootstrap();
    return data.employee;
  },

  async setMachine(machine) {
    set({ machine });
    const session = await getEmployeeSession();
    if (session) await setEmployeeSession({ ...session, machine });
  },

  async refreshBootstrap() {
    const stage = get().stage;
    if (!stage) return;
    try {
      const { data } = await terminalApi.get("/terminal/bootstrap", { params: { operation_id: stage.id } });
      await cacheParts(data.parts);
      await setMeta("last_bootstrap_at", new Date().toISOString());
      set({ operations: data.operations, machines: data.machines, parts: data.parts });
      // Keep the selected machine in sync with what's actually assigned: drop it
      // if it's no longer in the list, auto-pick it if there's exactly one.
      const machines = data.machines || [];
      const current = get().machine;
      if (current && !machines.some((m) => m.id === current.id)) {
        await get().setMachine(machines.length === 1 ? machines[0] : null);
      } else if (!current && machines.length === 1) {
        await get().setMachine(machines[0]);
      }
    } catch {
      // Offline — fall back silently to whatever is already cached in IndexedDB.
    }
  },

  async logout() {
    setTokens("terminal", null);
    await clearEmployeeSession();
    set({ employee: null, stage: null, machine: null, sessionId: null, parts: [] });
  },

  setOnline(online) {
    set({ online });
  },

  async refreshPendingCount() {
    set({ pendingCount: await getPendingCount() });
  },

  async sync() {
    const stage = get().stage;
    const employee = get().employee;
    const result = await runSync({ operationId: stage?.id, employeeId: employee?.id });
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
