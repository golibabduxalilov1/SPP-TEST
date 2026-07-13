const STORAGE_KEY = "spp_tutorial_seen_v1";

function readAll() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

export function isTutorialSeen(userId, pageKey) {
  return !!readAll()[userId]?.[pageKey];
}

export function markTutorialSeen(userId, pageKey) {
  const all = readAll();
  all[userId] = { ...all[userId], [pageKey]: true };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}
