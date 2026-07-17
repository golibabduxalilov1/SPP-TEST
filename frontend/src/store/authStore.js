import { create } from "zustand";
import { adminApi, getTokens, setTokens } from "../api/client";

export const useAuthStore = create((set, get) => ({
  user: null,
  ready: false,

  async init() {
    const tokens = getTokens("admin");
    if (!tokens?.access) {
      set({ ready: true });
      return;
    }
    try {
      const { data } = await adminApi.get("/me");
      set({ user: data, ready: true });
    } catch {
      setTokens("admin", null);
      set({ user: null, ready: true });
    }
  },

  async login(phone, password) {
    const { data } = await adminApi.post("/auth/login", { phone, password });
    setTokens("admin", { access: data.access, refresh: data.refresh });
    set({ user: data.user });
    return data.user;
  },

  logout() {
    setTokens("admin", null);
    set({ user: null });
  },

  hasRole(...roles) {
    const user = get().user;
    return !!user && (user.is_superuser || user.role === "super_admin" || roles.includes(user.role));
  },
}));
