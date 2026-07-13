import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

function tokenStorageKey(kind) {
  return kind === "terminal" ? "spp_terminal_tokens" : "spp_admin_tokens";
}

export function getTokens(kind) {
  try {
    return JSON.parse(localStorage.getItem(tokenStorageKey(kind)) || "null");
  } catch {
    return null;
  }
}

export function setTokens(kind, tokens) {
  if (!tokens) {
    localStorage.removeItem(tokenStorageKey(kind));
    return;
  }
  localStorage.setItem(tokenStorageKey(kind), JSON.stringify(tokens));
}

function createClient(kind) {
  const client = axios.create({ baseURL: BASE_URL });

  client.interceptors.request.use((config) => {
    const tokens = getTokens(kind);
    if (tokens?.access) {
      config.headers.Authorization = `Bearer ${tokens.access}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config;
      if (error.response?.status === 401 && !original._retry) {
        original._retry = true;
        const tokens = getTokens(kind);
        if (tokens?.refresh) {
          try {
            const refreshUrl = kind === "terminal" ? "/auth/refresh" : "/auth/refresh";
            const { data } = await axios.post(BASE_URL + refreshUrl, { refresh: tokens.refresh });
            setTokens(kind, { ...tokens, access: data.access });
            original.headers.Authorization = `Bearer ${data.access}`;
            return client(original);
          } catch {
            setTokens(kind, null);
          }
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

export const adminApi = createClient("admin");
export const terminalApi = createClient("terminal");
