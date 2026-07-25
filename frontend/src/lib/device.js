import { uuid } from "./uuid";

export function getDeviceId() {
  let id = localStorage.getItem("spp_device_id");
  if (!id) {
    id = "device-" + uuid().slice(0, 12);
    localStorage.setItem("spp_device_id", id);
  }
  return id;
}

// A terminal device is physically mounted at one stage — remembered locally so
// operators only need to enter their PIN on every login, not reselect the stage.
export function getSavedStageId() {
  return localStorage.getItem("spp_terminal_stage_id");
}

export function saveStageId(id) {
  if (id) localStorage.setItem("spp_terminal_stage_id", String(id));
}
