import { uuid } from "./uuid";

export function getDeviceId() {
  let id = localStorage.getItem("spp_device_id");
  if (!id) {
    id = "device-" + uuid().slice(0, 12);
    localStorage.setItem("spp_device_id", id);
  }
  return id;
}

// A terminal device is physically mounted at one post — remembered locally so
// operators only need to enter their PIN on every login, not reselect the post.
export function getSavedWorkstationId() {
  return localStorage.getItem("spp_terminal_workstation_id");
}

export function saveWorkstationId(id) {
  if (id) localStorage.setItem("spp_terminal_workstation_id", String(id));
}
