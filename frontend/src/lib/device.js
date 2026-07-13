export function getDeviceId() {
  let id = localStorage.getItem("spp_device_id");
  if (!id) {
    id = "device-" + crypto.randomUUID().slice(0, 12);
    localStorage.setItem("spp_device_id", id);
  }
  return id;
}
