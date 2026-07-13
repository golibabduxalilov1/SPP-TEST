import { dashboardSteps } from "./dashboard";
import { ordersSteps } from "./orders";
import { tabloSteps } from "./tablo";
import { labelsSteps } from "./labels";
import { machinesSteps } from "./machines";
import { employeesSteps } from "./employees";
import { conflictsSteps } from "./conflicts";
import { warehouseSteps } from "./warehouse";
import { reportsSteps } from "./reports";

export const TUTORIAL_PAGES = {
  dashboard: { path: "/", steps: dashboardSteps },
  orders: { path: "/orders", steps: ordersSteps },
  tablo: { path: "/tablo", steps: tabloSteps },
  labels: { path: "/labels", steps: labelsSteps },
  machines: { path: "/machines", steps: machinesSteps },
  employees: { path: "/employees", steps: employeesSteps },
  conflicts: { path: "/conflicts", steps: conflictsSteps },
  warehouse: { path: "/warehouse", steps: warehouseSteps },
  reports: { path: "/reports", steps: reportsSteps },
};

export function pageKeyForPath(pathname) {
  if (pathname === "/") return "dashboard";
  const key = Object.keys(TUTORIAL_PAGES).find(
    (k) => k !== "dashboard" && pathname.startsWith(TUTORIAL_PAGES[k].path)
  );
  return key || null;
}
